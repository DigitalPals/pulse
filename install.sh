#!/bin/bash

##############################################################
# Cybex Pulse Installation Script
# This script installs Cybex Pulse on various Linux distributions
##############################################################

# Safer bash settings
set -o pipefail
set -o nounset

# Define a trap for error handling
error_handler() {
    local line=$1
    local command=$2
    local code=${3:-1}
    log_error "Error occurred at line $line, command: '$command' exited with status: $code"
    echo -e "\n${RED}${BOLD}Installation failed!${NC}"
    echo -e "Please check the log file at ${LOG_FILE} for details."
    echo -e "You can report issues at: https://github.com/DigitalPals/pulse/issues"
    exit 1
}

# Set up trap to catch errors
trap 'error_handler ${LINENO} "$BASH_COMMAND" $?' ERR

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
VERBOSE="false"
PYTHON_CMD=""
INSTALL_DIR=""
SUDO_CMD=""

# Check if we need sudo for certain operations
if command -v sudo >/dev/null 2>&1; then
    SUDO_CMD="sudo"
fi

# Initialize log file
echo "Cybex Pulse Installation Log - $(date)" > $LOG_FILE
echo "System: $(uname -a)" >> $LOG_FILE
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
    echo -e "${CROSS_MARK} ${RED}${BOLD}ERROR:${NC} ${RED}$1${NC}"
    echo "[ERROR] $1" >> $LOG_FILE
    
    if [ "$2" = "fatal" ]; then
        echo -e "\n${RED}${BOLD}Installation failed!${NC}"
        echo -e "Please check the log file at ${LOG_FILE} for details."
        echo -e "You can report issues at: https://github.com/DigitalPals/pulse/issues"
        exit 1
    fi
    
    # Show the last few lines of the log if verbose
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${YELLOW}Last 5 log entries:${NC}"
        tail -n 5 "$LOG_FILE" | sed 's/^/  /'
    fi
}

log_warning() {
    echo -e "${YELLOW}$1${NC}"
    echo "[WARNING] $1" >> $LOG_FILE
}

# Function to detect Linux distribution
detect_distribution() {
    log_info "Detecting Linux distribution..."
    
    # Record detailed system information in the log
    if command -v lscpu >/dev/null 2>&1; then
        lscpu >> $LOG_FILE 2>&1
    fi
    
    if command -v free >/dev/null 2>&1; then
        free -h >> $LOG_FILE 2>&1
    fi
    
    # Try multiple methods to detect the distribution
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=${ID:-"unknown"}
        VERSION=${VERSION_ID:-"unknown"}
        echo "OS Release: $NAME $VERSION_ID" >> $LOG_FILE
    elif type lsb_release >/dev/null 2>&1; then
        DISTRO=$(lsb_release -si)
        VERSION=$(lsb_release -sr)
        echo "LSB Release: $DISTRO $VERSION" >> $LOG_FILE
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        DISTRO=${DISTRIB_ID:-"unknown"}
        VERSION=${DISTRIB_RELEASE:-"unknown"}
        echo "LSB Release File: $DISTRO $VERSION" >> $LOG_FILE
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
        VERSION=$(cat /etc/debian_version)
        echo "Debian Version: $VERSION" >> $LOG_FILE
    elif [ -f /etc/redhat-release ]; then
        DISTRO="redhat"
        VERSION=$(cat /etc/redhat-release)
        echo "RedHat Release: $VERSION" >> $LOG_FILE
    else
        log_error "Could not detect Linux distribution. Proceeding with caution." 
        DISTRO="unknown"
        VERSION="unknown"
    fi

    # Convert to lowercase
    DISTRO=$(echo ${DISTRO} | tr '[:upper:]' '[:lower:]')
    
    # Normalize distribution names
    case $DISTRO in
        ubuntu|debian|pop|mint|elementary|zorin|kali|raspbian|parrot|mx|linuxmint|deepin)
            DISTRO_FAMILY="debian"
            ;;
        fedora|rhel|centos|rocky|alma|redhat|amzn|oracle|scientific|ol)
            DISTRO_FAMILY="redhat"
            ;;
        arch|manjaro|endeavouros|garuda|archcraft|arcolinux|artix)
            DISTRO_FAMILY="arch"
            ;;
        opensuse|suse|sles|opensuse-leap|opensuse-tumbleweed)
            DISTRO_FAMILY="suse"
            ;;
        alpine)
            DISTRO_FAMILY="alpine"
            ;;
        gentoo|calculate|funtoo)
            DISTRO_FAMILY="gentoo"
            ;;
        void)
            DISTRO_FAMILY="void"
            ;;
        *)
            log_warning "Unsupported distribution: $DISTRO. Will attempt to install anyway."
            DISTRO_FAMILY="unknown"
            ;;
    esac
    
    # Record to log
    echo "Distribution Family: $DISTRO_FAMILY" >> $LOG_FILE
    
    log_success "Detected distribution: $DISTRO ($DISTRO_FAMILY family) version $VERSION"
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

# Set installation directories
set_install_directories() {
    log_info "Setting installation directories..."
    
    # Default to /opt/pulse as the installation directory
    if [ -z "$INSTALL_DIR" ]; then
        INSTALL_DIR="/opt/pulse"
    fi
    
    # Create the installation directory if it doesn't exist
    if [ ! -d "$INSTALL_DIR" ]; then
        log_info "Creating installation directory: $INSTALL_DIR"
        $SUDO_CMD mkdir -p "$INSTALL_DIR" >> $LOG_FILE 2>&1 || log_error "Failed to create installation directory" "fatal"
        $SUDO_CMD chmod 755 "$INSTALL_DIR" >> $LOG_FILE 2>&1
    fi
    
    log_success "Install directory set to: $INSTALL_DIR"
}

# Install packages via system package manager only
install_system_packages() {
    log_info "Installing all required Python packages via system package manager..."
    
    # Find the best Python command
    find_python_command() {
        log_info "Detecting Python installation..."
        
        # Check for Python 3.7+ first (as the minimum required version)
        for cmd in python3.11 python3.10 python3.9 python3.8 python3.7 python3 python; do
            if command -v $cmd &> /dev/null; then
                # Check version
                ver=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
                if [ $? -eq 0 ]; then
                    major=$(echo $ver | cut -d. -f1)
                    minor=$(echo $ver | cut -d. -f2)
                    
                    if [ "$major" -eq 3 ] && [ "$minor" -ge 7 ]; then
                        PYTHON_CMD=$cmd
                        log_success "Found suitable Python: $PYTHON_CMD (version $ver)"
                        echo "Python version: $($PYTHON_CMD --version)" >> $LOG_FILE 2>&1
                        return 0
                    else
                        log_warning "Found Python $cmd but version $ver is too old (need 3.7+)"
                    fi
                fi
            fi
        done
        
        log_error "No suitable Python installation found. Need Python 3.7 or newer."
        return 1
    }
    
    # Find the best Python command
    find_python_command || {
        log_warning "Attempting to install Python 3..."
        case $DISTRO_FAMILY in
            debian)
                $SUDO_CMD apt-get update -qq && $SUDO_CMD apt-get install -y python3 python3-pip >> $LOG_FILE 2>&1
                ;;
            redhat)
                if [ "$DISTRO" = "fedora" ]; then
                    $SUDO_CMD dnf install -y python3 python3-pip >> $LOG_FILE 2>&1
                else
                    $SUDO_CMD yum install -y python3 python3-pip >> $LOG_FILE 2>&1
                fi
                ;;
            arch)
                $SUDO_CMD pacman -Sy --noconfirm python python-pip >> $LOG_FILE 2>&1
                ;;
            suse)
                $SUDO_CMD zypper --non-interactive install python3 python3-pip >> $LOG_FILE 2>&1
                ;;
            *)
                log_error "Cannot install Python automatically on this system. Please install Python 3.7+ manually." "fatal"
                ;;
        esac
        find_python_command || log_error "Failed to install Python. Please install Python 3.7+ manually." "fatal"
    }
    
    # Check if we have any missing packages
    MISSING_PACKAGES=false
    
    if ! $PYTHON_CMD -c "import flask" 2>/dev/null || \
       ! $PYTHON_CMD -c "import telegram" 2>/dev/null || \
       ! $PYTHON_CMD -c "import nmap" 2>/dev/null || \
       ! $PYTHON_CMD -c "import speedtest" 2>/dev/null || \
       ! $PYTHON_CMD -c "import requests" 2>/dev/null || \
       ! $PYTHON_CMD -c "import psutil" 2>/dev/null; then
        MISSING_PACKAGES=true
    fi
    
    # If we have missing packages, install via system package manager
    if [ "$MISSING_PACKAGES" = true ]; then
        log_info "Installing missing Python packages using system package manager..."
        
        case $DISTRO_FAMILY in
            debian)
                log_info "Installing Python packages via apt..."
                # Try correct package names first, handling each package separately
                INSTALL_ERRORS=0
                
                # Function to install a Debian/Ubuntu package with fallbacks
                install_pkg() {
                    local primary_pkg="$1"
                    local fallback_pkg="$2"
                    local python_module="$3"
                    
                    # Check if module already installed in Python
                    if $PYTHON_CMD -c "import $python_module" 2>/dev/null; then
                        log_success "Module $python_module already available"
                        return 0
                    fi
                    
                    # Try primary package
                    log_info "Installing $primary_pkg..."
                    if $SUDO_CMD apt-get install -y $primary_pkg >> $LOG_FILE 2>&1; then
                        log_success "Installed $primary_pkg successfully"
                        return 0
                    fi
                    
                    # Try fallback package
                    log_warning "Could not install $primary_pkg, trying $fallback_pkg..."
                    if $SUDO_CMD apt-get install -y $fallback_pkg >> $LOG_FILE 2>&1; then
                        log_success "Installed $fallback_pkg successfully"
                        return 0
                    fi
                    
                    log_warning "Failed to install package for $python_module"
                    INSTALL_ERRORS=$((INSTALL_ERRORS+1))
                    return 1
                }
                
                # Install each package with appropriate fallbacks
                install_pkg "python3-flask" "python3-flask" "flask"
                install_pkg "python3-telegram-bot" "python3-python-telegram-bot" "telegram"
                install_pkg "python3-nmap" "python3-nmap" "nmap"
                install_pkg "speedtest-cli" "python3-speedtest-cli" "speedtest"
                install_pkg "python3-requests" "python3-requests" "requests"
                install_pkg "python3-psutil" "python3-psutil" "psutil"
                
                # Check if any packages failed to install
                if [ $INSTALL_ERRORS -gt 0 ]; then
                    log_warning "$INSTALL_ERRORS package(s) failed to install. The application may have limited functionality."
                    # Continue execution but warn the user
                else
                    log_success "All Python packages installed successfully"
                fi
                ;;
                
            redhat)
                if [ "$DISTRO" = "fedora" ]; then
                    log_info "Installing Python packages via dnf..."
                    # Install packages individually with fallbacks
                    INSTALL_ERRORS=0
                    
                    # Function to install a RedHat/Fedora package with fallbacks
                    install_pkg() {
                        local primary_pkg="$1"
                        local fallback_pkg="$2"
                        local python_module="$3"
                        
                        # Check if module already installed in Python
                        if $PYTHON_CMD -c "import $python_module" 2>/dev/null; then
                            log_success "Module $python_module already available"
                            return 0
                        fi
                        
                        # Try primary package
                        log_info "Installing $primary_pkg..."
                        if $SUDO_CMD dnf install -y $primary_pkg >> $LOG_FILE 2>&1; then
                            log_success "Installed $primary_pkg successfully"
                            return 0
                        fi
                        
                        # Try fallback package
                        log_warning "Could not install $primary_pkg, trying $fallback_pkg..."
                        if $SUDO_CMD dnf install -y $fallback_pkg >> $LOG_FILE 2>&1; then
                            log_success "Installed $fallback_pkg successfully"
                            return 0
                        fi
                        
                        log_warning "Failed to install package for $python_module"
                        INSTALL_ERRORS=$((INSTALL_ERRORS+1))
                        return 1
                    }
                    
                    # Install each package with appropriate fallbacks
                    install_pkg "python3-flask" "python3-flask" "flask"
                    install_pkg "python3-telegram-bot" "python3-python-telegram-bot" "telegram"
                    install_pkg "python3-nmap" "python3-nmap" "nmap"
                    install_pkg "speedtest-cli" "python3-speedtest-cli" "speedtest"
                    install_pkg "python3-requests" "python3-requests" "requests"
                    install_pkg "python3-psutil" "python3-psutil" "psutil"
                    
                    # Check if any packages failed to install
                    if [ $INSTALL_ERRORS -gt 0 ]; then
                        log_warning "$INSTALL_ERRORS package(s) failed to install. The application may have limited functionality."
                        # Continue execution but warn the user
                    else
                        log_success "All Python packages installed successfully"
                    fi
                else
                    log_info "Installing Python packages via yum..."
                    # Install packages individually with fallbacks
                    INSTALL_ERRORS=0
                    
                    # Function to install a RedHat/CentOS package with fallbacks
                    install_pkg() {
                        local primary_pkg="$1"
                        local fallback_pkg="$2"
                        local python_module="$3"
                        
                        # Check if module already installed in Python
                        if $PYTHON_CMD -c "import $python_module" 2>/dev/null; then
                            log_success "Module $python_module already available"
                            return 0
                        fi
                        
                        # Try primary package
                        log_info "Installing $primary_pkg..."
                        if $SUDO_CMD yum install -y $primary_pkg >> $LOG_FILE 2>&1; then
                            log_success "Installed $primary_pkg successfully"
                            return 0
                        fi
                        
                        # Try fallback package
                        log_warning "Could not install $primary_pkg, trying $fallback_pkg..."
                        if $SUDO_CMD yum install -y $fallback_pkg >> $LOG_FILE 2>&1; then
                            log_success "Installed $fallback_pkg successfully"
                            return 0
                        fi
                        
                        log_warning "Failed to install package for $python_module"
                        INSTALL_ERRORS=$((INSTALL_ERRORS+1))
                        return 1
                    }
                    
                    # Install each package with appropriate fallbacks
                    install_pkg "python3-flask" "python3-flask" "flask"
                    install_pkg "python3-telegram-bot" "python3-python-telegram-bot" "telegram"
                    install_pkg "python3-nmap" "python3-nmap" "nmap"
                    install_pkg "speedtest-cli" "python3-speedtest-cli" "speedtest"
                    install_pkg "python3-requests" "python3-requests" "requests"
                    install_pkg "python3-psutil" "python3-psutil" "psutil"
                    
                    # Check if any packages failed to install
                    if [ $INSTALL_ERRORS -gt 0 ]; then
                        log_warning "$INSTALL_ERRORS package(s) failed to install. The application may have limited functionality."
                        # Continue execution but warn the user
                    else
                        log_success "All Python packages installed successfully"
                    fi
                fi
                ;;
                
            arch)
                log_info "Installing Python packages via pacman..."
                # Install packages individually with fallbacks
                INSTALL_ERRORS=0
                
                # Function to install an Arch package with fallbacks
                install_pkg() {
                    local primary_pkg="$1"
                    local fallback_pkg="$2"
                    local python_module="$3"
                    
                    # Check if module already installed in Python
                    if $PYTHON_CMD -c "import $python_module" 2>/dev/null; then
                        log_success "Module $python_module already available"
                        return 0
                    fi
                    
                    # Try primary package
                    log_info "Installing $primary_pkg..."
                    if $SUDO_CMD pacman -S --noconfirm $primary_pkg >> $LOG_FILE 2>&1; then
                        log_success "Installed $primary_pkg successfully"
                        return 0
                    fi
                    
                    # Try fallback package if different
                    if [ "$primary_pkg" != "$fallback_pkg" ]; then
                        log_warning "Could not install $primary_pkg, trying $fallback_pkg..."
                        if $SUDO_CMD pacman -S --noconfirm $fallback_pkg >> $LOG_FILE 2>&1; then
                            log_success "Installed $fallback_pkg successfully"
                            return 0
                        fi
                    fi
                    
                    log_warning "Failed to install package for $python_module"
                    INSTALL_ERRORS=$((INSTALL_ERRORS+1))
                    return 1
                }
                
                # Install each package with appropriate fallbacks
                install_pkg "python-flask" "python-flask" "flask"
                install_pkg "python-telegram-bot" "python-telegram-bot" "telegram"
                install_pkg "python-nmap" "python-nmap" "nmap"
                install_pkg "python-speedtest-cli" "speedtest-cli" "speedtest"
                install_pkg "python-requests" "python-requests" "requests"
                install_pkg "python-psutil" "python-psutil" "psutil"
                
                # Check if any packages failed to install
                if [ $INSTALL_ERRORS -gt 0 ]; then
                    log_warning "$INSTALL_ERRORS package(s) failed to install. The application may have limited functionality."
                    # Continue execution but warn the user
                else
                    log_success "All Python packages installed successfully"
                fi
                ;;
                
            suse)
                log_info "Installing Python packages via zypper..."
                # Install packages individually with fallbacks
                INSTALL_ERRORS=0
                
                # Function to install a SUSE package with fallbacks
                install_pkg() {
                    local primary_pkg="$1"
                    local fallback_pkg="$2"
                    local python_module="$3"
                    
                    # Check if module already installed in Python
                    if $PYTHON_CMD -c "import $python_module" 2>/dev/null; then
                        log_success "Module $python_module already available"
                        return 0
                    fi
                    
                    # Try primary package
                    log_info "Installing $primary_pkg..."
                    if $SUDO_CMD zypper --non-interactive install $primary_pkg >> $LOG_FILE 2>&1; then
                        log_success "Installed $primary_pkg successfully"
                        return 0
                    fi
                    
                    # Try fallback package
                    log_warning "Could not install $primary_pkg, trying $fallback_pkg..."
                    if $SUDO_CMD zypper --non-interactive install $fallback_pkg >> $LOG_FILE 2>&1; then
                        log_success "Installed $fallback_pkg successfully"
                        return 0
                    fi
                    
                    log_warning "Failed to install package for $python_module"
                    INSTALL_ERRORS=$((INSTALL_ERRORS+1))
                    return 1
                }
                
                # Install each package with appropriate fallbacks
                install_pkg "python3-Flask" "python3-flask" "flask"
                install_pkg "python3-telegram-bot" "python3-python-telegram-bot" "telegram"
                install_pkg "python3-nmap" "python3-nmap" "nmap"
                install_pkg "python3-speedtest-cli" "speedtest-cli" "speedtest"
                install_pkg "python3-requests" "python3-requests" "requests"
                install_pkg "python3-psutil" "python3-psutil" "psutil"
                
                # Check if any packages failed to install
                if [ $INSTALL_ERRORS -gt 0 ]; then
                    log_warning "$INSTALL_ERRORS package(s) failed to install. The application may have limited functionality."
                    # Continue execution but warn the user
                else
                    log_success "All Python packages installed successfully"
                fi
                ;;
                
            unknown)
                log_warning "Unknown distribution family. Attempting to install packages with available package manager..."
                if command -v apt-get > /dev/null; then
                    log_info "Installing Python packages via apt..."
                    # Install packages individually with fallbacks for unknown distribution
                    INSTALL_ERRORS=0
                    
                    # Function to install a Debian/Ubuntu package with fallbacks
                    install_pkg() {
                        local primary_pkg="$1"
                        local fallback_pkg="$2"
                        local python_module="$3"
                        
                        # Check if module already installed in Python
                        if $PYTHON_CMD -c "import $python_module" 2>/dev/null; then
                            log_success "Module $python_module already available"
                            return 0
                        fi
                        
                        # Try primary package
                        log_info "Installing $primary_pkg..."
                        if $SUDO_CMD apt-get install -y $primary_pkg >> $LOG_FILE 2>&1; then
                            log_success "Installed $primary_pkg successfully"
                            return 0
                        fi
                        
                        # Try fallback package
                        log_warning "Could not install $primary_pkg, trying $fallback_pkg..."
                        if $SUDO_CMD apt-get install -y $fallback_pkg >> $LOG_FILE 2>&1; then
                            log_success "Installed $fallback_pkg successfully"
                            return 0
                        fi
                        
                        log_warning "Failed to install package for $python_module"
                        INSTALL_ERRORS=$((INSTALL_ERRORS+1))
                        return 1
                    }
                    
                    # Install each package with appropriate fallbacks
                    install_pkg "python3-flask" "python3-flask" "flask"
                    install_pkg "python3-telegram-bot" "python3-python-telegram-bot" "telegram"
                    install_pkg "python3-nmap" "python3-nmap" "nmap"
                    install_pkg "speedtest-cli" "python3-speedtest-cli" "speedtest"
                    install_pkg "python3-requests" "python3-requests" "requests"
                    install_pkg "python3-psutil" "python3-psutil" "psutil"
                    
                    # Check if any packages failed to install
                    if [ $INSTALL_ERRORS -gt 0 ]; then
                        log_warning "$INSTALL_ERRORS package(s) failed to install. The application may have limited functionality."
                        # Continue execution but warn the user
                    else
                        log_success "All Python packages installed successfully"
                    fi
                elif command -v dnf > /dev/null; then
                    # Install packages individually with fallbacks for Fedora/RHEL
                    INSTALL_ERRORS=0
                    
                    # Function to install a RedHat/Fedora package with fallbacks
                    install_pkg() {
                        local primary_pkg="$1"
                        local fallback_pkg="$2"
                        local python_module="$3"
                        
                        # Check if module already installed in Python
                        if $PYTHON_CMD -c "import $python_module" 2>/dev/null; then
                            log_success "Module $python_module already available"
                            return 0
                        fi
                        
                        # Try primary package
                        log_info "Installing $primary_pkg..."
                        if $SUDO_CMD dnf install -y $primary_pkg >> $LOG_FILE 2>&1; then
                            log_success "Installed $primary_pkg successfully"
                            return 0
                        fi
                        
                        # Try fallback package
                        log_warning "Could not install $primary_pkg, trying $fallback_pkg..."
                        if $SUDO_CMD dnf install -y $fallback_pkg >> $LOG_FILE 2>&1; then
                            log_success "Installed $fallback_pkg successfully"
                            return 0
                        fi
                        
                        log_warning "Failed to install package for $python_module"
                        INSTALL_ERRORS=$((INSTALL_ERRORS+1))
                        return 1
                    }
                    
                    # Install each package with appropriate fallbacks
                    install_pkg "python3-flask" "python3-flask" "flask"
                    install_pkg "python3-telegram-bot" "python3-python-telegram-bot" "telegram"
                    install_pkg "python3-nmap" "python3-nmap" "nmap"
                    install_pkg "speedtest-cli" "python3-speedtest-cli" "speedtest"
                    install_pkg "python3-requests" "python3-requests" "requests"
                    install_pkg "python3-psutil" "python3-psutil" "psutil"
                    
                    # Check if any packages failed to install
                    if [ $INSTALL_ERRORS -gt 0 ]; then
                        log_warning "$INSTALL_ERRORS package(s) failed to install. The application may have limited functionality."
                        # Continue execution but warn the user
                    else
                        log_success "All Python packages installed successfully"
                    fi
                elif command -v yum > /dev/null; then
                    # Install packages individually with fallbacks for RHEL/CentOS
                    INSTALL_ERRORS=0
                    
                    # Function to install a RedHat/CentOS package with fallbacks
                    install_pkg() {
                        local primary_pkg="$1"
                        local fallback_pkg="$2"
                        local python_module="$3"
                        
                        # Check if module already installed in Python
                        if $PYTHON_CMD -c "import $python_module" 2>/dev/null; then
                            log_success "Module $python_module already available"
                            return 0
                        fi
                        
                        # Try primary package
                        log_info "Installing $primary_pkg..."
                        if $SUDO_CMD yum install -y $primary_pkg >> $LOG_FILE 2>&1; then
                            log_success "Installed $primary_pkg successfully"
                            return 0
                        fi
                        
                        # Try fallback package
                        log_warning "Could not install $primary_pkg, trying $fallback_pkg..."
                        if $SUDO_CMD yum install -y $fallback_pkg >> $LOG_FILE 2>&1; then
                            log_success "Installed $fallback_pkg successfully"
                            return 0
                        fi
                        
                        log_warning "Failed to install package for $python_module"
                        INSTALL_ERRORS=$((INSTALL_ERRORS+1))
                        return 1
                    }
                    
                    # Install each package with appropriate fallbacks
                    install_pkg "python3-flask" "python3-flask" "flask"
                    install_pkg "python3-telegram-bot" "python3-python-telegram-bot" "telegram"
                    install_pkg "python3-nmap" "python3-nmap" "nmap"
                    install_pkg "speedtest-cli" "python3-speedtest-cli" "speedtest"
                    install_pkg "python3-requests" "python3-requests" "requests"
                    install_pkg "python3-psutil" "python3-psutil" "psutil"
                    
                    # Check if any packages failed to install
                    if [ $INSTALL_ERRORS -gt 0 ]; then
                        log_warning "$INSTALL_ERRORS package(s) failed to install. The application may have limited functionality."
                        # Continue execution but warn the user
                    else
                        log_success "All Python packages installed successfully"
                    fi
                elif command -v pacman > /dev/null; then
                    # Install packages individually with fallbacks for Arch
                    INSTALL_ERRORS=0
                    
                    # Function to install an Arch package with fallbacks
                    install_pkg() {
                        local primary_pkg="$1"
                        local fallback_pkg="$2"
                        local python_module="$3"
                        
                        # Check if module already installed in Python
                        if $PYTHON_CMD -c "import $python_module" 2>/dev/null; then
                            log_success "Module $python_module already available"
                            return 0
                        fi
                        
                        # Try primary package
                        log_info "Installing $primary_pkg..."
                        if $SUDO_CMD pacman -S --noconfirm $primary_pkg >> $LOG_FILE 2>&1; then
                            log_success "Installed $primary_pkg successfully"
                            return 0
                        fi
                        
                        # Try fallback package if different
                        if [ "$primary_pkg" != "$fallback_pkg" ]; then
                            log_warning "Could not install $primary_pkg, trying $fallback_pkg..."
                            if $SUDO_CMD pacman -S --noconfirm $fallback_pkg >> $LOG_FILE 2>&1; then
                                log_success "Installed $fallback_pkg successfully"
                                return 0
                            fi
                        fi
                        
                        log_warning "Failed to install package for $python_module"
                        INSTALL_ERRORS=$((INSTALL_ERRORS+1))
                        return 1
                    }
                    
                    # Install each package with appropriate fallbacks
                    install_pkg "python-flask" "python-flask" "flask"
                    install_pkg "python-telegram-bot" "python-telegram-bot" "telegram"
                    install_pkg "python-nmap" "python-nmap" "nmap"
                    install_pkg "python-speedtest-cli" "speedtest-cli" "speedtest"
                    install_pkg "python-requests" "python-requests" "requests"
                    install_pkg "python-psutil" "python-psutil" "psutil"
                    
                    # Check if any packages failed to install
                    if [ $INSTALL_ERRORS -gt 0 ]; then
                        log_warning "$INSTALL_ERRORS package(s) failed to install. The application may have limited functionality."
                        # Continue execution but warn the user
                    else
                        log_success "All Python packages installed successfully"
                    fi
                elif command -v zypper > /dev/null; then
                    # Install packages individually with fallbacks for SUSE
                    INSTALL_ERRORS=0
                    
                    # Function to install a SUSE package with fallbacks
                    install_pkg() {
                        local primary_pkg="$1"
                        local fallback_pkg="$2"
                        local python_module="$3"
                        
                        # Check if module already installed in Python
                        if $PYTHON_CMD -c "import $python_module" 2>/dev/null; then
                            log_success "Module $python_module already available"
                            return 0
                        fi
                        
                        # Try primary package
                        log_info "Installing $primary_pkg..."
                        if $SUDO_CMD zypper --non-interactive install $primary_pkg >> $LOG_FILE 2>&1; then
                            log_success "Installed $primary_pkg successfully"
                            return 0
                        fi
                        
                        # Try fallback package
                        log_warning "Could not install $primary_pkg, trying $fallback_pkg..."
                        if $SUDO_CMD zypper --non-interactive install $fallback_pkg >> $LOG_FILE 2>&1; then
                            log_success "Installed $fallback_pkg successfully"
                            return 0
                        fi
                        
                        log_warning "Failed to install package for $python_module"
                        INSTALL_ERRORS=$((INSTALL_ERRORS+1))
                        return 1
                    }
                    
                    # Install each package with appropriate fallbacks
                    install_pkg "python3-Flask" "python3-flask" "flask"
                    install_pkg "python3-telegram-bot" "python3-python-telegram-bot" "telegram"
                    install_pkg "python3-nmap" "python3-nmap" "nmap"
                    install_pkg "speedtest-cli" "python3-speedtest-cli" "speedtest"
                    install_pkg "python3-requests" "python3-requests" "requests"
                    install_pkg "python3-psutil" "python3-psutil" "psutil"
                    
                    # Check if any packages failed to install
                    if [ $INSTALL_ERRORS -gt 0 ]; then
                        log_warning "$INSTALL_ERRORS package(s) failed to install. The application may have limited functionality."
                        # Continue execution but warn the user
                    else
                        log_success "All Python packages installed successfully"
                    fi
                else
                    log_error "No supported package manager found. Cannot install Python packages." "fatal"
                fi
                ;;
        esac
        
        # Verify installation with detailed feedback
        MISSING=""
        if ! $PYTHON_CMD -c "import flask" 2>/dev/null; then
            MISSING="${MISSING}flask "
        fi
        if ! $PYTHON_CMD -c "import telegram" 2>/dev/null; then
            MISSING="${MISSING}telegram "
        fi
        if ! $PYTHON_CMD -c "import nmap" 2>/dev/null; then
            MISSING="${MISSING}nmap "
        fi
        if ! $PYTHON_CMD -c "import speedtest" 2>/dev/null; then
            MISSING="${MISSING}speedtest "
        fi
        if ! $PYTHON_CMD -c "import requests" 2>/dev/null; then
            MISSING="${MISSING}requests "
        fi
        
        # If any packages are missing, provide detailed warning but continue
        if [ -n "$MISSING" ]; then
            log_warning "Failed to install the following Python packages: ${MISSING}"
            log_warning "Please install them manually using your system's package manager." 
            log_warning "For example, on Debian/Ubuntu: sudo apt-get install python3-flask speedtest-cli python3-requests" 
            log_warning "Check the log file for details: $LOG_FILE"
            log_warning "The application will continue to install but may have limited functionality."
            if [ "$VERBOSE" = "true" ]; then
                echo -e "\n${YELLOW}Package install log:${NC}"
                cat $LOG_FILE | grep -A 10 -B 10 "Installing Python packages" | tail -n 30
            fi
            # Continue with installation instead of exiting
        fi
    else
        log_success "All required Python packages are already installed"
    fi
}

# Clone repository or update if already exists
clone_repository() {
    log_info "Setting up repository..."
    
    # Check if repository already exists in the installation directory
    if [ -d "$INSTALL_DIR/.git" ]; then
        log_info "Repository already exists, updating..."
        cd "$INSTALL_DIR"
        git pull >> $LOG_FILE 2>&1 || log_warning "Could not update the repository. Continuing with existing files."
    else
        # Is there a pulse directory inside the current directory?
        if [ -d "$(pwd)/pulse/.git" ] && [ "$(pwd)" != "$INSTALL_DIR" ]; then
            log_info "Repository exists in current directory, moving to installation directory..."
            $SUDO_CMD rm -rf "$INSTALL_DIR" >> $LOG_FILE 2>&1 || true
            $SUDO_CMD mkdir -p "$(dirname $INSTALL_DIR)" >> $LOG_FILE 2>&1
            $SUDO_CMD mv "$(pwd)/pulse" "$INSTALL_DIR" >> $LOG_FILE 2>&1 || log_error "Failed to move repository to installation directory" "fatal"
        else
            # Clone the repository directly into the installation directory
            log_info "Cloning the repository..."
            git clone "$REPO_URL" "$INSTALL_DIR" >> $LOG_FILE 2>&1 || log_error "Failed to clone repository. Check your internet connection." "fatal"
        fi
    fi
    
    # Ensure permissions are correct
    $SUDO_CMD chmod -R 755 "$INSTALL_DIR" >> $LOG_FILE 2>&1
    
    log_success "Repository setup completed at $INSTALL_DIR"
}

# Function to ensure the pulse file is executable and properly configured
ensure_pulse_executable() {
    log_info "Ensuring pulse file is executable..."
    
    # Make sure the pulse file exists and is executable
    if [ -f "$INSTALL_DIR/pulse" ]; then
        $SUDO_CMD chmod +x "$INSTALL_DIR/pulse"
        log_success "Pulse launcher script is executable"
    else
        log_error "Pulse launcher script not found at $INSTALL_DIR/pulse" "fatal"
    fi
    
    # Update the INSTALL_DIR in the pulse script
    log_info "Updating installation directory in pulse script..."
    
    # Create a temporary file with the updated content - simplified version without virtual environment
    cat > /tmp/pulse.tmp << EOF
#!/bin/bash
# Cybex Pulse launcher script
# This script starts the Cybex Pulse application

# Use the installation directory from the install script
INSTALL_DIR="${INSTALL_DIR}"

# Create a dynamic wrapper module for direct execution if it doesn't exist
if [ ! -f "\$INSTALL_DIR/run_app.py" ]; then
    cat > "\$INSTALL_DIR/run_app.py" << EOT
#!/usr/bin/env python3
# Dynamic wrapper to execute the application directly
import os
import sys

# Add the root directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Try to import from different approaches
try:
    # Try to run directly from the module
    from cybex_pulse.__main__ import main
    main()
except ImportError:
    try:
        # Try direct import of individual files
        import __main__
        __main__.main()
    except (ImportError, AttributeError):
        # Last resort - execute the main script directly
        try:
            with open(os.path.join(current_dir, '__main__.py'), 'r') as f:
                exec(f.read())
        except Exception as e:
            print(f"All execution methods failed: {e}")
            sys.exit(1)
EOT
    chmod +x "\$INSTALL_DIR/run_app.py"
fi

# Change to the Pulse directory and run the application directly
# Use exec to replace the shell process with Python to properly handle signals
cd \$INSTALL_DIR && export PYTHONPATH=\$INSTALL_DIR:\$PYTHONPATH && exec python3 "\$INSTALL_DIR/run_app.py" "\$@"
EOF
    
    # Replace the original pulse file with the updated one
    $SUDO_CMD mv /tmp/pulse.tmp "$INSTALL_DIR/pulse"
    $SUDO_CMD chmod +x "$INSTALL_DIR/pulse"
    
    log_success "Pulse launcher script configured to use $INSTALL_DIR (without virtual environment)"
}

# Create a systemd service file
create_service() {
    log_info "Creating systemd service..."
    
    # Create necessary system directories for logs and data
    log_info "Creating system directories for logs and data..."
    $SUDO_CMD mkdir -p /var/log/cybex_pulse 2>/dev/null || true
    $SUDO_CMD mkdir -p /var/lib/cybex_pulse 2>/dev/null || true
    $SUDO_CMD chmod 755 /var/log/cybex_pulse 2>/dev/null || true
    $SUDO_CMD chmod 755 /var/lib/cybex_pulse 2>/dev/null || true
    
    # Create systemd service file
    cat > /tmp/cybex-pulse.service << EOF
[Unit]
Description=Cybex Pulse Network Monitoring
After=network.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${INSTALL_DIR}/pulse
WorkingDirectory=${INSTALL_DIR}
Environment="PYTHONPATH=${INSTALL_DIR}"
Environment="PYTHONPATH_IGNORE_PEP668=1"
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
# Security hardening
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths=/var/log/cybex_pulse /var/lib/cybex_pulse
NoNewPrivileges=true
PrivateTmp=true
CapabilityBoundingSet=CAP_NET_RAW

[Install]
WantedBy=multi-user.target
EOF

    # Move to systemd directory if systemd is available
    if command -v systemctl >/dev/null 2>&1; then
        if [ -d "/etc/systemd/system" ]; then
            $SUDO_CMD mv /tmp/cybex-pulse.service /etc/systemd/system/
            $SUDO_CMD systemctl daemon-reload
            log_success "Systemd service created successfully"
        else
            log_warning "Could not create systemd service: directory not found"
        fi
    else
        # Try to create init.d script for non-systemd systems
        log_warning "Systemd not detected. Attempting to create init script instead..."
        
        # Create init script
        cat > /tmp/cybex-pulse << EOF
#!/bin/sh
### BEGIN INIT INFO
# Provides:          cybex-pulse
# Required-Start:    \$network \$local_fs \$remote_fs
# Required-Stop:     \$network \$local_fs \$remote_fs
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Cybex Pulse Network Monitoring
# Description:       Cybex Pulse Network Monitoring and Security
### END INIT INFO

DESC="Cybex Pulse Network Monitoring"
NAME=cybex-pulse
DAEMON=${INSTALL_DIR}/pulse
DAEMON_ARGS=""
PIDFILE=/var/run/\$NAME.pid
SCRIPTNAME=/etc/init.d/\$NAME
WORKDIR=${INSTALL_DIR}
PYTHON_PATH=${INSTALL_DIR}

# Export the python path
export PYTHONPATH=\$PYTHON_PATH
export PYTHONPATH_IGNORE_PEP668=1

# Exit if the package is not installed
[ -x "\$DAEMON" ] || exit 0

# Define LSB log_* functions
. /lib/lsb/init-functions

do_start() {
    log_daemon_msg "Starting \$DESC" "\$NAME"
    cd \$WORKDIR
    start-stop-daemon --start --quiet --background --make-pidfile --pidfile \$PIDFILE --exec \$DAEMON -- \$DAEMON_ARGS
    log_end_msg \$?
}

do_stop() {
    log_daemon_msg "Stopping \$DESC" "\$NAME"
    start-stop-daemon --stop --quiet --retry=TERM/30/KILL/5 --pidfile \$PIDFILE
    RETVAL="\$?"
    [ "\$RETVAL" = 2 ] && return 2
    rm -f \$PIDFILE
    log_end_msg \$RETVAL
    return "\$RETVAL"
}

case "\$1" in
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    restart|force-reload)
        do_stop
        case "\$?" in
            0|1)
                do_start
                ;;
            *)
                log_end_msg 1
                ;;
        esac
        ;;
    status)
        status_of_proc "\$DAEMON" "\$NAME" && exit 0 || exit \$?
        ;;
    *)
        echo "Usage: \$SCRIPTNAME {start|stop|restart|force-reload|status}" >&2
        exit 3
        ;;
esac

exit 0
EOF

        if [ -d "/etc/init.d" ]; then
            $SUDO_CMD mv /tmp/cybex-pulse /etc/init.d/
            $SUDO_CMD chmod +x /etc/init.d/cybex-pulse
            
            # Try to update run levels
            if command -v update-rc.d >/dev/null 2>&1; then
                $SUDO_CMD update-rc.d cybex-pulse defaults
            elif command -v chkconfig >/dev/null 2>&1; then
                $SUDO_CMD chkconfig --add cybex-pulse
            fi
            
            log_success "Init script created successfully"
        else
            log_warning "Could not create init script: directory not found"
        fi
    fi
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."
    
    # Check Python interpreter
    if [ -z "$PYTHON_CMD" ]; then
        # If PYTHON_CMD is not set, try to find a suitable Python
        for cmd in python3 python; do
            if command -v $cmd &> /dev/null; then
                PYTHON_CMD=$cmd
                break
            fi
        done
    fi
    
    if ! command -v "$PYTHON_CMD" &> /dev/null; then
        log_error "Python interpreter $PYTHON_CMD not found. Installation may not work correctly."
    else
        log_success "Python interpreter: $PYTHON_CMD ($(${PYTHON_CMD} --version 2>&1))"
    fi
    
    # Check if core requirements are available
    echo "Checking core Python packages..." >> $LOG_FILE
    
    local MISSING_PKGS=""
    for pkg in flask telegram nmap requests psutil; do
        if ! $PYTHON_CMD -c "import $pkg" &>/dev/null; then
            MISSING_PKGS="$MISSING_PKGS $pkg"
        else
            # Try to get version
            version=$($PYTHON_CMD -c "import $pkg; print(getattr($pkg, '__version__', 'unknown'))" 2>/dev/null)
            echo "Package $pkg: $version" >> $LOG_FILE
        fi
    done
    
    if [ -n "$MISSING_PKGS" ]; then
        log_warning "Some Python packages are missing:$MISSING_PKGS"
        log_warning "The application may not function correctly without these packages."
    else
        log_success "All core Python packages are available"
    fi
    
    # Check if pulse launcher script works
    if [ -f "${INSTALL_DIR}/pulse" ]; then
        log_success "Pulse launcher script found at ${INSTALL_DIR}/pulse"
    else
        log_warning "Pulse launcher script not found at expected location: ${INSTALL_DIR}/pulse"
    fi
    
    # Check if installation directory has git repository
    if [ -d "${INSTALL_DIR}/.git" ]; then
        log_success "Git repository verified at ${INSTALL_DIR}"
    else
        log_warning "Git repository not found at ${INSTALL_DIR}. Auto-updates may not work correctly."
    fi
    
    # Check service installation
    if command -v systemctl &>/dev/null && [ -f "/etc/systemd/system/cybex-pulse.service" ]; then
        log_success "Systemd service installed"
    elif [ -f "/etc/init.d/cybex-pulse" ]; then
        log_success "Init.d service installed"
    else
        log_warning "No service installed, application will need to be started manually"
    fi
    
    # Check system directories
    if [ -d "/var/log/cybex_pulse" ]; then
        log_success "Log directory created successfully at /var/log/cybex_pulse"
    else
        log_warning "Log directory not found at /var/log/cybex_pulse"
    fi
    
    if [ -d "/var/lib/cybex_pulse" ]; then
        log_success "Data directory created successfully at /var/lib/cybex_pulse"
    else
        log_warning "Data directory not found at /var/lib/cybex_pulse"
    fi
}

# Display completion message
print_completion() {
    # Installation directory is already set globally, no need to overwrite it
    
    # Run verification checks
    verify_installation
    
    echo -e "\n${GREEN}${BOLD}Cybex Pulse Installation Completed!${NC}\n"
    
    echo -e "${BLUE}Installation Details:${NC}"
    echo -e "  - ${BOLD}Repository:${NC} $INSTALL_DIR"
    echo -e "  - ${BOLD}Python:${NC} $PYTHON_CMD ($(${PYTHON_CMD} --version 2>&1))"
    echo -e "  - ${BOLD}Log File:${NC} $LOG_FILE"
    echo
    
    # Get all IP addresses
    echo -e "${YELLOW}Network Interfaces:${NC}"
    IP_ADDRESSES=$(ip -4 addr show scope global | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | sort)
    if [ -z "$IP_ADDRESSES" ]; then
        echo -e "  ${BOLD}IP Address:${NC} Could not detect (check network settings)"
        IP_ADDRESS="YOUR_IP_ADDRESS"
    else
        while read -r line; do
            echo -e "  ${BOLD}IP Address:${NC} $line"
        done <<< "$IP_ADDRESSES"
        # Use first IP for web interface
        IP_ADDRESS=$(echo "$IP_ADDRESSES" | head -n 1)
    fi
    
    echo -e "\n${GREEN}Usage Instructions:${NC}"
    echo -e "  - ${BOLD}Run the application manually:${NC} $INSTALL_DIR/pulse"
    
    if command -v systemctl &>/dev/null && [ -f "/etc/systemd/system/cybex-pulse.service" ]; then
        echo -e "  - ${BOLD}Start as a service:${NC} sudo systemctl start cybex-pulse"
        echo -e "  - ${BOLD}Enable at boot:${NC} sudo systemctl enable cybex-pulse"
        echo -e "  - ${BOLD}Check service status:${NC} sudo systemctl status cybex-pulse"
    elif [ -f "/etc/init.d/cybex-pulse" ]; then
        echo -e "  - ${BOLD}Start as a service:${NC} sudo service cybex-pulse start"
        echo -e "  - ${BOLD}Enable at boot:${NC} sudo update-rc.d cybex-pulse defaults"
        echo -e "  - ${BOLD}Check service status:${NC} sudo service cybex-pulse status"
    fi
    
    echo
    echo -e "${YELLOW}${BOLD}Web Interface:${NC}"
    echo -e "  After starting, access the web interface at ${BLUE}http://$IP_ADDRESS:8080${NC}"
    echo
    echo -e "${BLUE}Troubleshooting:${NC}"
    echo -e "  - If the application fails to start, check the log file: $LOG_FILE"
    echo -e "  - Run with verbose option: $INSTALL_DIR/pulse --verbose"
    echo -e "  - Check system Python packages if experiencing import errors"
    echo
    echo -e "${BLUE}For issues or more information, visit:${NC} ${BOLD}https://github.com/DigitalPals/pulse${NC}"
    echo
    
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${YELLOW}Installation Log Summary:${NC}"
        echo -e "  You can view the full log at: $LOG_FILE"
        echo
        echo -e "${YELLOW}Last 10 installation log entries:${NC}"
        tail -n 10 "$LOG_FILE" | sed 's/^/  /'
        echo
    fi
}

# Display usage information
display_help() {
    echo -e "${BOLD}${BLUE}Cybex Pulse Installation Script${NC}"
    echo -e "${BLUE}====================================${NC}\n"
    echo -e "Usage: $0 [OPTIONS]"
    echo
    echo -e "Options:"
    echo -e "  -v, --verbose      Enable verbose output (show detailed logs)"
    echo -e "  -h, --help         Display this help message"
    echo -e "  -n, --no-service   Don't create system service"
    echo -e "  -p, --python PATH  Use specific Python interpreter"
    echo -e "  --no-sudo          Don't use sudo even if available"
    echo -e "  --check-only       Only check prerequisites, don't install"
    echo
    echo -e "Example:"
    echo -e "  sudo $0 --verbose --python python3.9"
    echo
    echo -e "For issues or more information, visit: https://github.com/DigitalPals/pulse"
    exit 0
}

# Process command line arguments
process_args() {
    NO_SERVICE="false"
    CHECK_ONLY="false"
    USER_PYTHON=""
    NO_SUDO="false"
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                display_help
                ;;
            -v|--verbose)
                VERBOSE="true"
                echo -e "${YELLOW}Verbose mode enabled. Detailed output will be shown.${NC}"
                ;;
            -n|--no-service)
                NO_SERVICE="true"
                echo -e "${YELLOW}Service creation disabled.${NC}"
                ;;
            -p|--python)
                if [[ -z "${2:-}" || "${2:-}" == -* ]]; then
                    log_error "Python path not specified." "fatal"
                fi
                USER_PYTHON="${2:-}"
                echo -e "${YELLOW}Using specified Python interpreter: $USER_PYTHON${NC}"
                shift
                ;;
            --no-sudo)
                NO_SUDO="true"
                SUDO_CMD=""
                echo -e "${YELLOW}Sudo usage disabled.${NC}"
                ;;
            --check-only)
                CHECK_ONLY="true"
                echo -e "${YELLOW}Running in check-only mode.${NC}"
                ;;
            *)
                echo -e "${YELLOW}Unknown option: $1${NC}"
                ;;
        esac
        shift
    done
    
    # If user specified a Python interpreter, check if it exists
    if [ -n "$USER_PYTHON" ]; then
        if command -v "$USER_PYTHON" &> /dev/null; then
            PYTHON_CMD="$USER_PYTHON"
            echo -e "${GREEN}Using Python interpreter: $PYTHON_CMD${NC}"
        else
            log_error "Specified Python interpreter not found: $USER_PYTHON" "fatal"
        fi
    fi
    
    # If NO_SUDO is true, don't use sudo
    if [ "$NO_SUDO" = "true" ]; then
        SUDO_CMD=""
    fi
}

# Function to check system information
check_system_info() {
    log_info "Checking system information..."
    
    # Check for required tools
    for cmd in git curl; do
        if ! command -v $cmd &> /dev/null; then
            log_warning "Command '$cmd' is not installed, some functionality may be limited"
        else
            log_success "Command '$cmd' is available"
        fi
    done
    
    # Check connectivity
    if ping -c 1 github.com &>/dev/null; then
        log_success "Network connectivity: OK"
    else
        log_warning "Network connectivity: ISSUE - Cannot reach github.com"
        if ping -c 1 8.8.8.8 &>/dev/null; then
            log_warning "Can reach IP addresses but not hostnames. Possible DNS issue."
        else
            log_warning "Cannot reach external IP addresses. Check your network connection."
        fi
    fi
    
    # Check disk space
    FREE_SPACE=$(df -h . | awk 'NR==2 {print $4}')
    log_info "Free disk space: $FREE_SPACE"
    
    # Memory information
    if command -v free &>/dev/null; then
        MEM_INFO=$(free -h | grep Mem | awk '{print $2}')
        log_info "System memory: $MEM_INFO"
    fi
}

# Main function
main() {
    echo -e "${BOLD}${BLUE}Cybex Pulse Installation${NC}"
    echo -e "${BLUE}=============================${NC}\n"
    
    # Process command line arguments
    process_args "$@"
    
    # Check system information and log it
    check_system_info
    
    # If check-only mode, exit here
    if [ "$CHECK_ONLY" = "true" ]; then
        log_info "Check-only mode active, exiting without installation"
        exit 0
    fi
    
    # Check if script is running as root or has sudo access
    if [ "$EUID" -ne 0 ]; then
        if [ "$NO_SUDO" = "false" ] && command -v sudo >/dev/null 2>&1; then
            log_warning "This script should be run as root. Will attempt to use sudo for privileged operations."
            # Test if user has sudo privileges
            if sudo -n true 2>/dev/null; then
                SUDO_CMD="sudo"
            else
                log_error "Cannot use sudo without password. Please run this script as root or with sudo." "fatal"
            fi
        else
            log_error "This script requires root privileges and sudo is not available. Please run as root." "fatal"
        fi
    fi
    
    # Step 1: Detect distribution
    detect_distribution
    
    # Step 2: Set up installation directories
    set_install_directories
    
    # Step 3: Install system dependencies
    install_dependencies
    
    # Step 4: Install packages via system package manager
    install_system_packages
    
    # Step 5: Clone repository to correct location
    clone_repository
    
    # Step 6: Ensure pulse file is executable and properly configured
    ensure_pulse_executable
    
    # Step 7: Create systemd service (unless --no-service is specified)
    if [ "$NO_SERVICE" = "false" ]; then
        create_service
    else
        log_info "Skipping service creation as requested"
    fi
    
    # Print completion message
    print_completion
    
    # Exit with success
    exit 0
}

# Execute main function with all arguments
main "$@"
exit 0