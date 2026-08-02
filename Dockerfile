# ExFlow Enterprise — Dockerfile
FROM python:3.11-slim

# Tesseract for OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Persist data outside the container image
VOLUME ["/app/data"]
ENV EXFLOW_ADMIN_PW=admin123

EXPOSE 8503 8000

# Default: run the main Streamlit app
CMD ["python3", "-m", "streamlit", "run", "app.py", "--server.port", "8503", "--server.address", "0.0.0.0"]
