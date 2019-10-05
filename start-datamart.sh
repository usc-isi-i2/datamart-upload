#!/bin/sh

python3 worker/rq_worker.py &
python3 webapp-openapi.py
