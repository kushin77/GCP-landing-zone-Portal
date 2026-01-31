#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/backend:$(pwd)
export TEST_MODE=true
export ENVIRONMENT=test
export REQUIRE_AUTH=false
export ALLOW_DEV_BYPASS=true

# Create __init__.py if missing
touch backend/__init__.py

pytest backend/tests "$@"
