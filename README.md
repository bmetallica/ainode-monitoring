# AI Node Monitoring Dashboard

Real-time monitoring dashboard for LLM inference clusters, powered by MQTT, InfluxDB, and FastAPI.

## Architecture

```
LLM Nodes → MQTT Broker → Backend (FastAPI) → InfluxDB
                              ↘ Frontend (Chart.js Dashboard :3030)
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Access to an MQTT broker (e.g., Mosquitto, EMQX)

### Setup

```bash
git clone https://github.com/<your-username>/ainode-monitoring.git
cd ainode-monitoring
docker compose up -d
```

The dashboard will be available at **http://localhost:3030**.

### Configuration

1. Open the dashboard at `http://localhost:3030`
2. Click **Settings** in the top-right corner
3. Enter your MQTT broker connection details:
   - Broker hostname/IP
   - Port (default: 1883)
   - Topic prefix (e.g., `ainode`)
   - Username/Password (if required)
4. Click **Save** — settings persist across restarts

## MQTT Topic Structure

The backend subscribes to the following topics (replace `<prefix>` with your configured prefix):

| Topic | Description |
|-------|-------------|
| `<prefix>/<node-id>/system` | CPU, memory, disk, network metrics per node |
| `<prefix>/<node-id>/gpu` | GPU utilization, memory, temperature, power per node |
| `<prefix>/<node-id>/models` | Loaded models, active requests, token throughput per node |
| `<prefix>/cluster` | Aggregate cluster-wide statistics (sent by Head node only) |

### Payload Examples

**System** (`<prefix>/<node-id>/system`):
```json
{
  "node_id": "node-01",
  "cpu_percent": 45.2,
  "memory_total": 135000000000,
  "memory_used": 89000000000,
  "memory_cached": 12000000000,
  "disk_total": 2000000000000,
  "disk_used": 1200000000000,
  "network_interfaces": [
    {
      "name": "eth0",
      "speed": 10000,
      "bytes_sent": 1234567890,
      "bytes_recv": 9876543210
    }
  ]
}
```

**GPU** (`<prefix>/<node-id>/gpu`):
```json
{
  "node_id": "node-01",
  "gpus": [
    {
      "index": 0,
      "utilization": 92.5,
      "memory_used": 78000000000,
      "memory_total": 81000000000,
      "temperature": 78,
      "power_draw": 380
    }
  ]
}
```

**Models** (`<prefix>/<node-id>/models`):
```json
{
  "node_id": "node-01",
  "models": [
    {
      "name": "llama-3-70b",
      "active_requests": 12,
      "queue_size": 3,
      "avg_tokens_per_second": 45.2,
      "gpu_memory_used": 60000000000
    }
  ]
}
```

**Cluster** (`<prefix>/cluster`):
```json
{
  "total_nodes": 8,
  "active_nodes": 7,
  "total_gpus": 64,
  "active_gpus": 56,
  "total_requests": 150,
  "queued_requests": 22
}
```

## Dashboard Features

- **Real-time Metrics**: Auto-refreshing system, GPU, model, and cluster data
- **Historical Charts**: Filter by day to view past performance trends
- **Interactive Visualizations**: Line graphs, pie charts, and bar charts
- **Dark Theme**: Easy on the eyes for monitoring environments
- **Node Comparison**: Per-node breakdowns for all metric categories

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/api/config` | GET/PUT | MQTT connection settings |
| `/api/live/system` | GET | Latest system metrics per node |
| `/api/live/gpu` | GET | Latest GPU metrics per node |
| `/api/live/models` | GET | Latest model metrics per node |
| `/api/live/cluster` | GET | Latest cluster-wide metrics |
| `/api/history/day` | GET | Historical data for a given day (`?date=YYYY-MM-DD`) |
| `/api/nodes` | GET | List of known node IDs |

## Project Structure

```
├── backend/
│   ├── config.py      # Persistent MQTT config management
│   ├── influx.py      # InfluxDB client (write/query)
│   ├── main.py        # FastAPI app + REST routes
│   ├── models.py      # Dataclass definitions for MQTT payloads
│   └── mqtt_client.py # MQTT subscriber + topic routing
├── frontend/
│   ├── static/
│   │   ├── css/style.css   # Dark theme styling
│   │   └── js/dashboard.js # Chart.js rendering + API polling
│   └── templates/
│       └── index.html      # Dashboard layout
├── docker-compose.yml      # InfluxDB + webapp services
├── Dockerfile              # Python 3.11 webapp image
├── influxdb-init.sh        # InfluxDB bucket initialization
└── requirements.txt        # Python dependencies
```

## Network Interface Filtering

The backend automatically excludes these interfaces from network metrics:
- `lo` (loopback)
- `docker0` (Docker bridge)
- `veth*` (Docker veth pairs)
- `br-*` (bridge interfaces)

## Troubleshooting

- **Dashboard shows no data**: Verify MQTT broker connectivity in Settings, and ensure nodes are publishing to the correct topic prefix.
- **InfluxDB errors**: Check `docker compose logs influxdb` for initialization issues.
- **Port conflicts**: The dashboard runs on port 3030. Change it in `docker-compose.yml` if needed.
