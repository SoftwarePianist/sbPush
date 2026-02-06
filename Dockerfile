FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# Copy requirements first to leverage cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install system dependencies with robust non-interactive timezone setup
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*
ENV DEBIAN_FRONTEND=

# Install Playwright browsers (we only need chromium)
RUN playwright install chromium

# Copy application code
COPY . .

# Set timezone
ENV TZ=Asia/Shanghai

# Command to run the monitor
CMD ["python", "main.py", "monitor"]
