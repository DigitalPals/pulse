#!/bin/bash

##############################################################
# Cybex Pulse Installation Script
# This script installs Cybex Pulse on various Linux distributions
##############################################################

# Exit on errors
set -e

# Colors and formatting
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'    # No Color
CHECK_MARK="\033[0;32m✓\033[0m"
CROSS_MARK="\033[0;31m✗\033[0m"
INFO_MARK="\033[0;34mℹ\033[0m"

# Configuration
LOG_FILE="/tmp/cybex-pulse-install.log"
REPO_URL="https://github.com/DigitalPals/pulse.git"
REQUIREMENTS_FILE="cybex_pulse/requirements.txt"

# Initialize log file
echo "Cybex Pulse Installation Log - $(date)" > $LOG_FILE
echo "===============================================" >> $LOG_FILE

# Logging functions
log_info() {
    echo -e "${INFO_MARK} ${BLUE}$1${NC}"
    echo "[INFO] $1" >> $LOG_FILE
}

log_success() {
    echo -e "${CHECK_MARK} ${GREEN}$1${NC}"
    echo "[SUCCESS] $1" >> $LOG_FILE
}

log_error() {
    echo -e "${CROSS_MARK} ${RED}$1${NC}"
    echo "[ERROR] $1" >> $LOG_FILE
    if [ "$2" = "fatal" ]; then
        exit 1
    fi
}

log_warning() {
    echo -e "${YELLOW}$1${NC}"
    echo "[WARNING] $1" >> $LOG_FILE
}

# Function to detect Linux distribution
detect_distribution() {
    log_info "Detecting Linux distribution..."
    
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
        log_error "Could not detect Linux distribution." "fatal"
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
            log_warning "Unsupported distribution: $DISTRO. Will attempt to install anyway."
            DISTRO_FAMILY="unknown"
            ;;
    esac
    
    log_success "Detected distribution: $DISTRO ($DISTRO_FAMILY family)"
}

# Install dependencies using native package managers
install_dependencies() {
    log_info "Installing system dependencies..."
    
    # Determine package manager and install base packages
    case $DISTRO_FAMILY in
        debian)
            log_info "Updating apt repositories..."
            apt-get update -qq >> $LOG_FILE 2>&1
            
            log_info "Installing Python, Git, and core dependencies..."
            apt-get install -y python3 python3-pip python3-dev git curl wget nmap net-tools iproute2 sudo snmp arp-scan avahi-utils >> $LOG_FILE 2>&1
            
            # Install Python packages via apt - this will be comprehensive in install_system_packages()
            ;;
            
        redhat)
            if [ "$DISTRO" = "fedora" ]; then
                log_info "Installing Python, Git, and core dependencies..."
                dnf install -y python3 python3-pip python3-devel git curl wget nmap net-tools iproute sudo net-snmp-utils arp-scan avahi >> $LOG_FILE 2>&1
                
                # Install Python packages via dnf - this will be comprehensive in install_system_packages()
            else
                # For RHEL/CentOS/Rocky
                if ! rpm -q epel-release > /dev/null 2>&1; then
                    log_info "Installing EPEL repository..."
                    yum install -y epel-release >> $LOG_FILE 2>&1
                fi
                
                log_info "Installing Python, Git, and core dependencies..."
                yum install -y python3 python3-pip python3-devel git curl wget nmap net-tools iproute sudo net-snmp-utils arp-scan avahi >> $LOG_FILE 2>&1
                
                # Install Python packages via yum - this will be comprehensive in install_system_packages()
            fi
            ;;
            
        arch)
            log_info "Updating pacman repositories..."
            pacman -Sy --noconfirm >> $LOG_FILE 2>&1
            
            log_info "Installing Python, Git, and core dependencies..."
            pacman -S --noconfirm python python-pip git curl wget nmap net-tools iproute2 sudo net-snmp arp-scan avahi >> $LOG_FILE 2>&1
            
            # Install Python packages via pacman - this will be comprehensive in install_system_packages()
            ;;
            
        suse)
            log_info "Installing Python, Git, and core dependencies..."
            zypper --non-interactive install python3 python3-pip python3-devel git curl wget nmap net-tools iproute2 sudo net-snmp arp-scan avahi >> $LOG_FILE 2>&1
            
            # Install Python packages via zypper - this will be comprehensive in install_system_packages()
            ;;
            
        unknown)
            # Try to detect package manager
            if command -v apt-get > /dev/null; then
                log_info "Using apt package manager..."
                apt-get update -qq >> $LOG_FILE 2>&1
                apt-get install -y python3 python3-pip python3-dev git curl wget nmap net-tools iproute2 sudo snmp arp-scan avahi-utils >> $LOG_FILE 2>&1
                # Python packages will be installed in install_system_packages()
            elif command -v dnf > /dev/null; then
                log_info "Using dnf package manager..."
                dnf install -y python3 python3-pip python3-devel git curl wget nmap net-tools iproute sudo net-snmp-utils arp-scan avahi >> $LOG_FILE 2>&1
                # Python packages will be installed in install_system_packages()
            elif command -v yum > /dev/null; then
                log_info "Using yum package manager..."
                yum install -y epel-release >> $LOG_FILE 2>&1 || true
                yum install -y python3 python3-pip python3-devel git curl wget nmap net-tools iproute sudo net-snmp-utils arp-scan avahi >> $LOG_FILE 2>&1
                # Python packages will be installed in install_system_packages()
            elif command -v pacman > /dev/null; then
                log_info "Using pacman package manager..."
                pacman -Sy --noconfirm >> $LOG_FILE 2>&1
                pacman -S --noconfirm python python-pip git curl wget nmap net-tools iproute2 sudo net-snmp arp-scan avahi >> $LOG_FILE 2>&1
                # Python packages will be installed in install_system_packages()
            elif command -v zypper > /dev/null; then
                log_info "Using zypper package manager..."
                zypper --non-interactive install python3 python3-pip python3-devel git curl wget nmap net-tools iproute2 sudo net-snmp arp-scan avahi >> $LOG_FILE 2>&1
                # Python packages will be installed in install_system_packages()
            else
                log_error "No supported package manager found." "fatal"
            fi
            ;;
    esac
    
    # Verify Python is installed correctly
    if ! command -v python3 &> /dev/null; then
        if command -v python &> /dev/null; then
            log_info "Using 'python' instead of 'python3'"
            # Create symlink if needed
            if [ "$DISTRO_FAMILY" = "arch" ]; then
                ln -sf $(which python) /usr/local/bin/python3 2>/dev/null || true
            fi
        else
            log_error "Python 3 installation failed. Please install it manually." "fatal"
        fi
    fi

    log_success "Dependencies installed successfully"
    
    # Try to fix avahi if missing components
    if ! command -v avahi-browse &> /dev/null || ! command -v avahi-resolve &> /dev/null; then
        log_info "Installing additional Avahi components..."
        
        case $DISTRO_FAMILY in
            debian)
                apt-get install -y avahi-daemon avahi-discover avahi-utils libnss-mdns >> $LOG_FILE 2>&1 || true
                systemctl enable avahi-daemon >> $LOG_FILE 2>&1 || true
                systemctl start avahi-daemon >> $LOG_FILE 2>&1 || true
                ;;
            redhat)
                if [ "$DISTRO" = "fedora" ]; then
                    dnf install -y avahi avahi-tools nss-mdns >> $LOG_FILE 2>&1 || true
                else
                    yum install -y avahi avahi-tools nss-mdns >> $LOG_FILE 2>&1 || true
                fi
                systemctl enable avahi-daemon >> $LOG_FILE 2>&1 || true
                systemctl start avahi-daemon >> $LOG_FILE 2>&1 || true
                ;;
            arch)
                pacman -S --noconfirm avahi nss-mdns >> $LOG_FILE 2>&1 || true
                systemctl enable avahi-daemon >> $LOG_FILE 2>&1 || true
                systemctl start avahi-daemon >> $LOG_FILE 2>&1 || true
                ;;
            suse)
                zypper --non-interactive install avahi avahi-utils >> $LOG_FILE 2>&1 || true
                systemctl enable avahi-daemon >> $LOG_FILE 2>&1 || true
                systemctl start avahi-daemon >> $LOG_FILE 2>&1 || true
                ;;
        esac
        
        log_info "Avahi components installed"
    fi
}

# Install packages via system package manager only
install_system_packages() {
    log_info "Installing all required Python packages via system package manager..."
    
    # Determine Python command
    PYTHON_CMD="python3"
    if ! command -v python3 &> /dev/null; then
        PYTHON_CMD="python"
    fi
    
    # Check if we have any missing packages
    MISSING_PACKAGES=false
    
    if ! $PYTHON_CMD -c "import flask" 2>/dev/null || \
       ! $PYTHON_CMD -c "import telegram" 2>/dev/null || \
       ! $PYTHON_CMD -c "import nmap" 2>/dev/null || \
       ! $PYTHON_CMD -c "import speedtest" 2>/dev/null || \
       ! $PYTHON_CMD -c "import requests" 2>/dev/null; then
        MISSING_PACKAGES=true
    fi
    
    # If we have missing packages, install via system package manager
    if [ "$MISSING_PACKAGES" = true ]; then
        log_info "Installing missing Python packages using system package manager..."
        
        case $DISTRO_FAMILY in
            debian)
                log_info "Installing Python packages via apt..."
                apt-get install -y python3-flask python3-telegram-bot python3-nmap python3-speedtest-cli python3-requests >> $LOG_FILE 2>&1
                ;;
                
            redhat)
                if [ "$DISTRO" = "fedora" ]; then
                    log_info "Installing Python packages via dnf..."
                    dnf install -y python3-flask python3-telegram-bot python3-nmap python3-speedtest-cli python3-requests >> $LOG_FILE 2>&1
                else
                    log_info "Installing Python packages via yum..."
                    yum install -y python3-flask python3-telegram-bot python3-nmap python3-speedtest-cli python3-requests >> $LOG_FILE 2>&1
                fi
                ;;
                
            arch)
                log_info "Installing Python packages via pacman..."
                pacman -S --noconfirm python-flask python-telegram-bot python-nmap python-speedtest-cli python-requests >> $LOG_FILE 2>&1
                ;;
                
            suse)
                log_info "Installing Python packages via zypper..."
                zypper --non-interactive install python3-Flask python3-telegram-bot python3-nmap python3-speedtest-cli python3-requests >> $LOG_FILE 2>&1
                ;;
                
            unknown)
                log_warning "Unknown distribution family. Attempting to install packages with available package manager..."
                if command -v apt-get > /dev/null; then
                    apt-get install -y python3-flask python3-telegram-bot python3-nmap python3-speedtest-cli python3-requests >> $LOG_FILE 2>&1
                elif command -v dnf > /dev/null; then
                    dnf install -y python3-flask python3-telegram-bot python3-nmap python3-speedtest-cli python3-requests >> $LOG_FILE 2>&1
                elif command -v yum > /dev/null; then
                    yum install -y python3-flask python3-telegram-bot python3-nmap python3-speedtest-cli python3-requests >> $LOG_FILE 2>&1
                elif command -v pacman > /dev/null; then
                    pacman -S --noconfirm python-flask python-telegram-bot python-nmap python-speedtest-cli python-requests >> $LOG_FILE 2>&1
                elif command -v zypper > /dev/null; then
                    zypper --non-interactive install python3-Flask python3-telegram-bot python3-nmap python3-speedtest-cli python3-requests >> $LOG_FILE 2>&1
                else
                    log_error "No supported package manager found. Cannot install Python packages." "fatal"
                fi
                ;;
        esac
        
        # Verify installation
        if ! $PYTHON_CMD -c "import flask" 2>/dev/null || \
           ! $PYTHON_CMD -c "import telegram" 2>/dev/null || \
           ! $PYTHON_CMD -c "import nmap" 2>/dev/null || \
           ! $PYTHON_CMD -c "import speedtest" 2>/dev/null || \
           ! $PYTHON_CMD -c "import requests" 2>/dev/null; then
            log_error "Failed to install all required Python packages. Please install them manually." "fatal"
        fi
    else
        log_success "All required Python packages are already installed"
    fi
}

# Clone repository or update if already exists
clone_repository() {
    log_info "Setting up repository..."
    
    # Get the current directory
    CURRENT_DIR=$(pwd)
    
    # Check if repository already exists in the current directory
    if [ -d "$CURRENT_DIR/pulse/.git" ]; then
        log_info "Repository already exists, updating..."
        cd "$CURRENT_DIR/pulse"
        git pull >> $LOG_FILE 2>&1 || log_warning "Could not update the repository. Continuing with existing files."
        cd "$CURRENT_DIR"
    else
        # Clone the repository into the current directory
        log_info "Cloning the repository..."
        git clone "$REPO_URL" pulse >> $LOG_FILE 2>&1 || log_error "Failed to clone repository. Check your internet connection." "fatal"
    fi
    
    log_success "Repository setup completed"
}

# Create a wrapper script for running the application
create_wrapper_script() {
    log_info "Creating wrapper script..."
    
    # Get the full path
    INSTALL_DIR=$(pwd)
    
    cd pulse
    
    # Create the wrapper script to handle PYTHONPATH
    cat > pulse << EOF
#!/bin/bash
# Wrapper script for Cybex Pulse

# No local package paths needed - using system packages only

# Add the current directory to the Python path
export PYTHONPATH="$(pwd):\$PYTHONPATH"

# Run the application
exec python3 -m cybex_pulse "\$@"
EOF

    # Make it executable
    chmod +x pulse
    
    log_success "Wrapper script created"
}

# Create a systemd service file
create_service() {
    log_info "Creating systemd service..."
    
    # Get the current directory for the service file
    INSTALL_DIR=$(pwd)
    
    # Create systemd service file
    cat > /tmp/cybex-pulse.service << EOF
[Unit]
Description=Cybex Pulse Network Monitoring
After=network.target

[Service]
Type=simple
ExecStart=${INSTALL_DIR}/pulse
WorkingDirectory=${INSTALL_DIR}
Environment="PYTHONPATH=${INSTALL_DIR}"
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Move to systemd directory
    if [ -d "/etc/systemd/system" ]; then
        mv /tmp/cybex-pulse.service /etc/systemd/system/
        systemctl daemon-reload
        log_success "Systemd service created successfully"
    else
        log_warning "Could not create systemd service: directory not found"
    fi
}

# Display completion message
print_completion() {
    INSTALL_DIR=$(pwd)
    
    echo -e "\n${GREEN}${BOLD}Cybex Pulse Installation Completed!${NC}\n"
    
    echo "Installation Details:"
    echo "  - Repository: $INSTALL_DIR"
    echo "  - Log File: $LOG_FILE"
    echo
    
    echo "Usage Instructions:"
    echo "  - Run the application manually: $INSTALL_DIR/pulse"
    
    if [ -f "/etc/systemd/system/cybex-pulse.service" ]; then
        echo "  - Start as a service: sudo systemctl start cybex-pulse"
        echo "  - Enable at boot: sudo systemctl enable cybex-pulse"
        echo "  - Check service status: sudo systemctl status cybex-pulse"
    fi
    
    echo
    echo "After starting, access the web interface at http://YOUR_IP_ADDRESS:8000"
    echo
    echo "For issues or more information, visit: https://github.com/DigitalPals/pulse"
    echo
}

# Main function
main() {
    echo -e "${BOLD}${BLUE}Cybex Pulse Installation${NC}"
    echo -e "${BLUE}=============================${NC}\n"
    
    # Check if script is running as root
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root. Please use sudo or run as root." "fatal"
    fi
    
    # Step 1: Detect distribution
    detect_distribution
    
    # Step 2: Install system dependencies
    install_dependencies
    
    # Step 3: Install packages via system package manager
    install_system_packages
    
    # Step 4: Clone repository
    clone_repository
    
    # Step 5: Create wrapper script
    create_wrapper_script
    
    # Step 6: Create systemd service
    create_service
    
    # Print completion message
    print_completion
}

# Execute main function
main
exit 0