import logging
import select
import socket
import threading
from urllib.parse import quote, urlparse, urlunparse

import paramiko
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.config import settings

logger = logging.getLogger(__name__)

_client: MongoClient | None = None
_tunnel: "_ParamikoTunnel | None" = None


class _ParamikoTunnel:
    """Forward a local TCP port to a remote host through an SSH session."""

    def __init__(
        self,
        ssh_host: str,
        ssh_port: int,
        ssh_username: str,
        ssh_password: str,
        remote_host: str,
        remote_port: int,
    ) -> None:
        self._ssh_host = ssh_host
        self._ssh_port = ssh_port
        self._ssh_username = ssh_username
        self._ssh_password = ssh_password
        self._remote_host = remote_host
        self._remote_port = remote_port
        self._client: paramiko.SSHClient | None = None
        self._server: socket.socket | None = None
        self._threads: list[threading.Thread] = []
        self._stop = threading.Event()
        self.local_bind_port = 0

    def start(self) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self._ssh_host,
            port=self._ssh_port,
            username=self._ssh_username,
            password=self._ssh_password,
            timeout=10,
            banner_timeout=10,
            auth_timeout=10,
        )
        transport = client.get_transport()
        if transport is None:
            client.close()
            raise RuntimeError("SSH transport not available for Mongo tunnel")
        transport.set_keepalive(30)

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(8)
        server.settimeout(1.0)
        self.local_bind_port = int(server.getsockname()[1])
        self._client = client
        self._server = server

        acceptor = threading.Thread(target=self._accept_loop, daemon=True)
        acceptor.start()
        self._threads.append(acceptor)

    def _accept_loop(self) -> None:
        assert self._server is not None
        assert self._client is not None
        while not self._stop.is_set():
            try:
                local_sock, _addr = self._server.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            worker = threading.Thread(
                target=self._bridge, args=(local_sock,), daemon=True
            )
            worker.start()
            self._threads.append(worker)

    def _bridge(self, local_sock: socket.socket) -> None:
        transport = self._client.get_transport() if self._client else None
        if transport is None:
            local_sock.close()
            return
        try:
            channel = transport.open_channel(
                "direct-tcpip",
                (self._remote_host, self._remote_port),
                local_sock.getsockname(),
            )
        except Exception:
            logger.exception("Failed to open Mongo SSH channel")
            local_sock.close()
            return

        try:
            while not self._stop.is_set():
                readable, _, _ = select.select([local_sock, channel], [], [], 1.0)
                if local_sock in readable:
                    data = local_sock.recv(32768)
                    if not data:
                        break
                    channel.sendall(data)
                if channel in readable:
                    data = channel.recv(32768)
                    if not data:
                        break
                    local_sock.sendall(data)
        except OSError:
            pass
        finally:
            try:
                channel.close()
            except Exception:
                pass
            try:
                local_sock.close()
            except Exception:
                pass

    def stop(self) -> None:
        self._stop.set()
        if self._server is not None:
            try:
                self._server.close()
            except Exception:
                pass
            self._server = None
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None


def get_client() -> MongoClient:
    if _client is None:
        raise RuntimeError("MongoDB is not connected")
    return _client


def get_db() -> Database:
    return get_client()[settings.mongodb_db]


def _rewrite_uri_host(uri: str, host: str, port: int) -> str:
    parsed = urlparse(uri)
    username = parsed.username or ""
    password = parsed.password or ""
    userinfo = ""
    if username:
        userinfo = quote(username, safe="")
        if password:
            userinfo += f":{quote(password, safe='')}"
        userinfo += "@"
    return urlunparse(parsed._replace(netloc=f"{userinfo}{host}:{port}"))


def is_connected() -> bool:
    return _client is not None


def connect() -> bool:
    global _client, _tunnel
    if _client is not None:
        return True

    uri = settings.mongodb_uri
    try:
        if settings.mongodb_ssh_tunnel:
            logger.info(
                "Opening Mongo SSH tunnel via %s:%s",
                settings.clab_remote_host,
                settings.clab_remote_port,
            )
            if not settings.clab_remote_password:
                raise RuntimeError(
                    "Mongo SSH tunnel is enabled but CLAB_REMOTE_PASSWORD is empty"
                )
            _tunnel = _ParamikoTunnel(
                ssh_host=settings.clab_remote_host,
                ssh_port=settings.clab_remote_port,
                ssh_username=settings.clab_remote_username,
                ssh_password=settings.clab_remote_password,
                remote_host=settings.mongodb_tunnel_host,
                remote_port=settings.mongodb_tunnel_port,
            )
            _tunnel.start()
            uri = _rewrite_uri_host(uri, "127.0.0.1", _tunnel.local_bind_port)
            logger.info(
                "Mongo SSH tunnel %s:%s -> 127.0.0.1:%s",
                settings.mongodb_tunnel_host,
                settings.mongodb_tunnel_port,
                _tunnel.local_bind_port,
            )

        _client = MongoClient(
            uri,
            serverSelectionTimeoutMS=8000,
            connectTimeoutMS=8000,
        )
        _client.admin.command("ping")
        logger.info("Connected to MongoDB database %s", settings.mongodb_db)
        return True
    except Exception:
        logger.exception(
            "MongoDB is unavailable; API will start in degraded mode "
            "(catalog from local files, auth/instances disabled)"
        )
        close()
        return False


def close() -> None:
    global _client, _tunnel
    if _client is not None:
        _client.close()
        _client = None
    if _tunnel is not None:
        _tunnel.stop()
        _tunnel = None
    logger.info("MongoDB connection closed")


def ping() -> bool:
    try:
        get_client().admin.command("ping")
        return True
    except (PyMongoError, RuntimeError):
        return False
