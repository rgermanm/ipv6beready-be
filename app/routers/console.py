from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.security import user_from_token
from app.services.container_manager import container_manager
from app.services.lab_registry import get_lab
from app.services.ssh_proxy import bridge_console

router = APIRouter(prefix="/labs", tags=["lab-console"])

@router.websocket("/{lab_id}/console/{node}")
async def lab_console(
    websocket: WebSocket,
    lab_id: str,
    node: str,
    token: str | None = None,
) -> None:
    """Interactive SSH console to a per-user containerlab node."""
    await websocket.accept()

    user = user_from_token(token)
    if not user:
        await websocket.close(code=4401, reason="Authentication required")
        return

    lab = get_lab(lab_id)
    if not lab or lab.formula.provider != "clab" or not lab.formula.clab:
        await websocket.close(code=4404, reason="Lab not found")
        return

    allowed_nodes = {item.clab_node for item in (lab.topology.nodes if lab.topology else [])}
    if allowed_nodes and node not in allowed_nodes:
        await websocket.close(code=4400, reason=f"Invalid node: {node}")
        return

    instance = container_manager.get_instance(lab_id, user.id)
    if not instance or instance.status != "running":
        if not settings.mock_containers:
            reason = (
                "Lab instance expired"
                if instance and instance.status == "expired"
                else "Lab instance is not running"
            )
            await websocket.close(code=4403, reason=reason)
            return

    node_host = None
    if instance:
        match = next((n for n in instance.nodes if n.shortname == node), None)
        node_host = (match.ipv4 if match else None) or (
            f"clab-{instance.clab_name}-{node}" if instance else None
        )

    try:
        await bridge_console(
            websocket,
            lab.formula.clab,
            node,
            host=node_host,
            clab_name=instance.clab_name if instance else None,
        )
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger_msg = str(exc)
        try:
            await websocket.close(code=1011, reason=logger_msg[:120])
        except Exception:
            pass
