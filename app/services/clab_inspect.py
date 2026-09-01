from __future__ import annotations

import json
import re
from typing import Any

from app.models.instance import InstanceNode

_JSON_START = re.compile(r"[{\[]")


def parse_inspect_json(raw: str) -> Any:
    """Extract a JSON value from containerlab inspect stdout."""
    text = (raw or "").strip()
    if not text:
        return None
    match = _JSON_START.search(text)
    if not match:
        return None
    snippet = text[match.start() :]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        try:
            value, _end = decoder.raw_decode(snippet)
            return value
        except json.JSONDecodeError:
            return None


def flatten_inspect_containers(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        containers: list[dict[str, Any]] = []
        for item in raw:
            containers.extend(flatten_inspect_containers(item))
        return containers
    if not isinstance(raw, dict):
        return []
    if "containers" in raw and isinstance(raw["containers"], list):
        return flatten_inspect_containers(raw["containers"])
    if "name" in raw and (
        "ipv4_address" in raw or "ipv6_address" in raw or "state" in raw
    ):
        return [raw]
    containers: list[dict[str, Any]] = []
    for value in raw.values():
        if isinstance(value, list):
            containers.extend(flatten_inspect_containers(value))
    return containers


def _ip_only(address: str | None) -> str | None:
    if not address:
        return None
    value = str(address).strip()
    if not value or value.upper() in {"N/A", "NONE"}:
        return None
    return value.split("/")[0]


def _shortname(container_name: str, clab_name: str) -> str:
    prefix = f"clab-{clab_name}-"
    if container_name.startswith(prefix):
        return container_name[len(prefix) :]
    if "-" in container_name:
        return container_name.rsplit("-", 1)[-1]
    return container_name


def nodes_from_inspect(raw: Any, clab_name: str) -> list[InstanceNode]:
    nodes: list[InstanceNode] = []
    for container in flatten_inspect_containers(raw):
        name = str(container.get("name") or "")
        if not name:
            continue
        short = (
            container.get("name_short")
            or container.get("shortname")
            or _shortname(name, clab_name)
        )
        nodes.append(
            InstanceNode(
                name=name,
                shortname=str(short),
                ipv4=_ip_only(container.get("ipv4_address")),
                ipv6=_ip_only(container.get("ipv6_address")),
                state=container.get("state"),
                kind=container.get("kind"),
            )
        )
    return nodes
