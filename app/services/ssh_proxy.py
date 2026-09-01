import asyncio
import logging

import paramiko
from fastapi import WebSocket, WebSocketDisconnect

from app.config import settings
from app.models.lab import ClabConfig

logger = logging.getLogger(__name__)


def _container_hostname(clab: ClabConfig, node: str, clab_name: str | None = None) -> str:
    return f"clab-{clab_name or clab.lab_name}-{node}"


def _looks_like_ip(value: str) -> bool:
    if ":" in value and not value.startswith("["):
        return True
    parts = value.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False


def _resolve_container_ip(jump_client: paramiko.SSHClient, hostname: str) -> str:
    _, stdout, _ = jump_client.exec_command(
        f"getent hosts {hostname} | awk '{{print $1}}'",
        timeout=15,
    )
    ip = stdout.read().decode().strip()
    if not ip:
        raise RuntimeError(f"Could not resolve container hostname: {hostname}")
    return ip


def _open_container_shell(
    clab: ClabConfig,
    node: str,
    host: str | None = None,
    clab_name: str | None = None,
) -> paramiko.Channel:
    hostname = host or _container_hostname(clab, node, clab_name)
    creds = clab.node_credentials

    jump = paramiko.SSHClient()
    jump.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    jump.connect(
        hostname=settings.clab_remote_host,
        port=settings.clab_remote_port,
        username=settings.clab_remote_username,
        password=settings.clab_remote_password,
        timeout=30,
        banner_timeout=30,
        auth_timeout=30,
    )

    container_ip = hostname
    if not _looks_like_ip(hostname):
        container_ip = _resolve_container_ip(jump, hostname)
    transport = jump.get_transport()
    if transport is None:
        raise RuntimeError("Failed to open SSH transport to lab host")

    dest_channel = transport.open_channel(
        "direct-tcpip",
        (container_ip, 22),
        ("", 0),
    )

    inner = paramiko.Transport(dest_channel)
    inner.connect(username=creds.username, password=creds.password)
    shell = inner.open_session()
    shell.get_pty(term="xterm-256color", width=120, height=40)
    shell.invoke_shell()

    # Keep jump client alive for the session lifetime
    shell._ipv6beready_jump = jump  # type: ignore[attr-defined]
    shell._ipv6beready_inner = inner  # type: ignore[attr-defined]
    return shell


async def bridge_console(
    websocket: WebSocket,
    clab: ClabConfig,
    node: str,
    host: str | None = None,
    clab_name: str | None = None,
) -> None:
    loop = asyncio.get_running_loop()
    channel = await loop.run_in_executor(
        None, _open_container_shell, clab, node, host, clab_name
    )

    async def read_ssh() -> None:
        try:
            while True:
                if channel.recv_ready():
                    data = channel.recv(4096)
                    if not data:
                        break
                    await websocket.send_bytes(data)
                elif channel.exit_status_ready():
                    break
                else:
                    await asyncio.sleep(0.02)
        except Exception:
            logger.exception("SSH read error for node %s", node)

    async def read_ws() -> None:
        try:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    break
                if message["type"] != "websocket.receive":
                    continue
                if "bytes" in message and message["bytes"]:
                    channel.send(message["bytes"])
                elif "text" in message and message["text"]:
                    text = message["text"]
                    if text.startswith("{"):
                        # Optional resize message from xterm
                        try:
                            import json

                            payload = json.loads(text)
                            if payload.get("type") == "resize":
                                channel.resize_pty(
                                    width=payload.get("cols", 120),
                                    height=payload.get("rows", 40),
                                )
                                continue
                        except (json.JSONDecodeError, TypeError):
                            pass
                    channel.send(text)
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("WebSocket read error for node %s", node)

    read_task = asyncio.create_task(read_ssh())
    write_task = asyncio.create_task(read_ws())

    try:
        await asyncio.wait(
            [read_task, write_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
    finally:
        read_task.cancel()
        write_task.cancel()
        try:
            channel.close()
        except Exception:
            pass
        inner = getattr(channel, "_ipv6beready_inner", None)
        jump = getattr(channel, "_ipv6beready_jump", None)
        if inner:
            try:
                inner.close()
            except Exception:
                pass
        if jump:
            try:
                jump.close()
            except Exception:
                pass
