#!/bin/bash
# InfluxDB init - create additional buckets for historical data retention
sleep 5
influx bucket create --name history-7d --org ainode --retention 168h 2>/dev/null || true
influx bucket create --name history-30d --org ainode --retention 720h 2>/dev/null || true
