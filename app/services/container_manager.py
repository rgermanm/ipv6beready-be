import logging
import uuid
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.models.instance import LabInstance
from app.models.lab import LabDefinition, LabFormula
from app.models.session import LabSessionStatus
from app.repositories import instances as instance_repo
from app.services.clab_inspect import nodes_from_inspect
from app.services.clab_manager import clab_manager, resolve_clab_name, sanitize_user_id

logger = logging.getLogger(__name__)


class ContainerManager:
    """Provisions and tears down per-user lab instances."""

    def __init__(self) -> None:
        self._docker = None

    def _get_docker_client(self):
        if self._docker is not None:
            return self._docker

        import docker

        self._docker = docker.from_env()
        return self._docker

    def get_instance(self, lab_id: str, user_id: str) -> LabInstance | None:
        instance = instance_repo.get_active_instance(user_id, lab_id)
        if not instance:
            return None
        if instance.is_expired():
            self._expire_instance(instance)
            return None
        return instance

    def create_instance(self, lab: LabDefinition, user_id: str) -> LabInstance:
        existing = self.get_instance(lab.id, user_id)
        if existing and existing.status in ("starting", "running"):
            return existing

        ttl_seconds = settings.lab_ttl_seconds
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)
        session_id = f"lab-{lab.id}-{uuid.uuid4().hex[:8]}"
        clab_user = sanitize_user_id(user_id)
        workdir = lab.path or (lab.formula.clab.path if lab.formula.clab else "")
        clab_name = (
            resolve_clab_name(lab.formula.clab.lab_name, clab_user)
            if lab.formula.clab
            else session_id
        )
        topology_file = (
            lab.formula.clab.topology_file if lab.formula.clab else ""
        )

        instance = LabInstance(
            id="",
            session_id=session_id,
            lab_id=lab.id,
            user_id=user_id,
            clab_name=clab_name,
            path=workdir,
            topology_file=topology_file,
            status="starting",
            ttl_seconds=ttl_seconds,
            created_at=now,
            expires_at=expires_at,
            message="Lab provisioning started",
            endpoint=settings.clab_remote_host
            if lab.formula.provider == "clab"
            else settings.lab_host,
            port=lab.formula.port,
            protocol=lab.formula.protocol,
        )
        instance_repo.insert_instance(instance)

        session = LabSessionStatus(
            session_id=session_id,
            lab_id=lab.id,
            status="starting",
            protocol=lab.formula.protocol,
            port=lab.formula.port,
            credentials=lab.formula.credentials,
            expires_at=expires_at.isoformat(),
            message="Lab provisioning started",
        )

        try:
            if lab.formula.provider == "clab" and lab.formula.clab:
                if not workdir:
                    raise RuntimeError("Lab path is missing; cannot deploy containerlab")
                inspect = clab_manager.provision(
                    session,
                    lab.formula.clab,
                    user_id=clab_user,
                    ttl_seconds=ttl_seconds,
                    clab_name=clab_name,
                    workdir=workdir,
                )
                instance.inspect = inspect
                instance.nodes = nodes_from_inspect(inspect, clab_name)
            elif settings.mock_containers:
                self._provision_mock(session, lab.formula)
            else:
                self._provision_docker(session, lab.formula, user_id)
        except Exception as exc:
            logger.exception("Failed to provision lab %s for user %s", lab.id, user_id)
            instance.status = "error"
            instance.message = str(exc)
            instance_repo.save_instance(instance)
            return instance

        instance.status = session.status
        instance.message = session.message
        instance.endpoint = session.endpoint
        instance.port = session.port
        instance.protocol = session.protocol
        instance_repo.save_instance(instance)
        return instance

    def stop_instance(self, lab_id: str, user_id: str) -> bool:
        from app.services.lab_registry import get_lab

        lab = get_lab(lab_id)
        instance = instance_repo.get_active_instance(user_id, lab_id)
        if not instance and not lab:
            return False

        if instance:
            self._destroy_runtime(lab, instance)
            instance_repo.mark_stopped(instance, message="Lab terminated")
            return True

        return False

    def _expire_instance(self, instance: LabInstance) -> None:
        from app.services.lab_registry import get_lab

        lab = get_lab(instance.lab_id)
        self._destroy_runtime(lab, instance)
        instance_repo.mark_stopped(instance, message="Lab TTL expired")

    def _destroy_runtime(self, lab: LabDefinition | None, instance: LabInstance) -> None:
        if lab and lab.formula.provider == "clab" and lab.formula.clab:
            try:
                clab_manager.destroy(
                    lab.formula.clab,
                    user_id=sanitize_user_id(instance.user_id),
                    ttl_seconds=instance.ttl_seconds,
                    clab_name=instance.clab_name,
                    workdir=instance.path or lab.path,
                )
            except Exception:
                logger.exception(
                    "Failed to destroy containerlab %s", instance.clab_name
                )
            return

        if (
            instance.session_id
            and not settings.mock_containers
            and lab
            and lab.formula.provider != "clab"
        ):
            try:
                client = self._get_docker_client()
                container = client.containers.get(instance.session_id)
                container.stop(timeout=10)
                container.remove(force=True)
            except Exception:
                logger.exception(
                    "Failed to stop container for instance %s", instance.id
                )

    def _provision_mock(self, session: LabSessionStatus, formula: LabFormula) -> None:
        session.status = "running"
        session.endpoint = settings.lab_host
        session.port = 2222
        session.message = "Mock container running (MOCK_CONTAINERS=true)"
        session.container_id = f"mock-{session.session_id}"

    def _provision_docker(
        self,
        session: LabSessionStatus,
        formula: LabFormula,
        user_id: str | None,
    ) -> None:
        client = self._get_docker_client()
        container_name = f"{formula.container_name_prefix}-{session.session_id}"

        labels = {
            "ipv6beready.lab_id": session.lab_id,
            "ipv6beready.session_id": session.session_id,
        }
        if user_id:
            labels["ipv6beready.user_id"] = user_id

        run_kwargs: dict = {
            "image": formula.image,
            "name": container_name,
            "detach": True,
            "labels": labels,
            "environment": formula.environment or None,
            "ports": {f"{formula.port}/tcp": None},
        }

        if formula.networks:
            run_kwargs["network"] = settings.docker_network

        container = client.containers.run(**run_kwargs)
        container.reload()

        port_bindings = container.attrs["NetworkSettings"]["Ports"]
        host_port = int(port_bindings[f"{formula.port}/tcp"][0]["HostPort"])

        session.status = "running"
        session.endpoint = settings.lab_host
        session.port = host_port
        session.container_id = container.id
        session.message = "Container running"


container_manager = ContainerManager()
