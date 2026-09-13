import os
import logging
from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger(__name__)

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_ORG = os.getenv("INFLUX_ORG", "ainode")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "monitoring")

def _load_token() -> str:
    token_file = os.getenv("INFLUX_TOKEN_FILE", "/shared/influx_token.txt")
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            token = f.read().strip()
            if token:
                return token
    return os.getenv("INFLUX_TOKEN", "ainode-secret-password")


client = InfluxDBClient(url=INFLUX_URL, token=_load_token(), org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()


def write_point(measurement: str, tags: dict, fields: dict, timestamp: str, node_id: str) -> None:
    try:
        p = Point(measurement).tag("node_id", node_id)
        for k, v in tags.items():
            p.tag(k, v)
        p.fields_dict(fields).time(timestamp, WritePrecision.ms)
        write_api.write(INFLUX_BUCKET, INFLUX_ORG, p)
    except Exception as e:
        logger.error(f"Failed to write point to InfluxDB: {e}")


def store_system_metric(data: dict) -> None:
    node_id = data.get("node_id", "unknown")
    ts = data.get("timestamp", datetime.now(timezone.utc).isoformat())
    cpu = data.get("cpu", {})
    mem = data.get("memory", {})
    temp = data.get("temperature_c", {})

    cpu_fields = {
        "cores": cpu.get("cores"),
        "percent": cpu.get("percent"),
        "load_1m": cpu.get("load_1m"),
        "load_5m": cpu.get("load_5m"),
        "load_15m": cpu.get("load_15m"),
    }
    write_point("system_cpu", {"node_name": data.get("node_name", "")},
                {k: v for k, v in cpu_fields.items() if v is not None}, ts, node_id)

    mem_fields = {
        "total_mb": mem.get("total_mb"),
        "used_mb": mem.get("used_mb"),
        "available_mb": mem.get("available_mb"),
        "percent": mem.get("percent"),
        "swap_used_mb": mem.get("swap_used_mb"),
        "swap_total_mb": mem.get("swap_total_mb"),
    }
    write_point("system_memory", {"node_name": data.get("node_name", "")},
                {k: v for k, v in mem_fields.items() if v is not None}, ts, node_id)

    for mount, disk_info in data.get("disk", {}).items():
        disk_fields = {
            "total_gb": disk_info.get("total_gb"),
            "free_gb": disk_info.get("free_gb"),
            "percent": disk_info.get("percent"),
        }
        write_point("system_disk", {"node_name": data.get("node_name", ""), "mount": mount},
                    {k: v for k, v in disk_fields.items() if v is not None}, ts, node_id)

    for iface, net_info in data.get("network", {}).items():
        net_fields = {
            "bytes_sent": net_info.get("bytes_sent"),
            "bytes_recv": net_info.get("bytes_recv"),
            "tx_mbit_s": net_info.get("tx_mbit_s"),
            "rx_mbit_s": net_info.get("rx_mbit_s"),
            "link_mbit": net_info.get("link_mbit"),
            "tx_percent": net_info.get("tx_percent"),
            "rx_percent": net_info.get("rx_percent"),
        }
        write_point("system_network", {"node_name": data.get("node_name", ""), "interface": iface},
                    {k: v for k, v in net_fields.items() if v is not None}, ts, node_id)

    if temp:
        write_point("system_temperature", {"node_name": data.get("node_name", "")},
                    {k: float(v) for k, v in temp.items()}, ts, node_id)

    write_point("system_uptime", {"node_name": data.get("node_name", "")},
                {"uptime_seconds": data.get("uptime_seconds")}, ts, node_id)


def store_gpu_metric(data: dict) -> None:
    node_id = data.get("node_id", "unknown")
    ts = data.get("timestamp", datetime.now(timezone.utc).isoformat())
    fields = {
        "utilization_percent": data.get("utilization_percent"),
        "memory_used_mb": data.get("memory_used_mb"),
        "memory_total_mb": data.get("memory_total_mb"),
        "temperature_c": data.get("temperature_c"),
    }
    write_point("gpu", {"node_name": data.get("node_name", "")},
                {k: v for k, v in fields.items() if v is not None}, ts, node_id)


def store_models_metric(data: dict) -> None:
    node_id = data.get("node_id", "unknown")
    ts = data.get("timestamp", datetime.now(timezone.utc).isoformat())

    write_point("models_overview", {"node_name": data.get("node_name", "")},
                {
                    "requests_total": data.get("requests_total"),
                    "errors_total": data.get("errors_total"),
                    "uptime_seconds": data.get("uptime_seconds"),
                }, ts, node_id)

    for m in data.get("per_model", {}).values():
        model_name = m.get("model", "unknown")
        fields = {
            "requests": m.get("requests"),
            "errors": m.get("errors"),
            "avg_latency_ms": m.get("avg_latency_ms"),
            "tokens_generated": m.get("tokens_generated"),
            "avg_tokens_per_second": m.get("avg_tokens_per_second"),
        }
        write_point("model_performance", {"node_name": data.get("node_name", ""), "model": model_name},
                    {k: v for k, v in fields.items() if v is not None}, ts, node_id)

    for loaded in data.get("loaded", []):
        fields = {
            "api_port": loaded.get("api_port"),
            "nodes": loaded.get("nodes"),
            "gpu_memory_utilization": loaded.get("gpu_memory_utilization"),
            "max_model_len": loaded.get("max_model_len"),
        }
        tags = {"node_name": data.get("node_name", ""), "model": loaded.get("model", ""), "status": loaded.get("status", "")}
        write_point("model_loaded", tags,
                    {k: v for k, v in fields.items() if v is not None}, ts, node_id)


def store_cluster_metric(data: dict) -> None:
    node_id = data.get("node_id", "unknown")
    ts = data.get("timestamp", datetime.now(timezone.utc).isoformat())

    write_point("cluster", {"node_name": data.get("node_name", "")},
                {
                    "nodes_total": data.get("nodes_total"),
                    "nodes_online": data.get("nodes_online"),
                    "vram_total_gb": data.get("vram_total_gb"),
                }, ts, node_id)

    for n in data.get("nodes", []):
        fields = {
            "gpu_memory_gb": n.get("gpu_memory_gb"),
            "gpu_memory_used_percent": n.get("gpu_memory_used_percent"),
        }
        write_point("cluster_node", {"node_name": n.get("node_name", ""), "node_id": n.get("node_id", ""), "status": n.get("status", ""), "model": n.get("model", "")},
                    {k: v for k, v in fields.items() if v is not None}, ts, node_id)


def query_latest(measurement: str, node_id: str = None, limit: int = 1) -> list:
    filter_node = f' and node_id="{node_id}"' if node_id else ""
    q = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == "{measurement}"{filter_node})
      |> last()
      |> limit(n: {limit})
    '''
    try:
        tables = query_api.query(q, org=INFLUX_ORG)
        return tables
    except Exception as e:
        logger.error(f"Query error: {e}")
        return []


def query_range(measurement: str, start: str, end: str = None, node_id: str = None, field: str = None) -> list:
    filter_node = f' and node_id="{node_id}"' if node_id else ""
    filter_field = f' and r._field == "{field}"' if field else ""
    q = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start}, stop: {end})
      |> filter(fn: (r) => r._measurement == "{measurement}"{filter_node}{filter_field})
      |> mean()
    '''
    try:
        tables = query_api.query(q, org=INFLUX_ORG)
        return tables
    except Exception as e:
        logger.error(f"Query error: {e}")
        return []


def query_timeseries(measurement: str, start: str, end: str = None, node_id: str = None, field: str = None, group_by: list = None) -> list:
    filter_node = f' and node_id="{node_id}"' if node_id else ""
    filter_field = f' and r._field == "{field}"' if field else ""
    group_clause = ""
    if group_by:
        group_tags = ", ".join(group_by)
        group_clause = f'|> group(columns: [{group_tags}])'
    q = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start}, stop: {end})
      |> filter(fn: (r) => r._measurement == "{measurement}"{filter_node}{filter_field})
      |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
      {group_clause}
    '''
    try:
        tables = query_api.query(q, org=INFLUX_ORG)
        return tables
    except Exception as e:
        logger.error(f"Query error: {e}")
        return []


def get_all_node_ids() -> list:
    q = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -24h)
      |> keys()
      |> filter(fn: (r) => r._field == "node_id")
      |> distinct(column: "_value")
    '''
    try:
        tables = query_api.query(q, org=INFLUX_ORG)
        nodes = []
        for table in tables:
            for record in table.records:
                val = record.get_value()
                if val and val not in nodes:
                    nodes.append(val)
        return nodes
    except Exception:
        return []


def get_latest_system(node_id: str = None) -> dict:
    result = {"cpu": {}, "memory": {}, "disk": [], "network": [], "temperature": {}, "uptime": 0}
    measurements = [
        ("system_cpu", "cpu"), ("system_memory", "memory"),
        ("system_disk", "disk"), ("system_network", "network"),
        ("system_temperature", "temperature"), ("system_uptime", "uptime")
    ]
    for meas, key in measurements:
        tables = query_latest(meas, node_id)
        for table in tables:
            for record in table.records:
                field = record.get_field()
                value = record.get_value()
                tag_dict = record.get_tags()
                if key in ("disk", "network"):
                    item = {"value": value, "field": field, "tags": tag_dict}
                    result[key].append(item)
                elif key == "temperature":
                    if field and value is not None:
                        result[key][field] = value
                elif key == "uptime":
                    result[key] = value or 0
                else:
                    if field and value is not None:
                        result[key][field] = value
    return result


def get_latest_gpu(node_id: str = None) -> dict:
    result = {}
    tables = query_latest("gpu", node_id)
    for table in tables:
        for record in table.records:
            field = record.get_field()
            value = record.get_value()
            if field and value is not None:
                result[field] = value
    return result


def get_latest_models(node_id: str = None) -> dict:
    result = {"overview": {}, "per_model": [], "loaded": []}
    tables = query_latest("models_overview", node_id)
    for table in tables:
        for record in table.records:
            f = record.get_field()
            v = record.get_value()
            if f:
                result["overview"][f] = v
    tables = query_latest("model_performance", node_id)
    for table in tables:
        for record in table.records:
            tags = record.get_tags()
            f = record.get_field()
            v = record.get_value()
            model_name = tags.get("model", "unknown")
            entry = {"model": model_name}
            if f:
                entry[f] = v
            result["per_model"].append(entry)
    tables = query_latest("model_loaded", node_id)
    for table in tables:
        for record in table.records:
            tags = record.get_tags()
            f = record.get_field()
            v = record.get_value()
            entry = {"model": tags.get("model", ""), "status": tags.get("status", "")}
            if f:
                entry[f] = v
            result["loaded"].append(entry)
    return result


def get_latest_cluster() -> dict:
    result = {"overview": {}, "nodes": []}
    tables = query_latest("cluster")
    for table in tables:
        for record in table.records:
            f = record.get_field()
            v = record.get_value()
            if f:
                result["overview"][f] = v
    tables = query_latest("cluster_node")
    for table in tables:
        for record in table.records:
            tags = record.get_tags()
            f = record.get_field()
            v = record.get_value()
            entry = {
                "node_id": tags.get("node_id", ""),
                "node_name": tags.get("node_name", ""),
                "status": tags.get("status", ""),
                "model": tags.get("model", ""),
            }
            if f:
                entry[f] = v
            result["nodes"].append(entry)
    return result


def query_day_stats(date_str: str, node_id: str = None) -> dict:
    start = f'"20{date_str}T00:00:00Z"' if len(date_str) == 8 else f'"{date_str}T00:00:00Z"'
    end = f'"20{date_str}T23:59:59Z"' if len(date_str) == 8 else f'"{date_str}T23:59:59Z"'
    filter_node = f' and node_id="{node_id}"' if node_id else ""

    stats = {
        "cpu": {}, "gpu": {}, "memory": {}, "network": {}, "models": {}
    }

    queries = [
        ("system_cpu", "cpu", ["percent", "load_1m"]),
        ("gpu", "gpu", ["utilization_percent", "temperature_c"]),
        ("system_memory", "memory", ["percent", "used_mb"]),
        ("model_performance", "models", ["requests", "errors", "avg_latency_ms", "tokens_generated"]),
    ]

    for meas, key, fields in queries:
        for field in fields:
            filter_field = f' and r._field == "{field}"'
            q = f'''
            from(bucket: "{INFLUX_BUCKET}")
              |> range(start: {start}, stop: {end})
              |> filter(fn: (r) => r._measurement == "{meas}"{filter_node}{filter_field})
              |> quantile(q: 0.5)
              |> keep(columns: ["_value", "node_id", "model"])
            '''
            try:
                tables = query_api.query(q, org=INFLUX_ORG)
                for table in tables:
                    for record in table.records:
                        stats[key][field] = record.get_value()
            except Exception:
                pass

    return stats
