#!/bin/bash

# Cybex Pulse Docker run script
# This script ensures proper sequence of commands for Docker Compose

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Cybex Pulse Docker Setup${NC}"
echo -e "=========================="
echo

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check which Docker Compose command is available
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
    echo -e "${GREEN}Using docker-compose command${NC}"
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
    echo -e "${GREEN}Using docker compose command${NC}"
else
    echo -e "${RED}Error: Neither docker-compose nor docker compose is available.${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Stop any running containers
echo -e "${GREEN}Stopping any running containers...${NC}"
$COMPOSE_CMD down

# Build the image
echo -e "${GREEN}Building the Docker image...${NC}"
$COMPOSE_CMD build

# Start the containers
echo -e "${GREEN}Starting the containers...${NC}"
$COMPOSE_CMD up -d

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Success! Cybex Pulse is now running in Docker.${NC}"
    echo "Access the web interface at http://localhost:8080"
else
    echo -e "${RED}Failed to start Cybex Pulse with Docker Compose.${NC}"
    exit 1
fi

echo
echo -e "${YELLOW}Note:${NC} The container runs with privileged access to enable network scanning."
echo -e "${YELLOW}Note:${NC} For more information, see README.docker.md"