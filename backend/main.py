import os
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from backend import config as cfg_module
from backend import mqtt_client
from backend.influx import (
    get_latest_system,
    get_latest_gpu,
    get_latest_models,
    get_latest_cluster,
    query_timeseries,
    get_all_node_ids,
    query_day_stats,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="AINode Monitor")

FRONTEND = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND / "static")), name="static")
templates = Jinja2Templates(directory=str(FRONTEND / "templates"))


class MQTTConfigRequest(BaseModel):
    broker: str
    port: int = 1883
    user: str = ""
    password: str = ""
    topic_prefix: str


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/config")
async def get_config():
    c = cfg_module.load_config()
    c["connected"] = mqtt_client.is_connected()
    return c


@app.post("/api/config")
async def set_config(req: MQTTConfigRequest):
    c = cfg_module.load_config()
    c["broker"] = req.broker
    c["port"] = req.port
    c["user"] = req.user
    c["password"] = req.password
    c["topic_prefix"] = req.topic_prefix
    cfg_module.save_config(c)

    mqtt_client.stop_mqtt()
    mqtt_client.start_mqtt()

    c["connected"] = mqtt_client.is_connected()
    return c


@app.get("/api/live/system")
async def live_system(node_id: str = None):
    return get_latest_system(node_id)


@app.get("/api/live/gpu")
async def live_gpu(node_id: str = None):
    return get_latest_gpu(node_id)


@app.get("/api/live/models")
async def live_models(node_id: str = None):
    return get_latest_models(node_id)


@app.get("/api/live/cluster")
async def live_cluster():
    return get_latest_cluster()


@app.get("/api/nodes")
async def list_nodes():
    return get_all_node_ids()


@app.get("/api/history/timeseries")
async def history_timeseries(
    measurement: str,
    field: str = None,
    hours: int = 24,
    node_id: str = None,
):
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    tables = query_timeseries(measurement, start.isoformat(), end.isoformat(), node_id, field)
    series = []
    for table in tables:
        points = []
        for record in table.records:
            points.append({
                "time": str(record.get_time()),
                "value": record.get_value(),
                "node_id": record.get_tags().get("node_id", ""),
                "model": record.get_tags().get("model", ""),
            })
        series.append(points)
    return series


@app.get("/api/history/day")
async def history_day(date: str, node_id: str = None):
    return query_day_stats(date, node_id)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/status")
async def status():
    return {
        "mqtt_connected": mqtt_client.is_connected(),
        "config": cfg_module.load_config(),
    }


@app.on_event("startup")
async def startup():
    mqtt_client.start_mqtt()
