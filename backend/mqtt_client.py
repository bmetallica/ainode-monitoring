import asyncio
import json
import logging
import threading
import time
from typing import Optional

import paho.mqtt.client as mqtt

from backend.config import load_config
from backend.influx import store_system_metric, store_gpu_metric, store_models_metric, store_cluster_metric

logger = logging.getLogger(__name__)

_mqtt_client: Optional[mqtt.Client] = None
_stop_event = threading.Event()


def _on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info("Connected to MQTT broker")
        cfg = userdata.get("config", {})
        prefix = cfg.get("topic_prefix", "").rstrip("/")
        if prefix:
            topics = [
                f"{prefix}/+/system",
                f"{prefix}/+/gpu",
                f"{prefix}/+/models",
                f"{prefix}/cluster",
            ]
            for topic in topics:
                client.subscribe(topic)
                logger.info(f"Subscribed to {topic}")
    else:
        logger.error(f"MQTT connection failed with code {rc}")


def _on_message(client, userdata, msg):
    topic = msg.topic
    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(f"Invalid JSON on topic {topic}: {e}")
        return

    parts = topic.split("/")

    if len(parts) >= 3 and parts[-1] == "system":
        node_id = parts[-2]
        data["node_id"] = data.get("node_id", node_id)
        store_system_metric(data)
        logger.debug(f"Stored system metric for node {node_id}")

    elif len(parts) >= 3 and parts[-1] == "gpu":
        node_id = parts[-2]
        data["node_id"] = data.get("node_id", node_id)
        store_gpu_metric(data)
        logger.debug(f"Stored GPU metric for node {node_id}")

    elif len(parts) >= 3 and parts[-1] == "models":
        node_id = parts[-2]
        data["node_id"] = data.get("node_id", node_id)
        store_models_metric(data)
        logger.debug(f"Stored models metric for node {node_id}")

    elif len(parts) == 2 and parts[-1] == "cluster":
        store_cluster_metric(data)
        logger.debug("Stored cluster metric")

    else:
        logger.debug(f"Unmatched topic: {topic}")


def _run_mqtt_loop(config: dict):
    global _mqtt_client
    _mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    _mqtt_client.user_data_set({"config": config})

    if config.get("user"):
        _mqtt_client.username_pw_set(config["user"], config.get("password", ""))

    try:
        _mqtt_client.on_connect = _on_connect
        _mqtt_client.on_message = _on_message
        _mqtt_client.connect(config["broker"], config.get("port", 1883), 60)
        _mqtt_client.loop_start()
    except Exception as e:
        logger.error(f"Failed to start MQTT client: {e}")
        return

    while not _stop_event.is_set():
        _stop_event.wait(1)

    _mqtt_client.loop_stop()
    _mqtt_client.disconnect()
    _mqtt_client = None
    logger.info("MQTT client stopped")


def start_mqtt():
    cfg = load_config()
    if not cfg.get("broker") or not cfg.get("topic_prefix"):
        logger.warning("MQTT not configured — skipping connection")
        return

    _stop_event.clear()
    thread = threading.Thread(target=_run_mqtt_loop, args=(cfg,), daemon=True)
    thread.start()
    logger.info("MQTT subscriber thread started")


def stop_mqtt():
    _stop_event.set()
    logger.info("MQTT stop requested")


def is_connected() -> bool:
    return _mqtt_client is not None and _mqtt_client.is_connected()
