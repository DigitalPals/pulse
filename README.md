# <img src="https://uptime.cybex.net/img/logo/cybex-pulse.svg" alt="Cybex Pulse Logo" width="40"/> Cybex Pulse

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-green.svg)](https://github.com/cybex/Pulse)

A powerful home network monitoring tool that provides real-time insights into your network devices, internet performance, and security threats.

## 🚀 Features

- **Network Discovery** - Automatically detect and monitor all devices on your network
- **Device Fingerprinting** - Identify device types, vendors, and models
- **Internet Health** - Track speed, latency, and reliability over time
- **Website Monitoring** - Monitor the availability of your important websites
- **Security Scanning** - Detect potential security vulnerabilities
- **Real-time Alerts** - Get notified when new devices join or important devices go offline
- **Beautiful Dashboard** - Intuitive web interface for managing all aspects of your network

## 📋 Requirements

- Linux-based operating system (Debian, Ubuntu, Fedora, CentOS, etc.)
- Root privileges (required for network scanning and device fingerprinting)
- Python 3.6 or higher

## 💻 Installation

### Quick Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/cybex/Pulse.git
cd Pulse

# Run installation script with root privileges
sudo ./install.sh
```

### Manual Installation

1. Clone this repository
```bash
git clone https://github.com/cybex/Pulse.git
cd Pulse
```

2. Set up a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r cybex_pulse/requirements.txt
pip install -e .
```

4. Run the application
```bash
./pulse
```

## ⚙️ Configuration

On first run, Cybex Pulse will create a default configuration file in `~/.cybex_pulse/config.json`. 
You can modify this file directly or use the web interface to adjust settings.

## 🌐 Access the Web Interface

By default, the web interface is available at:
- URL: http://YOUR_IP_ADDRESS:8000

## 🔐 Why Root Privileges Are Required

Cybex Pulse requires root privileges for several reasons:
- **Network Scanning**: To perform comprehensive network scans using tools like nmap
- **ARP Table Access**: To monitor device presence on the network
- **Port Binding**: To bind to privileged ports for certain monitoring functions
- **System Service Installation**: To install and run as a system service

## 🐳 Running on Proxmox Containers

When running Cybex Pulse in a Proxmox container, you need to ensure the container has:

1. **Unprivileged Mode Access**:
   - Set the container as unprivileged in Proxmox
   - Add the following features to the container:
     ```
     features: keyctl=1,nesting=1
     ```

2. **Required Capabilities**:
   ```
   lxc.cap.drop: 
   lxc.cap.keep: sys_admin sys_nice sys_resource sys_time setgid setuid net_bind_service net_admin net_raw
   ```

3. **Additional Network Configuration**:
   - Ensure the container has its own network interface in bridge mode

## 📊 Screenshots

<div align="center">
  <img src="cybex_pulse/docs/dashboard.png" alt="Dashboard" width="45%"/>
  <img src="cybex_pulse/docs/devices.png" alt="Devices" width="45%"/>
</div>

## 🛠️ Service Management

```bash
# Start the service
sudo systemctl start cybex-pulse

# Stop the service
sudo systemctl stop cybex-pulse

# Restart the service
sudo systemctl restart cybex-pulse

# Check status
sudo systemctl status cybex-pulse

# View logs
sudo journalctl -u cybex-pulse
```

## 📄 License

This project is licensed under the terms of the MIT license included in the repository.