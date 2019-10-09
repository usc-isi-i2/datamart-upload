#!/bin/sh

python3 worker/rq_worker.py &
# python3 webapp-openapi.py
cd datamart_web
python3 generate_dataset_metadata.py
gunicorn webapp-openapi:app -b 0.0.0.0:9000 -w 20 --preload --timeout 1800
