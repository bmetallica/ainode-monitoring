#!/bin/bash
# InfluxDB init - create buckets and generate API token
echo "Running InfluxDB init script..."
influx bucket create --name history-7d --org ainode --retention 168h || true
influx bucket create --name history-30d --org ainode --retention 720h || true
# Generate API token with read/write permissions
TOKEN=$(influx auth create --description "ainode-monitor" --org ainode --read-buckets --write-buckets | awk 'NR==2{print $3}')
if [ -n "$TOKEN" ]; then
  echo "$TOKEN" > /shared/influx_token.txt
  echo "Token written to /shared/influx_token.txt"
else
  echo "ERROR: Failed to generate token"
fi
