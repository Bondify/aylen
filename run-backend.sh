#!/bin/bash

# Script to run the FastAPI backend server
echo "Starting Legal AI Backend..."
echo "Backend will be available at: http://localhost:8000"
echo "API docs will be available at: http://localhost:8000/docs"
echo ""

# Activate virtual environment and run the backend
uv run python backend/api.py