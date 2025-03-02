<div align="center">
  <img src="https://uptime.cybex.net/img/logo/cybex-pulse.svg" alt="Cybex Pulse Logo" width="120"/>
  
  <p>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
    <a href="https://github.com/DigitalPals/pulse"><img src="https://img.shields.io/badge/Version-1.0.0-green.svg" alt="Version"></a>
  </p>
</div>

<div align="center">
  <p><strong>A powerful home network monitoring tool that provides real-time insights into your network devices, internet performance, and security threats.</strong></p>
  <p><em>Keep your home network safe, optimized, and always under your control</em></p>

  <a href="#installation">Installation</a> •
  <a href="#features">Features</a> •
  <a href="#screenshots">Screenshots</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#license">License</a>
</div>

---

<div align="center">
  <h3>🚀 Quick Start</h3>
</div>

```bash
# One-line installation (Debian/Ubuntu)
curl -sSL https://github.com/DigitalPals/pulse/install.sh | sudo bash

# Access the web interface
# http://YOUR_IP_ADDRESS:8000
```

---

## 🚀 Features

### 🔍 Network Discovery
Automatically detect and monitor all devices on your network with intelligent periodic scanning that helps you identify every device connected to your home network.

### 👆 Device Fingerprinting
Identify device types, vendors, and models through advanced classification algorithms that can recognize thousands of different devices.

### 📊 Internet Health
Track speed, latency, and reliability over time with detailed historical metrics to ensure your internet connection is performing as expected.

### 🌐 Website Monitoring
Monitor the availability of your important websites and receive alerts when they're down, ensuring you're always aware of service disruptions.

### 🔐 Security Scanning
Detect potential security vulnerabilities and unprotected devices on your network to help safeguard your home against threats.

### ⚡ Real-time Alerts
Get notified when new devices join, important devices go offline, or security issues arise, giving you complete visibility into your network.

### ✨ Beautiful Dashboard
Intuitive web interface for managing all aspects of your network with responsive design for mobile and desktop, making network management easy.

## 📋 Requirements

<table>
  <tr>
    <td><strong>🐧 Operating System</strong></td>
    <td>Linux-based OS (Debian, Ubuntu, Fedora, CentOS, etc.)</td>
  </tr>
  <tr>
    <td><strong>🔑 Privileges</strong></td>
    <td>Root access (required for network scanning and device fingerprinting)</td>
  </tr>
  <tr>
    <td><strong>🐍 Python</strong></td>
    <td>Python 3.6 or higher with pip</td>
  </tr>
  <tr>
    <td><strong>🌐 Network</strong></td>
    <td>Ethernet or WiFi connection with access to your local network</td>
  </tr>
  <tr>
    <td><strong>💾 Storage</strong></td>
    <td>At least 500MB free disk space for installation and database</td>
  </tr>
</table>

## 💻 Installation

<details open>
<summary><strong>Quick Install (Recommended)</strong></summary>

The quick installation method will automatically set up everything you need, including dependencies, service configuration, and initial database setup.

```bash
# Clone the repository
git clone https://github.com/cybex/Pulse.git
cd Pulse

# Run installation script with root privileges
sudo ./install.sh
```

Once installed, the service will automatically start and be configured to run on system boot.
</details>

<details>
<summary><strong>Manual Installation</strong></summary>

If you prefer to control each step of the installation process, follow these instructions:

#### 1. Clone the Repository
```bash
git clone https://github.com/cybex/Pulse.git
cd Pulse
```

#### 2. Set Up a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
pip install -r cybex_pulse/requirements.txt
pip install -e .
```

#### 4. Initialize the Database
```bash
# Create initial database schema
python -m cybex_pulse.database.db_manager --init
```

#### 5. Run the Application
```bash
./pulse
```

For running as a service, create a systemd service file manually:
```bash
sudo nano /etc/systemd/system/cybex-pulse.service
```

Add the following content (adjust paths as needed):
```
[Unit]
Description=Cybex Pulse Network Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/Pulse
ExecStart=/opt/Pulse/pulse
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cybex-pulse
sudo systemctl start cybex-pulse
```
</details>

<details>
<summary><strong>Docker Installation</strong></summary>

For those who prefer containerized deployments, we provide a Docker image:

```bash
# Pull the image
docker pull cybex/pulse:latest

# Run with necessary network access
docker run -d \
  --name cybex-pulse \
  --network host \
  --cap-add NET_ADMIN \
  --cap-add NET_RAW \
  -v pulse-data:/opt/cybex-pulse/data \
  cybex/pulse:latest
```

**Note:** The container requires host networking and specific capabilities to perform network scanning.
</details>

## ⚙️ Configuration

<details open>
<summary><strong>Initial Setup</strong></summary>

On first run, Cybex Pulse will launch a setup wizard to guide you through the configuration process. 
The wizard helps you:

- Configure network interfaces for monitoring
- Set up email notifications (optional)
- Customize scanning intervals
- Configure security monitoring options

After initial setup, a configuration file is created at `~/.cybex_pulse/config.json`. 
You can modify this file directly or use the web interface settings panel.
</details>

<details>
<summary><strong>Advanced Configuration Options</strong></summary>

The configuration file supports the following advanced options:

```json
{
  "network": {
    "interfaces": ["eth0"],
    "scan_interval": 300,
    "exclude_ips": ["192.168.1.1"],
    "exclude_macs": ["00:11:22:33:44:55"]
  },
  "security": {
    "vuln_scan_enabled": true,
    "vuln_scan_interval": 86400,
    "port_scan_enabled": true
  },
  "monitoring": {
    "speed_test_interval": 3600,
    "website_check_interval": 300
  },
  "notifications": {
    "email": {
      "enabled": false,
      "smtp_server": "smtp.example.com",
      "smtp_port": 587,
      "username": "user@example.com",
      "password": "",
      "recipients": ["user@example.com"]
    },
    "pushover": {
      "enabled": false,
      "user_key": "",
      "app_token": ""
    }
  }
}
```
</details>

## 🌐 Web Interface

<div align="center">
  <table>
    <tr>
      <td><strong>Default URL</strong></td>
      <td>http://YOUR_IP_ADDRESS:8000</td>
    </tr>
  </table>
</div>

<p align="center">The web interface provides access to all monitoring features and configuration options</p>

## 🔐 Security Considerations

<details open>
<summary><strong>Why Root Privileges Are Required</strong></summary>

Cybex Pulse requires root privileges for several reasons:

- **Network Scanning**: To perform comprehensive network scans using tools like nmap
- **ARP Table Access**: To monitor device presence on the network
- **Port Binding**: To bind to privileged ports for certain monitoring functions
- **System Service Installation**: To install and run as a system service

We've designed the software to operate with the minimum necessary privileges while still providing powerful network monitoring capabilities.
</details>

<details>
<summary><strong>Data Privacy</strong></summary>

Cybex Pulse respects your privacy:

- All data is stored locally on your system
- No data is sent to external servers
- No telemetry or usage statistics are collected
- Network scan data never leaves your local network

The software only monitors devices on your local network and does not perform any external scanning or data collection beyond what you explicitly configure (like website monitoring).
</details>

## 🐳 Advanced Deployment Options

<details>
<summary><strong>Running on Proxmox Containers</strong></summary>

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
</details>

## 📊 Screenshots

<div align="center">
  <p><strong>Dashboard & Device Management</strong></p>
  <img src="cybex_pulse/docs/dashboard.png" alt="Dashboard" width="90%" style="max-width:800px"/>
  
  <p><strong>Network Map & Security Insights</strong></p>
  <img src="cybex_pulse/docs/devices.png" alt="Devices" width="90%" style="max-width:800px"/>
</div>

## 🛠️ Service Management

<table>
  <tr>
    <th colspan="2">Managing the Cybex Pulse Service</th>
  </tr>
  <tr>
    <td><strong>Start Service</strong></td>
    <td><code>sudo systemctl start cybex-pulse</code></td>
  </tr>
  <tr>
    <td><strong>Stop Service</strong></td>
    <td><code>sudo systemctl stop cybex-pulse</code></td>
  </tr>
  <tr>
    <td><strong>Restart Service</strong></td>
    <td><code>sudo systemctl restart cybex-pulse</code></td>
  </tr>
  <tr>
    <td><strong>Check Status</strong></td>
    <td><code>sudo systemctl status cybex-pulse</code></td>
  </tr>
  <tr>
    <td><strong>View Logs</strong></td>
    <td><code>sudo journalctl -u cybex-pulse</code></td>
  </tr>
  <tr>
    <td><strong>Enable at Boot</strong></td>
    <td><code>sudo systemctl enable cybex-pulse</code></td>
  </tr>
  <tr>
    <td><strong>Disable at Boot</strong></td>
    <td><code>sudo systemctl disable cybex-pulse</code></td>
  </tr>
</table>

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the terms of the MIT license included in the repository.

---

<div align="center">
  <p>Made with ❤️ by <a href="https://cybex.net">Cybex</a></p>
  <p>
    <a href="https://cybex.net">Website</a> •
    <a href="https://github.com/DigitalPals">GitHub</a> •
    <a href="https://twitter.com/CybexSecurity">Twitter</a>
  </p>
</div>