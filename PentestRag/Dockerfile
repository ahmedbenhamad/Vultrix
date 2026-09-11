FROM python:3.11-slim

# Prevent caching and keep python terminal output clean
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system-level dependencies
# Tesseract-ocr is required for the new Image Ingestion (OCR) feature.
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies first to optimize Docker build caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code into the container
COPY . .
COPY ./qdrant_baked_data /app/qdrant_baked_data
# Expose the API ports
EXPOSE 8000 8001

# Set default start command to the API server
CMD ["python", "main.py", "--serve"]
