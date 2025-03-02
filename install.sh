#!/bin/bash

##############################################################
# Cybex Pulse Installation Script
# This script installs Cybex Pulse on various Linux distributions
##############################################################

# Exit on errors
set -e

# Configuration
LOG_FILE="/tmp/cybex-pulse-install.log"
REPO_URL="https://github.com/DigitalPals/pulse.git"
INSTALL_DIR="/usr/local/lib/cybex-pulse"

# Define colors and symbols for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;36m'
NC='\033[0m'    # No Color
BOLD='\033[1m'
CHECK_MARK="\033[0;32m✓\033[0m"
CROSS_MARK="\033[0;31m✗\033[0m"
INFO_MARK="\033[0;34mℹ\033[0m"

# Initialize log file
echo "Cybex Pulse Installation Log - $(date)" > $LOG_FILE
echo "===============================================" >> $LOG_FILE

# Function to output messages
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

# Detect Linux distribution
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
        log_error "Could not detect Linux distribution" "fatal"
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

# Install system dependencies based on distribution
install_dependencies() {
    log_info "Installing system dependencies..."
    
    # Determine package manager and packages based on distribution
    case $DISTRO_FAMILY in
        debian)
            log_info "Updating apt repositories..."
            apt-get update -qq >> $LOG_FILE 2>&1
            
            log_info "Installing Python and dependencies..."
            apt-get install -y python3 python3-pip git curl wget >> $LOG_FILE 2>&1
            
            # Install Python packages via apt
            log_info "Installing Python packages via apt..."
            apt-get install -y python3-flask python3-requests python3-telegram-bot >> $LOG_FILE 2>&1 || true
            
            # Install packages that might not be in the repositories
            log_info "Installing additional Python packages via pip..."
            pip3 install python-nmap speedtest-cli >> $LOG_FILE 2>&1
            
            # Optional packages
            log_info "Installing optional packages..."
            apt-get install -y nmap net-tools iproute2 >> $LOG_FILE 2>&1 || true
            ;;
            
        redhat)
            if [ "$DISTRO" = "fedora" ]; then
                log_info "Installing Python and dependencies..."
                dnf install -y python3 python3-pip python3-devel gcc git curl wget >> $LOG_FILE 2>&1
                
                # Install Python packages via dnf when available
                log_info "Installing Python packages..."
                dnf install -y python3-flask python3-requests >> $LOG_FILE 2>&1 || true
                
                # Install additional packages via pip
                log_info "Installing additional Python packages via pip..."
                pip3 install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
            else
                # For RHEL/CentOS/Rocky
                log_info "Installing EPEL repository..."
                if ! rpm -q epel-release > /dev/null 2>&1; then
                    yum install -y epel-release >> $LOG_FILE 2>&1
                fi
                
                log_info "Installing Python and dependencies..."
                yum install -y python3 python3-pip python3-devel gcc git curl wget >> $LOG_FILE 2>&1
                
                # Install Python packages via yum when available
                log_info "Installing Python packages..."
                yum install -y python3-flask python3-requests >> $LOG_FILE 2>&1 || true
                
                # Install additional packages via pip
                log_info "Installing additional Python packages via pip..."
                pip3 install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
            fi
            
            # Optional packages
            log_info "Installing optional packages..."
            if [ "$DISTRO" = "fedora" ]; then
                dnf install -y nmap net-tools iproute >> $LOG_FILE 2>&1 || true
            else
                yum install -y nmap net-tools iproute >> $LOG_FILE 2>&1 || true
            fi
            ;;
            
        arch)
            log_info "Updating pacman repositories..."
            pacman -Sy --noconfirm >> $LOG_FILE 2>&1
            
            log_info "Installing Python and dependencies..."
            pacman -S --noconfirm python python-pip git curl wget >> $LOG_FILE 2>&1
            
            # Install Python packages via pacman when available
            log_info "Installing Python packages..."
            pacman -S --noconfirm python-flask python-requests >> $LOG_FILE 2>&1 || true
            
            # Install additional packages via pip
            log_info "Installing additional Python packages via pip..."
            pip install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
            
            # Optional packages
            log_info "Installing optional packages..."
            pacman -S --noconfirm nmap net-tools iproute2 >> $LOG_FILE 2>&1 || true
            ;;
            
        suse)
            log_info "Installing Python and dependencies..."
            zypper --non-interactive install python3 python3-pip python3-devel gcc git curl wget >> $LOG_FILE 2>&1
            
            # Install Python packages via zypper when available
            log_info "Installing Python packages..."
            zypper --non-interactive install python3-Flask python3-requests >> $LOG_FILE 2>&1 || true
            
            # Install additional packages via pip
            log_info "Installing additional Python packages via pip..."
            pip3 install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
            
            # Optional packages
            log_info "Installing optional packages..."
            zypper --non-interactive install nmap net-tools iproute2 >> $LOG_FILE 2>&1 || true
            ;;
            
        unknown)
            # Try to detect package manager
            if command -v apt-get > /dev/null; then
                log_info "Using apt package manager..."
                apt-get update -qq >> $LOG_FILE 2>&1
                apt-get install -y -qq python3 python3-pip git curl wget >> $LOG_FILE 2>&1
                apt-get install -y -qq python3-flask python3-requests python3-telegram-bot >> $LOG_FILE 2>&1 || true
                pip3 install python-nmap speedtest-cli >> $LOG_FILE 2>&1
                apt-get install -y -qq nmap net-tools iproute2 >> $LOG_FILE 2>&1 || true
            elif command -v dnf > /dev/null; then
                log_info "Using dnf package manager..."
                dnf install -y python3 python3-pip python3-devel gcc git curl wget >> $LOG_FILE 2>&1
                dnf install -y python3-flask python3-requests >> $LOG_FILE 2>&1 || true
                pip3 install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
                dnf install -y nmap net-tools iproute >> $LOG_FILE 2>&1 || true
            elif command -v yum > /dev/null; then
                log_info "Using yum package manager..."
                yum install -y python3 python3-pip python3-devel gcc git curl wget >> $LOG_FILE 2>&1
                yum install -y python3-flask python3-requests >> $LOG_FILE 2>&1 || true
                pip3 install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
                yum install -y nmap net-tools iproute >> $LOG_FILE 2>&1 || true
            elif command -v pacman > /dev/null; then
                log_info "Using pacman package manager..."
                pacman -Sy --noconfirm >> $LOG_FILE 2>&1
                pacman -S --noconfirm python python-pip git curl wget >> $LOG_FILE 2>&1
                pacman -S --noconfirm python-flask python-requests >> $LOG_FILE 2>&1 || true
                pip install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
                pacman -S --noconfirm nmap net-tools iproute2 >> $LOG_FILE 2>&1 || true
            elif command -v zypper > /dev/null; then
                log_info "Using zypper package manager..."
                zypper --non-interactive install python3 python3-pip python3-devel gcc git curl wget >> $LOG_FILE 2>&1
                zypper --non-interactive install python3-Flask python3-requests >> $LOG_FILE 2>&1 || true
                pip3 install python-telegram-bot python-nmap speedtest-cli >> $LOG_FILE 2>&1
                zypper --non-interactive install nmap net-tools iproute2 >> $LOG_FILE 2>&1 || true
            else
                log_error "No supported package manager found" "fatal"
            fi
            ;;
    esac
    
    # Verify Python is installed correctly
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 installation failed. Please install it manually." "fatal"
    fi
    
    log_success "Dependencies installed successfully"
}

# Clone repository or update if already exists
clone_repository() {
    log_info "Setting up repository..."
    
    # Check if repository already exists
    if [ -d "./pulse" ]; then
        log_info "Repository already exists, updating..."
        cd pulse
        git pull >> $LOG_FILE 2>&1
        cd ..
    else
        # Clone the repository
        log_info "Cloning the repository..."
        git clone $REPO_URL >> $LOG_FILE 2>&1
        if [ $? -ne 0 ]; then
            log_error "Failed to clone repository. Check your internet connection." "fatal"
        fi
    fi
    
    log_success "Repository setup completed"
}

# Install the application to system directories
install_application() {
    log_info "Installing application to system directories..."
    
    # Create installation directory
    mkdir -p $INSTALL_DIR
    
    # Copy files from repository
    log_info "Copying files to installation directory..."
    cp -r pulse/cybex_pulse/* $INSTALL_DIR/
    
    # Create necessary directories
    mkdir -p /etc/cybex-pulse /var/log/cybex-pulse
    
    # Set proper permissions
    chmod -R 755 $INSTALL_DIR
    chmod 775 /var/log/cybex-pulse
    
    log_success "Application installed to system directories"
}

# Create a launcher script
create_launcher() {
    log_info "Creating launcher script..."
    
    # Create a launcher script in /usr/local/bin
    cat > /usr/local/bin/cybex-pulse << EOF
#!/bin/bash
# Launcher script for Cybex Pulse

# Set Python path to include our directory
export PYTHONPATH="$INSTALL_DIR:\$PYTHONPATH"

# Run the application
python3 -m cybex_pulse "\$@"
EOF

    # Make it executable
    chmod +x /usr/local/bin/cybex-pulse
    
    log_success "Launcher script created"
}

# Create a simple systemd service
create_service() {
    log_info "Creating systemd service..."
    
    # Create systemd service file
    cat > /etc/systemd/system/cybex-pulse.service << EOF
[Unit]
Description=Cybex Pulse Network Monitoring
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/cybex-pulse
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload

    log_success "Systemd service created"
}

# Display completion message
print_completion() {
    echo -e "\n${GREEN}${BOLD}Cybex Pulse Installation Completed!${NC}\n"
    
    echo "Installation Details:"
    echo "  - Repository: $(pwd)/pulse"
    echo "  - Installation Directory: $INSTALL_DIR"
    echo "  - Log File: $LOG_FILE"
    echo
    
    echo "Usage Instructions:"
    echo "  - Run the application with: cybex-pulse"
    echo "  - Start as a service: sudo systemctl start cybex-pulse"
    echo "  - Enable at boot: sudo systemctl enable cybex-pulse"
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
    
    # Step 2: Install dependencies
    install_dependencies
    
    # Step 3: Clone repository
    clone_repository
    
    # Step 4: Install application
    install_application
    
    # Step 5: Create launcher script
    create_launcher
    
    # Step 6: Create systemd service
    create_service
    
    # Print completion message
    print_completion
}

# Execute main function
main
exit 0