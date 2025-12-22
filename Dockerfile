FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nmap \
    wget \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Subfinder
RUN wget https://github.com/projectdiscovery/subfinder/releases/latest/download/subfinder_2.6.3_linux_amd64.zip \
 && unzip subfinder_*.zip \
 && mv subfinder /usr/local/bin/subfinder \
 && chmod +x /usr/local/bin/subfinder \
 && rm subfinder_*.zip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
