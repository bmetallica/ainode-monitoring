from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class SystemMetric:
    node_id: str
    node_name: str
    timestamp: str
    cpu_cores: int = 0
    cpu_percent: float = 0.0
    cpu_load_1m: float = 0.0
    cpu_load_5m: float = 0.0
    cpu_load_15m: float = 0.0
    mem_total_mb: int = 0
    mem_used_mb: int = 0
    mem_available_mb: int = 0
    mem_percent: float = 0.0
    swap_used_mb: Optional[int] = None
    swap_total_mb: Optional[int] = None
    uptime_seconds: int = 0
    temperatures: dict = field(default_factory=dict)


@dataclass
class GPUMetric:
    node_id: str
    node_name: str
    timestamp: str
    utilization_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    temperature_c: float = 0.0


@dataclass
class ModelInfo:
    model: str = ""
    api_port: int = 0
    status: str = ""
    nodes: int = 0
    gpu_memory_utilization: float = 0.0
    max_model_len: int = 0
    load_phase: str = ""


@dataclass
class ModelPerf:
    model: str = ""
    requests: int = 0
    errors: int = 0
    avg_latency_ms: float = 0.0
    tokens_generated: int = 0
    avg_tokens_per_second: Optional[float] = None


@dataclass
class ModelsMetric:
    node_id: str
    node_name: str
    timestamp: str
    loaded: list = field(default_factory=list)
    embeddings: list = field(default_factory=list)
    requests_total: int = 0
    errors_total: int = 0
    uptime_seconds: int = 0
    per_model: dict = field(default_factory=dict)


@dataclass
class ClusterNode:
    node_id: str = ""
    node_name: str = ""
    status: str = ""
    model: str = ""
    gpu_memory_gb: float = 0.0
    gpu_memory_used_percent: float = 0.0


@dataclass
class ClusterMetric:
    node_id: str
    node_name: str
    timestamp: str
    nodes_total: int = 0
    nodes_online: int = 0
    vram_total_gb: float = 0.0
    nodes: list = field(default_factory=list)
