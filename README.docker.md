# Cybex Pulse Docker Setup

This document provides instructions for running Cybex Pulse in a Docker container.

## Prerequisites

- Docker installed on your system
- Docker Compose installed on your system
- Root/sudo access (for building and running the container)

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/DigitalPals/pulse.git
   cd pulse
   ```

2. Build and start the container using Docker Compose:
   ```bash
   docker-compose up -d
   ```

3. Access the web interface at http://localhost:8080

## Configuration

### Timezone

By default, the container uses UTC timezone. To change this, edit the `docker-compose.yml` file and update the `TZ` environment variable:

```yaml
environment:
  - TZ=Europe/Amsterdam  # Replace with your timezone
```

### Persistent Data

The Docker setup uses volumes to persist data:
- `pulse-logs`: Stores application logs at `/var/log/cybex_pulse`
- `pulse-data`: Stores application data at `/var/lib/cybex_pulse`

These volumes ensure your data is preserved even if the container is removed.

## Container Management

### View Logs

```bash
docker logs cybex-pulse
```

### Stop the Container

```bash
docker-compose down
```

### Restart the Container

```bash
docker-compose restart
```

### Rebuild and Update

If you've updated the code or Dockerfile:

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

## Important Notes

1. The container runs in `privileged` mode and with `network_mode: host` because Cybex Pulse requires:
   - Network scanning capabilities
   - Access to the host network interfaces
   - Root privileges for certain operations

2. The web interface is accessible on port 8080 of your host machine.

3. First-time setup will run automatically when you first access the web interface.

## Troubleshooting

If you encounter issues:

1. Check the container logs:
   ```bash
   docker logs cybex-pulse
   ```

2. Ensure the container has proper network access:
   ```bash
   docker exec -it cybex-pulse ip addr
   ```

3. Verify the container has the necessary permissions:
   ```bash
   docker exec -it cybex-pulse nmap -sP 192.168.1.0/24
   ```
   (Replace the IP range with your local network)

4. If the web interface isn't accessible, check if the application is running:
   ```bash
   docker exec -it cybex-pulse ps aux