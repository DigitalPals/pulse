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
            apt-get install -y python3 python3-pip python3-dev git curl wget nmap net-tools iproute2 sudo >> $LOG_FILE 2>&1
            
            # Install Python packages from requirements.txt using apt when possible
            log_info "Installing Python packages via apt..."
            apt-get install -y python3-flask python3-requests >> $LOG_FILE 2>&1 || true
            
            # For packages that might not be in the repositories, use pip
            log_info "Installing additional Python packages via pip..."
            python3 -m pip install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
            ;;
            
        redhat)
            if [ "$DISTRO" = "fedora" ]; then
                log_info "Installing Python, Git, and core dependencies..."
                dnf install -y python3 python3-pip python3-devel git curl wget nmap net-tools iproute sudo >> $LOG_FILE 2>&1
                
                # Install Python packages via dnf when available
                log_info "Installing Python packages..."
                dnf install -y python3-flask python3-requests >> $LOG_FILE 2>&1 || true
            else
                # For RHEL/CentOS/Rocky
                if ! rpm -q epel-release > /dev/null 2>&1; then
                    log_info "Installing EPEL repository..."
                    yum install -y epel-release >> $LOG_FILE 2>&1
                fi
                
                log_info "Installing Python, Git, and core dependencies..."
                yum install -y python3 python3-pip python3-devel git curl wget nmap net-tools iproute sudo >> $LOG_FILE 2>&1
                
                # Install Python packages via yum when available
                log_info "Installing Python packages..."
                yum install -y python3-flask python3-requests >> $LOG_FILE 2>&1 || true
            fi
            
            # Install additional packages via pip
            log_info "Installing additional Python packages via pip..."
            python3 -m pip install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
            ;;
            
        arch)
            log_info "Updating pacman repositories..."
            pacman -Sy --noconfirm >> $LOG_FILE 2>&1
            
            log_info "Installing Python, Git, and core dependencies..."
            pacman -S --noconfirm python python-pip git curl wget nmap net-tools iproute2 sudo >> $LOG_FILE 2>&1
            
            # Install Python packages via pacman when available
            log_info "Installing Python packages..."
            pacman -S --noconfirm python-flask python-requests >> $LOG_FILE 2>&1 || true
            
            # Install additional packages via pip
            log_info "Installing additional Python packages via pip..."
            python -m pip install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
            ;;
            
        suse)
            log_info "Installing Python, Git, and core dependencies..."
            zypper --non-interactive install python3 python3-pip python3-devel git curl wget nmap net-tools iproute2 sudo >> $LOG_FILE 2>&1
            
            # Install Python packages via zypper when available
            log_info "Installing Python packages..."
            zypper --non-interactive install python3-Flask python3-requests >> $LOG_FILE 2>&1 || true
            
            # Install additional packages via pip
            log_info "Installing additional Python packages via pip..."
            python3 -m pip install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
            ;;
            
        unknown)
            # Try to detect package manager
            if command -v apt-get > /dev/null; then
                log_info "Using apt package manager..."
                apt-get update -qq >> $LOG_FILE 2>&1
                apt-get install -y python3 python3-pip python3-dev git curl wget nmap net-tools iproute2 sudo >> $LOG_FILE 2>&1
                apt-get install -y python3-flask python3-requests >> $LOG_FILE 2>&1 || true
                python3 -m pip install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
            elif command -v dnf > /dev/null; then
                log_info "Using dnf package manager..."
                dnf install -y python3 python3-pip python3-devel git curl wget nmap net-tools iproute sudo >> $LOG_FILE 2>&1
                dnf install -y python3-flask python3-requests >> $LOG_FILE 2>&1 || true
                python3 -m pip install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
            elif command -v yum > /dev/null; then
                log_info "Using yum package manager..."
                yum install -y epel-release >> $LOG_FILE 2>&1 || true
                yum install -y python3 python3-pip python3-devel git curl wget nmap net-tools iproute sudo >> $LOG_FILE 2>&1
                yum install -y python3-flask python3-requests >> $LOG_FILE 2>&1 || true
                python3 -m pip install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
            elif command -v pacman > /dev/null; then
                log_info "Using pacman package manager..."
                pacman -Sy --noconfirm >> $LOG_FILE 2>&1
                pacman -S --noconfirm python python-pip git curl wget nmap net-tools iproute2 sudo >> $LOG_FILE 2>&1
                pacman -S --noconfirm python-flask python-requests >> $LOG_FILE 2>&1 || true
                python -m pip install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
            elif command -v zypper > /dev/null; then
                log_info "Using zypper package manager..."
                zypper --non-interactive install python3 python3-pip python3-devel git curl wget nmap net-tools iproute2 sudo >> $LOG_FILE 2>&1
                zypper --non-interactive install python3-Flask python3-requests >> $LOG_FILE 2>&1 || true
                python3 -m pip install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
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

    # Check Python version
    PYTHON_CMD="python3"
    if ! command -v python3 &> /dev/null; then
        PYTHON_CMD="python"
    fi

    # Verify pip is available
    if ! $PYTHON_CMD -m pip --version &> /dev/null; then
        log_error "Pip installation failed. Please install it manually." "fatal"
    fi
    
    log_success "Dependencies installed successfully"
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
    
    # Ensure the requirements file exists
    if [ ! -f "$CURRENT_DIR/pulse/$REQUIREMENTS_FILE" ]; then
        log_error "Requirements file not found in the repository." "fatal"
    fi
}

# Install Python dependencies from requirements.txt
install_python_requirements() {
    log_info "Installing Python dependencies from requirements.txt..."
    
    # Check which Python command to use
    PYTHON_CMD="python3"
    if ! command -v python3 &> /dev/null; then
        PYTHON_CMD="python"
    fi
    
    # Install requirements
    cd pulse
    $PYTHON_CMD -m pip install -r "$REQUIREMENTS_FILE" >> $LOG_FILE 2>&1
    
    # Install the package in development mode
    $PYTHON_CMD -m pip install -e . >> $LOG_FILE 2>&1
    
    log_success "Python requirements installed"
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
    echo "  - Repository: $INSTALL_DIR/pulse"
    echo "  - Log File: $LOG_FILE"
    echo
    
    echo "Usage Instructions:"
    echo "  - Run the application manually: cd $INSTALL_DIR/pulse && ./pulse"
    
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
    
    # Step 3: Clone repository
    clone_repository
    
    # Step 4: Install Python requirements
    install_python_requirements
    
    # Step 5: Create systemd service
    create_service
    
    # Print completion message
    print_completion
}

# Execute main function
main
exit 0