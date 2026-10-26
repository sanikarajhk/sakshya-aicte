#!/bin/bash
set -e

# Port configuration (supports cloud environments with dynamic $PORT)
STREAMLIT_PORT="${PORT:-8501}"
API_PORT="${API_PORT:-8000}"

echo "🚀 Starting Sakshya AICTE Validation Engine..."

# Ensure synthetic dataset and SQLite database are initialized
if [ ! -f "sakshya/data/ground_truth.json" ]; then
    echo "📦 Initializing synthetic dataset and database..."
    python3 -m sakshya.data_generator.generator
fi

# Start FastAPI background REST service
echo "🌐 Launching FastAPI REST API on port ${API_PORT}..."
python3 -m uvicorn sakshya.api.main:app --host 0.0.0.0 --port "${API_PORT}" &
API_PID=$!

# Wait briefly for API to bind
sleep 2

# Start Streamlit Frontend
echo "📊 Launching Streamlit Portal on port ${STREAMLIT_PORT}..."
python3 -m streamlit run sakshya/dashboard/app.py \
    --server.port="${STREAMLIT_PORT}" \
    --server.address=0.0.0.0 \
    --server.headless=true

# Wait for background jobs
wait $API_PID
