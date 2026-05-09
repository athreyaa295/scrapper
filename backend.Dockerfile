# Dockerfile for Backend
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY backend/ .

# Expose port
EXPOSE 8000

# Run uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
