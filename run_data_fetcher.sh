#!/bin/bash

export PATH="/root/.local/bin:$PATH"

cd /root/caner
uv run --project /root/caner data_fetcher.py
