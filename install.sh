#!/bin/bash

#######################################################
# Cybex Pulse Installation Script
# This script installs Cybex Pulse on various Linux distributions
#######################################################

set -e

# Enable better error handling
trap 'handle_error $? $LINENO' ERR

handle_error() {
    local exit_code=$1
    local line_number=$2
    echo -e "\n\033[0;31m✗ Error occurred at line $line_number (exit code $exit_code)\033[0m"
    echo -e "\033[0;31mInstallation failed. Check error details above.\033[0m"
    exit $exit_code
}

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'
CYAN='\033[0;36m'

# Configuration
INSTALL_DIR="/opt/cybex-pulse"
SERVICE_USER="cybexpulse"
CONFIG_DIR="/etc/cybex-pulse"
LOG_DIR="/var/log/cybex-pulse"
SERVICE_NAME="cybex-pulse"

# Functions
print_header() {
    clear
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                            ║${NC}"
    echo -e "${BLUE}║      ${BOLD}Cybex Pulse - Network Monitoring Installation${NC}${BLUE}        ║${NC}"
    echo -e "${BLUE}║                                                            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo
}

show_spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

progress() {
    echo -ne "${YELLOW}⏳ $1...${NC}"
}

success() {
    echo -e "\r${GREEN}✓ $1${NC}"
}

error() {
    echo -e "\r${RED}✗ $1${NC}"
    echo
    echo -e "${RED}Installation failed. Please check the error above.${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

step() {
    echo -e "\n${CYAN}${BOLD}[$1/${TOTAL_STEPS}] $2${NC}"
}

check_distribution() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        DISTRO=$(lsb_release -si)
        VERSION=$(lsb_release -sr)
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        DISTRO=$DISTRIB_ID
        VERSION=$DISTRIB_RELEASE
    else
        error "Could not detect Linux distribution"
    fi

    DISTRO=$(echo $DISTRO | tr '[:upper:]' '[:lower:]')
    
    # Normalize distribution names
    case $DISTRO in
        ubuntu|debian|pop|mint|elementary|zorin|kali)
            DISTRO_FAMILY="debian"
            ;;
        fedora|rhel|centos|rocky|alma|redhat|amzn)
            DISTRO_FAMILY="redhat"
            ;;
        arch|manjaro|endeavouros|garuda)
            DISTRO_FAMILY="arch"
            ;;
        opensuse|suse|sles)
            DISTRO_FAMILY="suse"
            ;;
        *)
            warning "Unsupported distribution: $DISTRO. Will attempt to install anyway."
            DISTRO_FAMILY="unknown"
            ;;
    esac
}

install_dependencies() {
    progress "Installing system dependencies"
    
    # Create a log file for installation details
    LOG_FILE="/tmp/cybex-pulse-install.log"
    echo "Cybex Pulse Installation Log - $(date)" > $LOG_FILE
    
    case $DISTRO_FAMILY in
        debian)
            # Capture detailed output to log file
            {
                echo "Running apt-get update..." >> $LOG_FILE
                apt-get update -qq
                
                echo "Installing dependencies..." >> $LOG_FILE
                apt-get install -y -qq python3 python3-pip python3-venv nmap net-tools arp-scan iproute2 \
                                  avahi-utils snmp net-snmp-tools curl
            } >> $LOG_FILE 2>&1 || {
                echo "Failed to install dependencies. Check $LOG_FILE for details."
                error "Failed to install dependencies (see $LOG_FILE for details)"
            }
            ;;
        redhat)
            {
                echo "Installing dependencies for RedHat-based system..." >> $LOG_FILE
                if [ "$DISTRO" = "fedora" ]; then
                    dnf install -y python3 python3-pip nmap net-tools arp-scan iproute net-snmp-utils avahi-tools curl
                else
                    # RHEL/CentOS may need EPEL repository
                    if ! rpm -q epel-release > /dev/null 2>&1; then
                        echo "Installing EPEL repository..." >> $LOG_FILE
                        yum install -y epel-release
                    fi
                    yum install -y python3 python3-pip nmap net-tools arp-scan iproute net-snmp-utils avahi-tools curl
                fi
            } >> $LOG_FILE 2>&1 || {
                echo "Failed to install dependencies. Check $LOG_FILE for details."
                error "Failed to install dependencies (see $LOG_FILE for details)"
            }
            ;;
        arch)
            {
                echo "Installing dependencies for Arch-based system..." >> $LOG_FILE
                pacman -Sy --noconfirm python python-pip nmap net-tools arp-scan iproute2 avahi net-snmp curl
            } >> $LOG_FILE 2>&1 || {
                echo "Failed to install dependencies. Check $LOG_FILE for details."
                error "Failed to install dependencies (see $LOG_FILE for details)"
            }
            ;;
        suse)
            {
                echo "Installing dependencies for SUSE-based system..." >> $LOG_FILE
                zypper --non-interactive install python3 python3-pip nmap net-tools arp-scan iproute2 avahi net-snmp curl
            } >> $LOG_FILE 2>&1 || {
                echo "Failed to install dependencies. Check $LOG_FILE for details."
                error "Failed to install dependencies (see $LOG_FILE for details)"
            }
            ;;
        unknown)
            warning "Attempting to install dependencies using available package manager..."
            echo "Attempting to detect package manager for unknown distribution..." >> $LOG_FILE
            # Try different package managers
            if command -v apt-get > /dev/null; then
                echo "Using apt-get package manager..." >> $LOG_FILE
                apt-get update -qq
                apt-get install -y -qq python3 python3-pip python3-venv nmap net-tools arp-scan iproute2 \
                                  avahi-utils snmp curl
            elif command -v yum > /dev/null; then
                echo "Using yum package manager..." >> $LOG_FILE
                yum install -y python3 python3-pip nmap net-tools arp-scan iproute avahi-tools net-snmp-utils curl
            elif command -v dnf > /dev/null; then
                echo "Using dnf package manager..." >> $LOG_FILE
                dnf install -y python3 python3-pip nmap net-tools arp-scan iproute avahi-tools net-snmp-utils curl
            elif command -v pacman > /dev/null; then
                echo "Using pacman package manager..." >> $LOG_FILE
                pacman -Sy --noconfirm python python-pip nmap net-tools arp-scan iproute2 avahi net-snmp curl
            elif command -v zypper > /dev/null; then
                echo "Using zypper package manager..." >> $LOG_FILE
                zypper --non-interactive install python3 python3-pip nmap net-tools arp-scan iproute2 avahi net-snmp curl
            else
                error "No supported package manager found"
            fi >> $LOG_FILE 2>&1 || {
                echo "Failed to install dependencies. Check $LOG_FILE for details."
                error "Failed to install dependencies (see $LOG_FILE for details)"
            }
            ;;
    esac
    
    success "System dependencies installed"
}

create_user() {
    progress "Creating service user"
    
    # Check if user already exists
    if id "$SERVICE_USER" &>/dev/null; then
        success "Service user already exists"
        return
    fi
    
    # Create user without login shell and home directory
    {
        useradd -r -s /bin/false $SERVICE_USER
    } > /dev/null 2>&1 || error "Failed to create service user"
    
    success "Service user created"
}

setup_directories() {
    progress "Setting up application directories"
    
    # Create installation directory
    mkdir -p $INSTALL_DIR $CONFIG_DIR $LOG_DIR
    
    # Set proper permissions
    chown -R $SERVICE_USER:$SERVICE_USER $CONFIG_DIR $LOG_DIR
    chmod 755 $INSTALL_DIR $CONFIG_DIR
    chmod 775 $LOG_DIR
    
    success "Directories created"
}

install_python_packages() {
    progress "Creating Python virtual environment"
    
    # Create and activate Python virtual environment
    {
        echo "Creating Python virtual environment..." >> $LOG_FILE
        python3 -m venv $INSTALL_DIR/venv
        # Use the full path to pip to ensure we're using the venv
        echo "Upgrading pip..." >> $LOG_FILE
        $INSTALL_DIR/venv/bin/pip install --upgrade pip
    } >> $LOG_FILE 2>&1 || {
        echo "Failed to create virtual environment. Check $LOG_FILE for details."
        error "Failed to create virtual environment (see $LOG_FILE for details)"
    }
    
    success "Python virtual environment created"
    
    progress "Installing Python dependencies"
    
    # Install required Python packages
    {
        echo "Installing Python packages..." >> $LOG_FILE
        $INSTALL_DIR/venv/bin/pip install flask python-telegram-bot speedtest-cli python-nmap requests
        
        # Check if requirements.txt exists (when we have the repository)
        if [ -f "$INSTALL_DIR/requirements.txt" ]; then
            echo "Installing requirements from requirements.txt..." >> $LOG_FILE
            $INSTALL_DIR/venv/bin/pip install -r $INSTALL_DIR/requirements.txt
        fi
    } >> $LOG_FILE 2>&1 || {
        echo "Failed to install Python dependencies. Check $LOG_FILE for details."
        error "Failed to install Python dependencies (see $LOG_FILE for details)"
    }
    
    success "Python dependencies installed"
}

copy_application() {
    progress "Copying application files"
    
    # Get current directory
    CURRENT_DIR="$(pwd)"
    
    # Check if we're running from the repository or via curl pipe
    if [ -d "$CURRENT_DIR/cybex_pulse" ]; then
        # We have the repository locally
        {
            cp -r $CURRENT_DIR/cybex_pulse/* $INSTALL_DIR/
            # Copy pulse executable script to bin
            mkdir -p /usr/local/bin
            cp $CURRENT_DIR/pulse /usr/local/bin/cybex-pulse
            chmod +x /usr/local/bin/cybex-pulse
        } 2>&1 || error "Failed to copy application files"
    else
        # We need to download the repository
        progress "Downloading repository from GitHub"
        TEMP_DIR=$(mktemp -d)
        {
            # Install git if not already installed
            case $DISTRO_FAMILY in
                debian)
                    apt-get install -y -qq git > /dev/null 2>&1
                    ;;
                redhat)
                    if [ "$DISTRO" = "fedora" ]; then
                        dnf install -y git > /dev/null 2>&1
                    else
                        yum install -y git > /dev/null 2>&1
                    fi
                    ;;
                arch)
                    pacman -Sy --noconfirm git > /dev/null 2>&1
                    ;;
                suse)
                    zypper --non-interactive install git > /dev/null 2>&1
                    ;;
                unknown)
                    if command -v apt-get > /dev/null; then
                        apt-get install -y -qq git > /dev/null 2>&1
                    elif command -v yum > /dev/null; then
                        yum install -y git > /dev/null 2>&1
                    elif command -v dnf > /dev/null; then
                        dnf install -y git > /dev/null 2>&1
                    elif command -v pacman > /dev/null; then
                        pacman -Sy --noconfirm git > /dev/null 2>&1
                    elif command -v zypper > /dev/null; then
                        zypper --non-interactive install git > /dev/null 2>&1
                    fi
                    ;;
            esac
            
            # Clone repository
            git clone https://github.com/DigitalPals/pulse.git $TEMP_DIR
            
            # Copy files
            cp -r $TEMP_DIR/cybex_pulse/* $INSTALL_DIR/
            # Copy pulse executable
            mkdir -p /usr/local/bin
            cp $TEMP_DIR/pulse /usr/local/bin/cybex-pulse
            chmod +x /usr/local/bin/cybex-pulse
            
            # Clean up
            rm -rf $TEMP_DIR
        } 2>&1 || error "Failed to download and copy application files"
        success "Repository downloaded and installed"
    fi
    
    # Create symlink to the venv-python executable
    ln -sf $INSTALL_DIR/venv/bin/python /usr/local/bin/cybex-pulse-python
    
    success "Application files copied"
}

install_systemd_service() {
    progress "Installing systemd service"
    
    # Create systemd service file
    cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Cybex Pulse Network Monitoring
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python -m cybex_pulse
Restart=on-failure
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=cybex-pulse
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd manager configuration
    {
        systemctl daemon-reload
    } > /dev/null 2>&1 || error "Failed to reload systemd configuration"
    
    success "Systemd service installed"
}

configure_app() {
    progress "Configuring application"
    
    # Create default configuration
    mkdir -p $CONFIG_DIR
    
    # Create empty configuration if it doesn't exist
    if [ ! -f $CONFIG_DIR/config.json ]; then
        cat > $CONFIG_DIR/config.json << EOF
{
  "general": {
    "scan_interval": 300
  },
  "network": {
    "subnet": "192.168.1.0/24"
  },
  "web_interface": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8000
  },
  "alerts": {
    "enabled": false,
    "new_device": true,
    "device_offline": false,
    "important_device_offline": true,
    "latency_threshold": 100,
    "website_error": true
  },
  "monitoring": {
    "internet_health": {
      "enabled": true,
      "interval": 3600
    },
    "websites": {
      "enabled": false,
      "interval": 300,
      "urls": []
    },
    "security": {
      "enabled": false,
      "interval": 86400
    }
  },
  "fingerprinting": {
    "enabled": true,
    "confidence_threshold": 0.5,
    "max_threads": 10,
    "timeout": 2
  }
}
EOF
    fi
    
    # Set proper permissions
    chown $SERVICE_USER:$SERVICE_USER $CONFIG_DIR/config.json
    chmod 640 $CONFIG_DIR/config.json
    
    # Create symlink to config directory
    mkdir -p /home/$SERVICE_USER/.cybex_pulse
    ln -sf $CONFIG_DIR/config.json /home/$SERVICE_USER/.cybex_pulse/config.json
    
    success "Application configured"
}

start_service() {
    progress "Starting Cybex Pulse service"
    
    {
        systemctl enable $SERVICE_NAME.service
        systemctl start $SERVICE_NAME.service
    } > /dev/null 2>&1 || error "Failed to start service"
    
    success "Service started"
}

print_completion() {
    echo -e "\n${GREEN}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║                                                            ║${NC}"
    echo -e "${GREEN}${BOLD}║      Cybex Pulse installation completed successfully!       ║${NC}"
    echo -e "${GREEN}${BOLD}║                                                            ║${NC}"
    echo -e "${GREEN}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${BOLD}Access Information:${NC}"
    echo -e "  Web Interface: http://$(hostname -I | awk '{print $1}'):8000"
    echo
    echo -e "${BOLD}Service Management:${NC}"
    echo -e "  Start service:   ${CYAN}sudo systemctl start $SERVICE_NAME${NC}"
    echo -e "  Stop service:    ${CYAN}sudo systemctl stop $SERVICE_NAME${NC}"
    echo -e "  Restart service: ${CYAN}sudo systemctl restart $SERVICE_NAME${NC}"
    echo -e "  Check status:    ${CYAN}sudo systemctl status $SERVICE_NAME${NC}"
    echo -e "  View logs:       ${CYAN}sudo journalctl -u $SERVICE_NAME${NC}"
    echo
    echo -e "${BOLD}Configuration:${NC}"
    echo -e "  Config file:     ${CYAN}$CONFIG_DIR/config.json${NC}"
    echo -e "  Log directory:   ${CYAN}$LOG_DIR${NC}"
    echo -e "  Install log:     ${CYAN}$LOG_FILE${NC}"
    echo
    echo -e "${YELLOW}NOTE: If this is your first time running Cybex Pulse,${NC}"
    echo -e "${YELLOW}you'll need to complete the setup wizard in the web interface.${NC}"
    echo
    echo -e "${BOLD}If you encounter any issues:${NC}"
    echo -e "  - Check the installation log: ${CYAN}$LOG_FILE${NC}"
    echo -e "  - Check the service status: ${CYAN}sudo systemctl status $SERVICE_NAME${NC}"
    echo -e "  - View service logs: ${CYAN}sudo journalctl -u $SERVICE_NAME${NC}"
    echo
}

# Main installation process
print_header

# Check if script is running as root
if [ "$EUID" -ne 0 ]; then
    error "This script must be run as root"
fi

# Detect Linux distribution
check_distribution
echo -e "${BOLD}Detected distribution:${NC} $DISTRO ($DISTRO_FAMILY family)"
echo

# Define total steps
TOTAL_STEPS=8

# Begin installation
step 1 "Installing system dependencies"
install_dependencies

step 2 "Creating service user"
create_user

step 3 "Setting up directories"
setup_directories

step 4 "Installing Python packages"
install_python_packages

step 5 "Copying application files"
copy_application

step 6 "Installing systemd service"
install_systemd_service

step 7 "Configuring application"
configure_app

step 8 "Starting service"
start_service

# Installation complete
print_completion

exit 0