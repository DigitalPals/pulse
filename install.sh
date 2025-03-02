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
VENV_DIR="venv"

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
            apt-get install -y python3 python3-pip python3-venv git curl wget >> $LOG_FILE 2>&1
            
            # Optional packages
            log_info "Installing optional packages..."
            apt-get install -y nmap net-tools iproute2 >> $LOG_FILE 2>&1 || true
            ;;
            
        redhat)
            if [ "$DISTRO" = "fedora" ]; then
                log_info "Installing Python and dependencies..."
                dnf install -y python3 python3-pip python3-devel gcc git curl wget >> $LOG_FILE 2>&1
            else
                # For RHEL/CentOS/Rocky
                log_info "Installing EPEL repository..."
                if ! rpm -q epel-release > /dev/null 2>&1; then
                    yum install -y epel-release >> $LOG_FILE 2>&1
                fi
                
                log_info "Installing Python and dependencies..."
                yum install -y python3 python3-pip python3-devel gcc git curl wget >> $LOG_FILE 2>&1
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
            
            # Optional packages
            log_info "Installing optional packages..."
            pacman -S --noconfirm nmap net-tools iproute2 >> $LOG_FILE 2>&1 || true
            ;;
            
        suse)
            log_info "Installing Python and dependencies..."
            zypper --non-interactive install python3 python3-pip python3-devel gcc git curl wget >> $LOG_FILE 2>&1
            
            # Optional packages
            log_info "Installing optional packages..."
            zypper --non-interactive install nmap net-tools iproute2 >> $LOG_FILE 2>&1 || true
            ;;
            
        unknown)
            # Try to detect package manager
            if command -v apt-get > /dev/null; then
                log_info "Using apt package manager..."
                apt-get update -qq >> $LOG_FILE 2>&1
                apt-get install -y -qq python3 python3-pip python3-venv git curl wget >> $LOG_FILE 2>&1
                apt-get install -y -qq nmap net-tools iproute2 >> $LOG_FILE 2>&1 || true
            elif command -v dnf > /dev/null; then
                log_info "Using dnf package manager..."
                dnf install -y python3 python3-pip python3-devel gcc git curl wget >> $LOG_FILE 2>&1
                dnf install -y nmap net-tools iproute >> $LOG_FILE 2>&1 || true
            elif command -v yum > /dev/null; then
                log_info "Using yum package manager..."
                yum install -y python3 python3-pip python3-devel gcc git curl wget >> $LOG_FILE 2>&1
                yum install -y nmap net-tools iproute >> $LOG_FILE 2>&1 || true
            elif command -v pacman > /dev/null; then
                log_info "Using pacman package manager..."
                pacman -Sy --noconfirm >> $LOG_FILE 2>&1
                pacman -S --noconfirm python python-pip git curl wget >> $LOG_FILE 2>&1
                pacman -S --noconfirm nmap net-tools iproute2 >> $LOG_FILE 2>&1 || true
            elif command -v zypper > /dev/null; then
                log_info "Using zypper package manager..."
                zypper --non-interactive install python3 python3-pip python3-devel gcc git curl wget >> $LOG_FILE 2>&1
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
    
    # Verify pip is installed correctly
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 installation failed. Please install it manually." "fatal"
    fi
    
    # Make sure virtualenv functionality works
    if ! python3 -m venv --help &> /dev/null; then
        log_warning "Python venv module is not available, attempting to install..."
        case $DISTRO_FAMILY in
            debian)
                apt-get install -y python3-venv >> $LOG_FILE 2>&1
                ;;
            redhat)
                if [ "$DISTRO" = "fedora" ]; then
                    dnf install -y python3-venv >> $LOG_FILE 2>&1
                else
                    yum install -y python3-venv >> $LOG_FILE 2>&1
                fi
                ;;
            # Arch Linux has venv included with Python
            suse)
                zypper --non-interactive install python3-venv >> $LOG_FILE 2>&1
                ;;
        esac
        
        if ! python3 -m venv --help &> /dev/null; then
            log_error "Python venv module installation failed. Please install it manually." "fatal"
        fi
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

# Set up Python virtual environment
setup_python_environment() {
    log_info "Setting up Python virtual environment..."
    
    cd pulse
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        log_info "Creating new virtual environment..."
        python3 -m venv $VENV_DIR >> $LOG_FILE 2>&1
        if [ $? -ne 0 ]; then
            log_error "Failed to create virtual environment. Check your Python installation." "fatal"
        fi
    else
        log_info "Using existing virtual environment..."
    fi
    
    # Activate virtual environment
    source $VENV_DIR/bin/activate
    
    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip >> $LOG_FILE 2>&1
    
    # Install dependencies
    if [ -f "cybex_pulse/requirements.txt" ]; then
        log_info "Installing requirements from requirements.txt..."
        pip install -r cybex_pulse/requirements.txt >> $LOG_FILE 2>&1
    else
        log_warning "requirements.txt not found, installing base dependencies..."
        # Install some basic packages
        pip install flask requests python-nmap >> $LOG_FILE 2>&1
    fi
    
    # Install the package in development mode
    log_info "Installing package in development mode..."
    cd cybex_pulse
    pip install -e . >> $LOG_FILE 2>&1
    
    # Handle common import issues
    if [ $? -ne 0 ]; then
        log_warning "Installation had issues. Attempting to fix..."
        
        # Create __init__.py files in all directories
        find . -type d -not -path "*/\.*" -not -path "*/$VENV_DIR*" -exec touch {}/__init__.py \; >> $LOG_FILE 2>&1
        
        # Retry installation
        pip install -e . >> $LOG_FILE 2>&1
        if [ $? -ne 0 ]; then
            log_error "Failed to install the package. Check the logs for details."
        fi
    fi
    
    # Return to base directory
    cd ../..
    
    log_success "Python environment setup completed"
}

# Verify installation is working
verify_installation() {
    log_info "Verifying installation..."
    
    cd pulse
    source $VENV_DIR/bin/activate
    
    # Try to import the module
    echo "import sys; sys.path.insert(0, '.'); import cybex_pulse; print('Module imported successfully')" > test_import.py
    python test_import.py >> $LOG_FILE 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Module imported successfully"
    else
        log_warning "Module import failed. Application may not work correctly."
        
        # Set up environment variables as a workaround
        echo "export PYTHONPATH=$(pwd):$(pwd)/cybex_pulse:\$PYTHONPATH" >> $VENV_DIR/bin/activate
        log_info "Added PYTHONPATH to virtual environment activation script"
    fi
    
    cd ..
    
    log_success "Installation verified"
}

# Create a launcher script
create_launcher() {
    log_info "Creating launcher script..."
    
    # Create a launcher script that activates the virtual environment
    cat > pulse/pulse << EOF
#!/bin/bash
# Launcher script for Cybex Pulse

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="\$SCRIPT_DIR/$VENV_DIR"

# Activate the virtual environment
source "\$VENV_DIR/bin/activate"

# Set Python path to include our directory
export PYTHONPATH="\$SCRIPT_DIR:\$SCRIPT_DIR/cybex_pulse:\$PYTHONPATH"

# Run the application
python -m cybex_pulse "\$@"
EOF

    # Make it executable
    chmod +x pulse/pulse
    
    # Create a symlink in /usr/local/bin for system-wide access
    if [ -L "/usr/local/bin/cybex-pulse" ]; then
        rm /usr/local/bin/cybex-pulse
    fi
    
    ln -s "$(pwd)/pulse/pulse" /usr/local/bin/cybex-pulse
    
    log_success "Launcher script created"
}

# Display completion message
print_completion() {
    echo -e "\n${GREEN}${BOLD}Cybex Pulse Installation Completed!${NC}\n"
    
    echo "Installation Details:"
    echo "  - Repository Location: $(pwd)/pulse"
    echo "  - Log File: $LOG_FILE"
    echo
    
    echo "Usage Instructions:"
    echo "  - Run the application with: cybex-pulse"
    echo "  - Or from the project directory with: ./pulse/pulse"
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
    
    # Step 4: Set up Python environment
    setup_python_environment
    
    # Step 5: Verify installation
    verify_installation
    
    # Step 6: Create launcher script
    create_launcher
    
    # Print completion message
    print_completion
}

# Execute main function
main
exit 0