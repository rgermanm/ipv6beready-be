import logging
import re
import shlex

import paramiko

from app.config import settings
from app.models.lab import ClabConfig, LabCredentials
from app.models.session import LabSessionStatus
from app.services.clab_inspect import nodes_from_inspect, parse_inspect_json

logger = logging.getLogger(__name__)

_USER_ID_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def sanitize_user_id(user_id: str) -> str:
    cleaned = _USER_ID_RE.sub("", user_id).strip("-_")
    return cleaned[:32] or "user"


def resolve_clab_name(base_name: str, user_id: str | None) -> str:
    if not user_id:
        return base_name
    return f"{base_name}-{sanitize_user_id(user_id)}"


class ClabManager:
    """Deploys and destroys containerlab topologies on a remote host via SSH."""

    def _connect(self) -> paramiko.SSHClient:
        if not settings.clab_remote_password:
            raise RuntimeError("CLAB_REMOTE_PASSWORD is not configured")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=settings.clab_remote_host,
            port=settings.clab_remote_port,
            username=settings.clab_remote_username,
            password=settings.clab_remote_password,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30,
        )
        return client

    def _run(
        self,
        client: paramiko.SSHClient,
        command: str,
        timeout: int = 120,
    ) -> tuple[int, str, str]:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err = stderr.read().decode()
        return exit_code, out, err

    def _env_prefix(self, user_id: str, ttl_seconds: int) -> str:
        return f"USER_ID={shlex.quote(user_id)} TTL={int(ttl_seconds)}"

    def _container_hostname(self, clab_name: str, node: str) -> str:
        return f"clab-{clab_name}-{node}"

    def inspect(
        self,
        clab: ClabConfig,
        *,
        user_id: str,
        ttl_seconds: int,
        clab_name: str,
        workdir: str,
    ) -> object | None:
        if settings.mock_containers:
            return self._mock_inspect(clab_name)

        client = self._connect()
        try:
            return self._inspect(client, clab, user_id, ttl_seconds, clab_name, workdir)
        finally:
            client.close()

    def _inspect(
        self,
        client: paramiko.SSHClient,
        clab: ClabConfig,
        user_id: str,
        ttl_seconds: int,
        clab_name: str,
        workdir: str,
    ) -> object | None:
        env = self._env_prefix(user_id, ttl_seconds)
        quoted_dir = shlex.quote(workdir)
        quoted_topo = shlex.quote(clab.topology_file)
        quoted_name = shlex.quote(clab_name)
        commands = [
            f"cd {quoted_dir} && {env} containerlab inspect --name {quoted_name} -f json 2>/dev/null",
            f"cd {quoted_dir} && {env} containerlab inspect -t {quoted_topo} -f json 2>/dev/null",
        ]
        for command in commands:
            exit_code, out, err = self._run(client, command, timeout=60)
            parsed = parse_inspect_json(out)
            if parsed:
                return parsed
            if exit_code != 0:
                logger.debug("containerlab inspect failed: %s", err or out[-500:])
        return None

    def is_lab_running(
        self,
        clab: ClabConfig,
        *,
        user_id: str,
        ttl_seconds: int,
        clab_name: str,
        workdir: str,
    ) -> bool:
        if settings.mock_containers:
            return False
        client = self._connect()
        try:
            inspect = self._inspect(
                client, clab, user_id, ttl_seconds, clab_name, workdir
            )
            nodes = nodes_from_inspect(inspect, clab_name)
            return any((node.state or "").lower() == "running" for node in nodes)
        finally:
            client.close()

    def provision(
        self,
        session: LabSessionStatus,
        clab: ClabConfig,
        *,
        user_id: str,
        ttl_seconds: int,
        clab_name: str,
        workdir: str,
    ) -> object | None:
        if settings.mock_containers:
            self._provision_mock(session, clab, clab_name)
            return self._mock_inspect(clab_name)

        client = self._connect()
        try:
            env = self._env_prefix(user_id, ttl_seconds)
            quoted_dir = shlex.quote(workdir)
            quoted_topo = shlex.quote(clab.topology_file)

            running = False
            inspect = self._inspect(
                client, clab, user_id, ttl_seconds, clab_name, workdir
            )
            if nodes_from_inspect(inspect, clab_name):
                running = True

            if not running:
                logger.info(
                    "Deploying containerlab %s in %s (USER_ID=%s TTL=%s)",
                    clab_name,
                    workdir,
                    user_id,
                    ttl_seconds,
                )
                deploy_cmd = (
                    f"cd {quoted_dir} && {env} containerlab deploy "
                    f"-t {quoted_topo} 2>&1"
                )
                exit_code, out, err = self._run(client, deploy_cmd, timeout=300)
                if exit_code != 0:
                    raise RuntimeError(
                        f"containerlab deploy failed: {err or out[-2000:]}"
                    )
                logger.info("Containerlab deploy output: %s", out[-500:])
                inspect = self._inspect(
                    client, clab, user_id, ttl_seconds, clab_name, workdir
                )

            entry_host = self._container_hostname(clab_name, clab.entry_node)
            session.status = "running"
            session.endpoint = settings.clab_remote_host
            session.port = settings.clab_remote_port
            session.protocol = "ssh"
            session.credentials = LabCredentials(
                username=settings.clab_remote_username,
                password=settings.clab_remote_password,
            )
            session.container_id = clab_name
            session.message = (
                f"Containerlab '{clab_name}' is running. "
                f"Node access via inspect IPs (entry: {entry_host})."
            )
            return inspect
        finally:
            client.close()

    def destroy(
        self,
        clab: ClabConfig,
        *,
        user_id: str,
        ttl_seconds: int,
        clab_name: str,
        workdir: str,
    ) -> None:
        if settings.mock_containers:
            return

        client = self._connect()
        try:
            env = self._env_prefix(user_id, ttl_seconds)
            quoted_dir = shlex.quote(workdir)
            quoted_topo = shlex.quote(clab.topology_file)
            quoted_name = shlex.quote(clab_name)
            commands = [
                f"cd {quoted_dir} && {env} containerlab destroy --name {quoted_name} --cleanup 2>&1",
                f"cd {quoted_dir} && {env} containerlab destroy -t {quoted_topo} --cleanup 2>&1",
            ]
            for destroy_cmd in commands:
                exit_code, out, err = self._run(client, destroy_cmd, timeout=180)
                if exit_code == 0:
                    return
                logger.warning(
                    "containerlab destroy returned %s: %s",
                    exit_code,
                    err or out[-1000:],
                )
        finally:
            client.close()

    def _mock_inspect(self, clab_name: str) -> dict:
        nodes = ["r1", "r2", "r3", "pc1", "pc2", "pc3"]
        containers = []
        for index, node in enumerate(nodes, start=2):
            containers.append(
                {
                    "lab_name": clab_name,
                    "name": f"clab-{clab_name}-{node}",
                    "container_id": f"mock-{node}",
                    "kind": "linux",
                    "state": "running",
                    "ipv4_address": f"172.20.20.{index}/24",
                    "ipv6_address": f"3fff:172:20:20::{index}/64",
                }
            )
        return {clab_name: containers}

    def _provision_mock(
        self, session: LabSessionStatus, clab: ClabConfig, clab_name: str
    ) -> None:
        entry_host = self._container_hostname(clab_name, clab.entry_node)
        session.status = "running"
        session.endpoint = settings.clab_remote_host
        session.port = settings.clab_remote_port
        session.protocol = "ssh"
        session.credentials = LabCredentials(
            username=settings.clab_remote_username,
            password=settings.clab_remote_password or "mock-password",
        )
        session.container_id = f"mock-{clab_name}"
        session.message = (
            f"Mock containerlab '{clab_name}' (MOCK_CONTAINERS=true). "
            f"Node access: ssh {entry_host} "
            f"(password: {clab.node_credentials.password})"
        )


clab_manager = ClabManager()
