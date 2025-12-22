FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nmap \
    git \
    wget \
    ca-certificates \
    golang \
    && rm -rf /var/lib/apt/lists/*

# Install Subfinder using Go (SAFE & STABLE)
RUN go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# Make sure Go bin is in PATH
ENV PATH="/root/go/bin:${PATH}"

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
