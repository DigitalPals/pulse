FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV INSTALL_DIR=/opt/pulse

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    nmap \
    net-tools \
    iproute2 \
    sudo \
    snmp \
    arp-scan \
    avahi-utils \
    avahi-daemon \
    libnss-mdns \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /var/log/cybex_pulse /var/lib/cybex_pulse

# Set working directory
WORKDIR /opt/pulse

# Copy the application
COPY . /opt/pulse/

# Install Python dependencies
RUN pip install --no-cache-dir -r cybex_pulse/requirements.txt

# Make the pulse script executable
RUN chmod +x /opt/pulse/pulse

# Expose the web interface port
EXPOSE 8080

# Set the entrypoint
ENTRYPOINT ["/opt/pulse/pulse"]