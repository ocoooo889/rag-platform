"""
平台端口注册表 — 与项目根 port.md 保持一致（Day2）。
后端 B 维护；其他模块可 `from app.schema.ports import PORT_REGISTRY, get_port`。
"""

from __future__ import annotations

import socket
from dataclasses import asdict, dataclass
from typing import Any, Literal

import httpx

Protocol = Literal["HTTP", "HTTP/SSE", "Redis"]


@dataclass(frozen=True)
class PortSpec:
    port: int
    feature: str
    process: str
    bind: str
    protocol: Protocol
    health_check: str
    owner: str
    depends: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["depends"] = list(self.depends)
        return row


# 严格对齐 port.md
PORT_REGISTRY: tuple[PortSpec, ...] = (
    PortSpec(
        8000,
        "-（已有：向量库）",
        "Chroma",
        "127.0.0.1:8000",
        "HTTP",
        "GET /api/v2/heartbeat",
        "共用（先起）",
        (),
    ),
    PortSpec(
        8001,
        "-（已有：主 API；承载防注入/意图/切分/重写/混合检索/模型热读/评测 API）",
        "FastAPI 主",
        "0.0.0.0:8001",
        "HTTP/SSE",
        "GET /health",
        "后端 B 起实例1",
        ("8000", "6379"),
    ),
    PortSpec(
        8002,
        "重排序（Rerank）",
        "Rerank 微服务",
        "127.0.0.1:8002",
        "HTTP",
        "GET /health",
        "后端 A",
        (),
    ),
    PortSpec(
        8003,
        "网关负载均衡 · 后端副本1（多人同时对话）",
        "FastAPI 副本1",
        "0.0.0.0:8003",
        "HTTP/SSE",
        "GET /health",
        "后端 B",
        ("8001",),
    ),
    PortSpec(
        8004,
        "网关负载均衡 · 后端副本2（Day2 可选）",
        "FastAPI 副本2",
        "0.0.0.0:8004",
        "HTTP/SSE",
        "GET /health",
        "后端 B（Day2 下午可选）",
        ("8001",),
    ),
    PortSpec(
        6379,
        "缓存（Answer Redis）",
        "Redis",
        "127.0.0.1:6379",
        "Redis",
        "PING",
        "后端 B（Docker/redis-server）",
        (),
    ),
    PortSpec(
        8080,
        "网关负载均衡（统一入口 + SSE 粘性）",
        "Nginx Gateway",
        "0.0.0.0:8080",
        "HTTP/SSE",
        "GET /health → 反代后端",
        "后端 B",
        ("8001", "8003", "8004"),
    ),
    PortSpec(
        5173,
        "-（已有：前端开发）",
        "Vite",
        "127.0.0.1:5173",
        "HTTP",
        "页面可开",
        "前端 A/B",
        ("8001",),
    ),
    PortSpec(
        8520,
        "-（已有：Docker SPA 入口）",
        "Docker SPA 入口",
        "宿主机映射",
        "HTTP",
        "打开首页",
        "可选，2 天不强制",
        (),
    ),
)

CHROMA_PORT = 8000
API_PORT = 8001
RERANK_PORT = 8002
API_REPLICA1_PORT = 8003
API_REPLICA2_PORT = 8004
REDIS_PORT = 6379
GATEWAY_PORT = 8080
VITE_DEV_PORT = 5173
DOCKER_SPA_PORT = 8520


def get_port(port: int) -> PortSpec | None:
    for spec in PORT_REGISTRY:
        if spec.port == port:
            return spec
    return None


def list_ports_dict() -> list[dict[str, Any]]:
    return [spec.to_dict() for spec in PORT_REGISTRY]


def _probe_host_port(port: int) -> str:
    """HTTP 类服务统一用 127.0.0.1 探测（与 port.md bind 一致）。"""
    return "127.0.0.1"


def _probe_redis(host: str, port: int, timeout: float = 2.0) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(b"*1\r\n$4\r\nPING\r\n")
            data = sock.recv(64)
            if b"PONG" in data:
                return True, "PONG"
            return False, data.decode("utf-8", errors="replace")[:80] or "无 PONG"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:120]


def _probe_http(url: str, timeout: float = 2.5) -> tuple[bool, str]:
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            if resp.status_code < 400:
                body = (resp.text or "")[:80]
                return True, f"HTTP {resp.status_code}" + (f" · {body}" if body else "")
            return False, f"HTTP {resp.status_code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:120]


def probe_service(port: int, timeout: float = 2.5) -> dict[str, Any]:
    """按 port.md 健康检查约定探测单个端口。"""
    spec = get_port(port)
    if spec is None:
        return {"port": port, "status": "unknown", "detail": "未在 port.md 注册"}

    host = _probe_host_port(port)
    ok = False
    detail = ""

    if port == CHROMA_PORT:
        ok, detail = _probe_http(f"http://{host}:{port}/api/v2/heartbeat", timeout)
    elif port == REDIS_PORT:
        ok, detail = _probe_redis(host, port, timeout=min(timeout, 2.0))
    elif port in (API_PORT, API_REPLICA1_PORT, API_REPLICA2_PORT, RERANK_PORT, GATEWAY_PORT):
        ok, detail = _probe_http(f"http://{host}:{port}/health", timeout)
    elif port == VITE_DEV_PORT:
        ok, detail = _probe_http(f"http://{host}:{port}/", timeout)
    elif port == DOCKER_SPA_PORT:
        ok, detail = _probe_http(f"http://{host}:{port}/", timeout)
    else:
        detail = "无自动探测"

    return {
        "port": spec.port,
        "key": _service_key(spec.port),
        "feature": spec.feature,
        "process": spec.process,
        "bind": spec.bind,
        "protocol": spec.protocol,
        "health_check": spec.health_check,
        "owner": spec.owner,
        "depends": list(spec.depends),
        "status": "ok" if ok else "down",
        "detail": detail or ("正常" if ok else "不可用"),
    }


def _service_key(port: int) -> str:
    mapping = {
        CHROMA_PORT: "chroma",
        API_PORT: "api_main",
        RERANK_PORT: "rerank",
        API_REPLICA1_PORT: "api_replica1",
        API_REPLICA2_PORT: "api_replica2",
        REDIS_PORT: "redis",
        GATEWAY_PORT: "gateway",
        VITE_DEV_PORT: "vite",
        DOCKER_SPA_PORT: "docker_spa",
    }
    return mapping.get(port, f"port_{port}")


def probe_all_services(timeout: float = 2.5) -> list[dict[str, Any]]:
    return [probe_service(spec.port, timeout=timeout) for spec in PORT_REGISTRY]
