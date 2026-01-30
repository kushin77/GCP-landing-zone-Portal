#!/bin/bash
sleep 2
curl -X POST http://localhost:8082/api/v1/analysis/rca \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Issue", "description": "This is a test issue for RCA analysis", "labels": ["bug"], "assignees": ["testuser"]}'