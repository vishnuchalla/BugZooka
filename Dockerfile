FROM python:3.11

# Install gsutil and dependencies securely
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    bzip2 \
    gnupg \
    ca-certificates \
    apt-transport-https \
    lsb-release && \
    curl -sSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" \
    > /etc/apt/sources.list.d/google-cloud-sdk.list && \
    apt-get update && \
    apt-get install -y google-cloud-sdk && \
    apt-get clean

# Get latest version tag dynamically and download + install binary
RUN set -eux; \
    LATEST_VERSION=$(curl -s https://api.github.com/repos/logjuicer/logjuicer/releases/latest | jq -r .tag_name); \
    DOWNLOAD_URL="https://github.com/logjuicer/logjuicer/releases/download/${LATEST_VERSION}/logjuicer-x86_64-linux.tar.bz2"; \
    curl -L "$DOWNLOAD_URL" -o /tmp/logjuicer.tar.bz2; \
    tar -xjf /tmp/logjuicer.tar.bz2 -C /usr/local/; \
    chmod +x /usr/local/bin/logjuicer; \
    rm /tmp/logjuicer.tar.bz2

# Set working directory
WORKDIR /app

# Copy source code
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Disable buffering
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python3", "slack.py"]
