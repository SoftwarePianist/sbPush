FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# Copy requirements first to leverage cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install system dependencies with robust timezone setup
RUN echo "tzdata tzdata/Areas select Asia" | debconf-set-selections && \
    echo "tzdata tzdata/Zones/Asia select Shanghai" | debconf-set-selections && \
    DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y tzdata && \
    rm -rf /var/lib/apt/lists/*

# Install Playwright browsers (we only need chromium)
RUN playwright install chromium

# Copy application code
COPY . .

# Set timezone
ENV TZ=Asia/Shanghai

# Command to run the monitor
CMD ["python", "main.py", "monitor"]
