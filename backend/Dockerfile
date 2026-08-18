FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Expose the API port
EXPOSE 8000

# Start the application using the entrypoint script
CMD ["./entrypoint.sh"]
