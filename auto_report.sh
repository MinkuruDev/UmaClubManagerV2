#! /usr/bin/bash

echo "$(date) Starting $0"
SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR/"
export $(cat .env | xargs)

attempts=5
count=0
while [ $count -lt $attempts ]; do
    curl -f -X POST "http://localhost:3636/full_update" -H "Authorization: Bearer $ADMIN_TOKEN" -d "" && \
        curl -f -X POST "http://localhost:3636/fan_data/report_discord" -H "Authorization: Bearer $ADMIN_TOKEN" -d "" && \
        break
    count=$((count + 1))
    echo "Attempt $count failed"
    if [ $count -eq $attempts ]; then
        echo "$(date) All attempts failed. Exiting."
        exit 1
    fi
    echo "Retrying in $((60 * $count)) seconds..."
    sleep $((60 * $count))
done

echo "$(date) Finished $0"
