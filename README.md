# Cybex Pulse

A home network monitoring tool that provides real-time insights into your network devices, internet speed, and security.

## Features

- Network device discovery and monitoring
- Internet speed testing
- Website monitoring
- Basic security scanning
- Telegram alerts
- Web interface for easy management

## Installation

1. Clone this repository
```bash
git clone https://github.com/yourusername/Pulse.git
cd Pulse
```

2. Set up a virtual environment (optional but recommended)
```bash
python -m venv venv
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

## Configuration

On first run, Cybex Pulse will create a default configuration file in `~/.cybex_pulse/config.json`. 
You can modify this file directly or use the web interface to adjust settings.

## Access the Web Interface

By default, the web interface is available at:
- URL: http://YOUR_IP_ADDRESS:8080

## License

This project is licensed under the terms of the license included in the repository.