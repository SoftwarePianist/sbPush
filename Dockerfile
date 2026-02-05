FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# Copy requirements first to leverage cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (we only need chromium)
RUN playwright install chromium

# Copy application code
COPY . .

# Set timezone
ENV TZ=Asia/Shanghai

# Command to run the monitor
CMD ["python", "main.py", "monitor"]
