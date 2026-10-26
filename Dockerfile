# Sakshya - AICTE Application Validation Engine
# Multi-Service Container (Streamlit Dashboard + FastAPI REST Service)

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies for OCR (Tesseract), Vision (OpenCV), and QR decoding (ZBar)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-hin \
    libzbar0 \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure start script has executable permissions
RUN chmod +x start.sh

# Pre-generate synthetic data and initialize SQLite database in the image
RUN python3 -m sakshya.data_generator.generator

# Expose ports for Streamlit (8501) and FastAPI (8000)
EXPOSE 8501 8000

# Healthcheck for container orchestrators
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Default launch command
CMD ["./start.sh"]
