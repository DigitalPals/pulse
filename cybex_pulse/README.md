# Cybex Pulse - Home Network Monitoring Application

Cybex Pulse is a comprehensive home network monitoring application designed to keep track of devices on your network, monitor internet performance, check website availability, and scan for security vulnerabilities.

![Cybex Pulse Dashboard](docs/dashboard.png)

## Features

### Core Features (MVP)

- **Network Guard**
  - Continuous scanning of local network for devices
  - Automatic registration of known devices
  - Real-time alerts when new devices connect or known devices go offline
  - Telegram notifications for important events

### Planned Features

- **Important Devices Monitoring**
  - Designate critical devices for priority monitoring
  - Immediate alerts if important devices go offline

- **Internet Health Check**
  - Periodic ISP speed tests
  - Latency monitoring with configurable thresholds
  - Historical performance tracking

- **External Website Monitoring**
  - Monitor up to 5 user-defined websites
  - Check response times and status codes
  - Alert on website errors or downtime

- **Network Security**
  - Port scanning for connected devices
  - Basic vulnerability checks
  - Security recommendations

- **Logging and Reporting**
  - Comprehensive event logging in SQLite database
  - Historical data retention with configurable policies
  - Periodic summary reports

- **Web Interface**
  - Real-time dashboard with device overview
  - Modern design with Catppuccin color scheme and nerdfonts
  - Configuration management
  - Historical data visualization

## Installation

### Prerequisites

- Python 3.8 or higher
- Elevated permissions for network scanning (sudo/root)
- The following tools:
  - `arp-scan` for network device discovery
  - `nmap` for security scanning (optional)

### Dependencies

Cybex Pulse requires the following Python packages:

```
flask
python-telegram-bot
speedtest-cli
python-nmap
requests
setuptools_scm
```

### Installation Steps

1. Clone the repository:

```bash
git clone https://github.com/yourusername/cybex-pulse.git
cd cybex-pulse
```

2. Install required packages:

```bash
pip install -r requirements.txt
```

The application automatically detects and displays its version at startup.

3. Install system dependencies:

```bash
# On Debian/Ubuntu
sudo apt-get install arp-scan nmap

# On Fedora/RHEL
sudo dnf install arp-scan nmap

# On Arch Linux
sudo pacman -S arp-scan nmap

# On macOS (using Homebrew)
brew install arp-scan nmap
```

## Usage

### First Run

On first run, Cybex Pulse will guide you through a setup wizard to configure the application:

```bash
python -m cybex_pulse
```

The setup wizard will help you configure:
- Network subnet to scan
- Telegram bot for notifications (optional)
- Web interface settings
- Monitoring features

### Running as a Service

For continuous operation, you can set up Cybex Pulse as a system service:

#### Systemd (Linux)

Create a service file at `/etc/systemd/system/cybex-pulse.service`:

```
[Unit]
Description=Cybex Pulse Network Monitor
After=network.target

[Service]
ExecStart=/usr/bin/python3 -m cybex_pulse
WorkingDirectory=/path/to/cybex-pulse
User=root
Group=root
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable cybex-pulse
sudo systemctl start cybex-pulse
```

#### LaunchAgent (macOS)

Create a plist file at `~/Library/LaunchAgents/com.yourusername.cybex-pulse.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yourusername.cybex-pulse</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>-m</string>
        <string>cybex_pulse</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/path/to/cybex-pulse</string>
    <key>StandardErrorPath</key>
    <string>/tmp/cybex-pulse.err</string>
    <key>StandardOutPath</key>
    <string>/tmp/cybex-pulse.out</string>
</dict>
</plist>
```

Load the service:

```bash
launchctl load ~/Library/LaunchAgents/com.yourusername.cybex-pulse.plist
```

### Web Interface

Once running, you can access the web interface at:

```
http://localhost:8080
```

Or at the host and port you configured during setup.

## Configuration

All configuration is stored in `~/.cybex_pulse/config.json` and can be modified through the web interface or by editing the file directly.

### Telegram Bot Setup

To use Telegram notifications:

1. Create a new bot by messaging [@BotFather](https://t.me/botfather) on Telegram
2. Follow the prompts to create a new bot and get the API token
3. Start a conversation with your bot
4. Get your chat ID by messaging [@userinfobot](https://t.me/userinfobot)
5. Enter these details in the Cybex Pulse settings

## Security Considerations

- Cybex Pulse requires elevated permissions to scan the network
- The web interface should be secured with a username and password
- Consider binding the web interface to localhost (127.0.0.1) for local-only access
- For remote access, consider using a reverse proxy with HTTPS

## Troubleshooting

### Common Issues

- **Network scanning not working**: Ensure you have installed `arp-scan` and are running with sufficient permissions
- **Speed tests failing**: Check your internet connection and ensure `speedtest-cli` is installed
- **Web interface not accessible**: Verify the configured host and port, and check for firewall rules

### Logs

Logs are stored in `~/.cybex_pulse/logs/cybex_pulse.log` and can be helpful for diagnosing issues.

## Versioning

Cybex Pulse uses an automatic versioning system that detects file changes and updates the version number accordingly:

- Version numbers follow the format: `MAJOR.MINOR.PATCH[-dev]`
- For development versions, the format includes `-dev` suffix: `0.1.2-dev`
- The version number automatically increments when file changes are detected

The application checks for changes at startup and automatically updates the version if needed. This happens completely automatically without any manual steps required.

### How It Works

1. When the application starts, it computes hashes of all Python files in the project
2. It compares these hashes with the previously stored hashes
3. If any files have changed, it increments the version number
4. The new version and file hashes are saved for future comparison

This approach ensures that each time you modify the code and run the application, the version number will automatically increment to reflect the changes.

### Checking the Current Version

You can check the current version by running:

```bash
python cybex_pulse/get_version.py
```

Or by checking the application logs at startup. The version information includes:
- The current version number
- When the version was last updated
- Whether this is a development version

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.