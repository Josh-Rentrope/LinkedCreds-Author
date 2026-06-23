# backend/Dockerfile
FROM python:3.11-slim

# Set the working directory to /app inside the container
WORKDIR /app

# Install system dependencies (often needed for compiling certain Python packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements first to leverage Docker's layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download the required spaCy models
RUN python -m spacy download en_core_web_lg
RUN python -m spacy download en_core_web_trf

# Copy the rest of the backend source code
COPY . .

# Expose the port your App Runner was using
EXPOSE 8080

# Start the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]