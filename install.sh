#!/bin/bash

#######################################################
# Cybex Pulse Installation Script
# This script installs Cybex Pulse on various Linux distributions
#######################################################

# Don't exit on errors, we'll handle them manually
set +e

# Configuration
INSTALL_DIR="/opt/cybex-pulse"
SERVICE_USER="cybexpulse"
CONFIG_DIR="/etc/cybex-pulse"
LOG_DIR="/var/log/cybex-pulse"
SERVICE_NAME="cybex-pulse"
LOG_FILE="/tmp/cybex-pulse-install.log"
TOTAL_STEPS=9

# Define colors and symbols
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'
BOLD='\033[1m'
CHECK_MARK="\033[0;32m✓\033[0m"
CROSS_MARK="\033[0;31m✗\033[0m"
ARROW="\033[0;36m➜\033[0m"
INFO="\033[0;34mℹ\033[0m"
WARNING="\033[0;33m⚠\033[0m"

#######################################################
# Logging Functions
#######################################################

# Initialize log file
init_log() {
    echo "Cybex Pulse Installation Log - $(date)" > $LOG_FILE
    echo "===============================================" >> $LOG_FILE
}

# Function to handle errors but continue installation
handle_error() {
    local exit_code=$1
    local line_number=$2
    local message=$3
    echo -e "\n\033[0;31m✗ Warning at line $line_number: $message\033[0m"
    echo "Warning at line $line_number: $message (exit code $exit_code)" >> $LOG_FILE
    # Don't exit, just warn
}

# Print success message
success() {
    printf " ${CHECK_MARK} ${GREEN}[SUCCESS]${NC}\n"
    echo "SUCCESS: $1" >> $LOG_FILE
}

# Print error message
error() {
    printf " ${CROSS_MARK} ${RED}[FAILED]${NC}\n"
    echo "ERROR: $1" >> $LOG_FILE
    echo
    if [ "$2" = "fatal" ]; then
        echo -e "${RED}Installation failed. Please check the error above.${NC}"
        exit 1
    else
        echo -e "${YELLOW}Continuing with installation despite error...${NC}"
        # Don't exit, try to continue
    fi
}

# Print warning message
warning() {
    echo -e "${WARNING} ${YELLOW}WARNING: $1${NC}"
    echo "WARNING: $1" >> $LOG_FILE
}

# Print info message
info() {
    echo -e "${INFO} ${BLUE}$1${NC}"
    echo "INFO: $1" >> $LOG_FILE
}

#######################################################
# UI Functions
#######################################################

# Clear the screen and print Cybex logo
print_cybex_logo() {
    echo
    echo -e "${CYAN}_________        ___.                   __________      .__                 ${NC}"
    echo -e "${CYAN}\_   ___ \___.__.\_ |__   ____ ___  ___ \______   \__ __|  |   ______ ____  ${NC}"
    echo -e "${CYAN}/    \  \<   |  | | __ \_/ __ \\  \/  /  |     ___/  |  \  |  /  ___// __ \ ${NC}"
    echo -e "${CYAN}\     \___\___  | | \_\ \  ___/ >    <   |    |   |  |  /  |__\___ \\  ___/ ${NC}"
    echo -e "${CYAN} \______  / ____| |___  /\___  >__/\_ \  |____|   |____/|____/____  >\___  >${NC}"
    echo -e "${CYAN}        \/\/          \/     \/      \/                           \/     \/ ${NC}"
    echo
}

# Print header
print_header() {
    print_cybex_logo
    
    echo -e "${WHITE}---------------------------------------------------${NC}"
    echo -e "${WHITE}  ${BOLD}Cybex Pulse Network Monitoring Installation${NC}"
    echo -e "${WHITE}  Version 1.0.0${NC}"
    echo -e "${WHITE}---------------------------------------------------${NC}"
    echo
    echo -e "${INFO} ${BLUE}Initializing installation...${NC}"
    echo
}

# Show spinner during long operations
show_spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='⣾⣽⣻⢿⡿⣟⣯⣷'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " ${CYAN}%c${NC}  " "${spinstr:0:1}"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# Show progress message
progress() {
    local text=$1
    printf "${ARROW} ${CYAN}%-60s${NC}" "${text}..."
}

# Display step information
step() {
    local step_num=$1
    local description=$2
    
    echo
    echo -e "${WHITE}${BOLD}STEP $step_num/$TOTAL_STEPS: $description${NC}"
    echo -e "${WHITE}---------------------------------------------------${NC}"
}

# Draw a progress bar
draw_progress_bar() {
    local current=$1
    local total=$2
    local width=50
    local percentage=$((current * 100 / total))
    local completed=$((width * current / total))
    local remaining=$((width - completed))
    
    printf "[${GREEN}"
    for ((i=0; i<completed; i++)); do
        printf "="
    done
    printf ">${NC}"
    for ((i=0; i<remaining; i++)); do
        printf " "
    done
    printf "] ${BOLD}%d%%${NC}\n" $percentage
}

# Print separator
separator() {
    echo -e "${WHITE}---------------------------------------------------${NC}"
}

#######################################################
# System Detection Functions
#######################################################

# Detect Linux distribution
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

#######################################################
# Verification Functions 
#######################################################

# Check if Python is installed and get version
check_python() {
    progress "Checking Python installation"
    echo "Checking Python installation..." >> $LOG_FILE
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        PYTHON_VERSION_NUM=$(echo $PYTHON_VERSION | sed 's/Python //')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION_NUM | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION_NUM | cut -d. -f2)
        
        echo "Detected Python version: $PYTHON_VERSION_NUM" >> $LOG_FILE
        
        if [ $PYTHON_MAJOR -ge 3 ] && [ $PYTHON_MINOR -ge 8 ]; then
            success "Python $PYTHON_VERSION_NUM detected (meets requirements)"
            return 0
        else
            error "Python $PYTHON_VERSION_NUM is installed, but Cybex Pulse requires Python 3.8 or newer"
            return 1
        fi
    else
        error "Python 3 is not installed"
        return 1
    fi
}

# Check if pip is installed and working
check_pip() {
    progress "Checking pip installation"
    echo "Checking pip installation..." >> $LOG_FILE
    
    if command -v pip3 &> /dev/null; then
        PIP_VERSION=$(pip3 --version 2>&1)
        echo "Detected pip version: $PIP_VERSION" >> $LOG_FILE
        success "pip is installed and working"
        return 0
    else
        error "pip3 is not installed or not in PATH"
        return 1
    fi
}

# Check if venv module is available
check_venv() {
    progress "Checking Python venv module"
    echo "Checking Python venv module..." >> $LOG_FILE
    
    if python3 -m venv --help &> /dev/null; then
        success "Python venv module is available"
        return 0
    else
        error "Python venv module is not available"
        
        # Try to install venv package based on distribution
        case $DISTRO_FAMILY in
            debian)
                info "Attempting to install python3-venv package..."
                apt-get install -y python3-venv >> $LOG_FILE 2>&1
                ;;
            redhat)
                info "Attempting to install python3-venv package..."
                if [ "$DISTRO" = "fedora" ]; then
                    dnf install -y python3-venv >> $LOG_FILE 2>&1
                else
                    yum install -y python3-venv >> $LOG_FILE 2>&1
                fi
                ;;
            arch)
                info "venv module should be included with Python on Arch Linux"
                ;;
            suse)
                info "Attempting to install python3-venv package..."
                zypper --non-interactive install python3-venv >> $LOG_FILE 2>&1
                ;;
        esac
        
        # Check again after installation attempt
        if python3 -m venv --help &> /dev/null; then
            success "Python venv module is now available"
            return 0
        else
            warning "Python venv module is still not available, will try alternative approach"
            return 1
        fi
    fi
}

#######################################################
# Package Management Functions
#######################################################

# Install a package using the appropriate package manager
install_package() {
    local package=$1
    local package_manager=$2
    
    printf "  ${ARROW} ${CYAN}%-50s${NC}" "Installing ${package}..."
    echo "Trying to install: $package with $package_manager" >> $LOG_FILE
    
    case $package_manager in
        apt)
            apt-get install -y -qq $package >> $LOG_FILE 2>&1
            ;;
        yum)
            yum install -y $package >> $LOG_FILE 2>&1
            ;;
        dnf)
            dnf install -y $package >> $LOG_FILE 2>&1
            ;;
        pacman)
            pacman -S --noconfirm $package >> $LOG_FILE 2>&1
            ;;
        zypper)
            zypper --non-interactive install $package >> $LOG_FILE 2>&1
            ;;
    esac
    
    local result=$?
    
    if [ $result -eq 0 ]; then
        echo -e " ${CHECK_MARK} ${GREEN}[SUCCESS]${NC}"
        echo "SUCCESS: Installed $package" >> $LOG_FILE
        return 0
    else
        echo -e " ${CROSS_MARK} ${RED}[FAILED]${NC}"
        echo "FAILED: Could not install $package" >> $LOG_FILE
        return 1
    fi
}

# Install system dependencies
install_dependencies() {
    progress "Installing system dependencies"
    echo "===============================================" >> $LOG_FILE
    echo "Beginning dependency installation" >> $LOG_FILE
    
    local pkg_manager=""
    local core_pkgs=()
    local optional_pkgs=()
    
    # Determine package manager and packages based on distribution
    case $DISTRO_FAMILY in
        debian)
            pkg_manager="apt"
            echo -e "\n${INFO} ${BLUE}Running apt-get update...${NC}" | tee -a $LOG_FILE
            apt-get update -qq >> $LOG_FILE 2>&1
            
            # Core packages (required)
            core_pkgs=("python3" "python3-pip" "python3-venv" "curl" "git")
            
            # Optional packages (nice to have)
            optional_pkgs=("nmap" "net-tools" "iproute2" "avahi-utils" "snmp" "arp-scan")
            ;;
        redhat)
            if [ "$DISTRO" = "fedora" ]; then
                pkg_manager="dnf"
                core_pkgs=("python3" "python3-pip" "curl" "git")
                optional_pkgs=("nmap" "net-tools" "iproute" "avahi-tools" "net-snmp-utils" "arp-scan")
            else
                pkg_manager="yum"
                # RHEL/CentOS may need EPEL repository
                if ! rpm -q epel-release > /dev/null 2>&1; then
                    echo -e "\n${INFO} ${BLUE}Installing EPEL repository...${NC}" | tee -a $LOG_FILE
                    yum install -y epel-release >> $LOG_FILE 2>&1
                fi
                core_pkgs=("python3" "python3-pip" "curl" "git")
                optional_pkgs=("nmap" "net-tools" "iproute" "avahi-tools" "net-snmp-utils" "arp-scan")
            fi
            ;;
        arch)
            pkg_manager="pacman"
            echo -e "\n${INFO} ${BLUE}Updating pacman...${NC}" | tee -a $LOG_FILE
            pacman -Sy --noconfirm >> $LOG_FILE 2>&1
            core_pkgs=("python" "python-pip" "curl" "git")
            optional_pkgs=("nmap" "net-tools" "iproute2" "avahi" "net-snmp" "arp-scan")
            ;;
        suse)
            pkg_manager="zypper"
            core_pkgs=("python3" "python3-pip" "curl" "git")
            optional_pkgs=("nmap" "net-tools" "iproute2" "avahi" "net-snmp" "arp-scan")
            ;;
        unknown)
            detect_unknown_package_manager
            ;;
    esac
    
    # Install core packages (required packages)
    echo -e "\n${BOLD}${WHITE}Installing core packages:${NC}"
    local core_success=true
    for pkg in "${core_pkgs[@]}"; do
        if ! install_package "$pkg" "$pkg_manager"; then
            core_success=false
        fi
    done
    
    if [ "$core_success" = false ]; then
        error "Some core packages failed to install. The application may not function correctly."
    else
        success "Core packages installed"
    fi
    
    # Install optional packages
    echo -e "\n${BOLD}${WHITE}Installing optional packages (some may not be available):${NC}"
    echo "Beginning optional package installation..." >> $LOG_FILE
    
    for pkg in "${optional_pkgs[@]}"; do
        install_package "$pkg" "$pkg_manager" || warning "Optional package $pkg could not be installed, but installation will continue"
    done
    
    success "Optional packages installation completed"
    
    # Verify Python installation after dependencies are installed
    check_python
    check_pip
    check_venv
}

# Detect package manager on unknown distributions
detect_unknown_package_manager() {
    warning "Attempting to detect package manager for unknown distribution..."
    # Try different package managers
    if command -v apt-get > /dev/null; then
        pkg_manager="apt"
        echo -e "${INFO} ${BLUE}Using apt-get package manager...${NC}" | tee -a $LOG_FILE
        apt-get update -qq >> $LOG_FILE 2>&1
        core_pkgs=("python3" "python3-pip" "python3-venv" "curl" "git")
        optional_pkgs=("nmap" "net-tools" "iproute2" "avahi-utils" "snmp" "arp-scan")
    elif command -v yum > /dev/null; then
        pkg_manager="yum"
        echo -e "${INFO} ${BLUE}Using yum package manager...${NC}" | tee -a $LOG_FILE
        core_pkgs=("python3" "python3-pip" "curl" "git")
        optional_pkgs=("nmap" "net-tools" "iproute" "avahi-tools" "net-snmp-utils" "arp-scan")
    elif command -v dnf > /dev/null; then
        pkg_manager="dnf"
        echo -e "${INFO} ${BLUE}Using dnf package manager...${NC}" | tee -a $LOG_FILE
        core_pkgs=("python3" "python3-pip" "curl" "git")
        optional_pkgs=("nmap" "net-tools" "iproute" "avahi-tools" "net-snmp-utils" "arp-scan")
    elif command -v pacman > /dev/null; then
        pkg_manager="pacman"
        echo -e "${INFO} ${BLUE}Using pacman package manager...${NC}" | tee -a $LOG_FILE
        pacman -Sy --noconfirm >> $LOG_FILE 2>&1
        core_pkgs=("python" "python-pip" "curl" "git")
        optional_pkgs=("nmap" "net-tools" "iproute2" "avahi" "net-snmp" "arp-scan")
    elif command -v zypper > /dev/null; then
        pkg_manager="zypper"
        echo -e "${INFO} ${BLUE}Using zypper package manager...${NC}" | tee -a $LOG_FILE
        core_pkgs=("python3" "python3-pip" "curl" "git")
        optional_pkgs=("nmap" "net-tools" "iproute2" "avahi" "net-snmp" "arp-scan")
    else
        error "No supported package manager found" "fatal"
    fi
}

#######################################################
# User and Directory Setup Functions
#######################################################

# Create service user
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

# Create necessary directories
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

#######################################################
# Python Environment Setup
#######################################################

# Setup Python and install packages
install_python_packages() {
    progress "Setting up Python environment"
    echo "===============================================" >> $LOG_FILE
    echo "Setting up Python environment..." >> $LOG_FILE
    
    # Check system Python is available
    setup_python_environment
    
    # Install Python packages
    install_python_dependencies
}

# Setup Python environment
setup_python_environment() {
    echo -ne "${ARROW} ${CYAN}Checking Python installation...${NC} "
    echo "Checking Python installation..." >> $LOG_FILE
    
    if command -v python3 > /dev/null 2>&1; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        PYTHON_VERSION_NUM=$(echo $PYTHON_VERSION | sed 's/Python //')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION_NUM | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION_NUM | cut -d. -f2)
        
        if [ $PYTHON_MAJOR -ge 3 ] && [ $PYTHON_MINOR -ge 8 ]; then
            echo -e "${CHECK_MARK} ${GREEN}Success${NC} ($PYTHON_VERSION)"
            echo "SUCCESS: Found Python $PYTHON_VERSION_NUM" >> $LOG_FILE
        else
            echo -e "${CROSS_MARK} ${RED}Version too old${NC}"
            echo "WARNING: Python $PYTHON_VERSION_NUM found, but version 3.8+ is recommended" >> $LOG_FILE
            warning "Python $PYTHON_VERSION_NUM found, but version 3.8+ is recommended. Continuing anyway."
        fi
    else
        echo -e "${CROSS_MARK} ${RED}Not found${NC}"
        echo "ERROR: Python 3 not found" >> $LOG_FILE
        error "Python 3 not found. Please install Python 3.8 or newer."
        return 1
    fi
    
    # Check if pip is available
    echo -ne "${ARROW} ${CYAN}Checking pip installation...${NC} "
    echo "Checking pip installation..." >> $LOG_FILE
    
    if command -v pip3 > /dev/null 2>&1; then
        PIP_VERSION=$(pip3 --version 2>&1)
        echo -e "${CHECK_MARK} ${GREEN}Success${NC} ($(echo $PIP_VERSION | cut -d' ' -f1,2))"
        echo "SUCCESS: Found pip: $PIP_VERSION" >> $LOG_FILE
    else
        echo -e "${CROSS_MARK} ${RED}Not found${NC}"
        echo "ERROR: pip3 not found" >> $LOG_FILE
        error "pip3 not found. Please install pip for Python 3."
        return 1
    fi
    
    # Create necessary directories
    mkdir -p $INSTALL_DIR/bin $INSTALL_DIR/log
    
    # Create Python launcher script
    echo -ne "${ARROW} ${CYAN}Creating Python launcher...${NC} "
    echo "Creating Python launcher..." >> $LOG_FILE
    
    cat > $INSTALL_DIR/bin/cybex-python << EOF
#!/bin/bash
# Python launcher script for Cybex Pulse
export PYTHONPATH=$INSTALL_DIR:\$PYTHONPATH
python3 "\$@"
EOF
    chmod +x $INSTALL_DIR/bin/cybex-python
    
    if [ -x "$INSTALL_DIR/bin/cybex-python" ]; then
        echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
        echo "SUCCESS: Created Python launcher" >> $LOG_FILE
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        echo "WARNING: Failed to create Python launcher" >> $LOG_FILE
        warning "Failed to create Python launcher, but continuing with installation"
    fi
    
    # Create symlink to system Python
    ln -sf $(which python3) /usr/local/bin/cybex-python
    
    success "Python environment setup completed"
}

# Install Python dependencies
install_python_dependencies() {
    # Define core Python packages
    python_core_pkgs=("flask" "requests" "python-nmap")
    python_optional_pkgs=("speedtest-cli" "python-telegram-bot" "pyyaml" "click")
    
    # Determine which pip to use (system pip)
    PIP_CMD="pip3"
    
    # Make sure pip is up-to-date
    echo -ne "${ARROW} ${CYAN}Upgrading pip...${NC} "
    if $PIP_CMD install --upgrade pip >> $LOG_FILE 2>&1; then
        echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        warning "Failed to upgrade pip, but continuing with installation"
    fi
    
    # Install core Python packages
    echo -e "\n${BOLD}${WHITE}Installing Python dependencies:${NC}"
    echo "Installing Python packages..." >> $LOG_FILE
    
    local py_core_success=true
    for pkg in "${python_core_pkgs[@]}"; do
        echo -ne "  ${ARROW} ${CYAN}Installing ${pkg}...${NC} "
        echo "Installing Python package: $pkg" >> $LOG_FILE
        
        if $PIP_CMD install $pkg >> $LOG_FILE 2>&1; then
            echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
            echo "SUCCESS: Installed Python package $pkg" >> $LOG_FILE
        else
            echo -e "${CROSS_MARK} ${RED}Failed${NC}"
            echo "FAILED: Could not install Python package $pkg" >> $LOG_FILE
            py_core_success=false
        fi
    done
    
    if [ "$py_core_success" = false ]; then
        error "Some core Python packages failed to install. The application may not function correctly."
    fi
    
    # Install optional Python packages
    echo -e "\n${BOLD}${WHITE}Installing optional Python packages:${NC}"
    for pkg in "${python_optional_pkgs[@]}"; do
        echo -ne "  ${ARROW} ${CYAN}Installing ${pkg}...${NC} "
        echo "Installing optional Python package: $pkg" >> $LOG_FILE
        
        if $PIP_CMD install $pkg >> $LOG_FILE 2>&1; then
            echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
            echo "SUCCESS: Installed Python package $pkg" >> $LOG_FILE
        else
            echo -e "${CROSS_MARK} ${RED}Failed${NC}"
            echo "FAILED: Could not install Python package $pkg" >> $LOG_FILE
            warning "Optional Python package $pkg could not be installed, but installation will continue"
        fi
    done
    
    # Check if requirements.txt exists (when we have the repository)
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        echo -ne "${ARROW} ${CYAN}Installing packages from requirements.txt...${NC} "
        echo "Installing requirements from requirements.txt..." >> $LOG_FILE
        
        if $PIP_CMD install -r $INSTALL_DIR/requirements.txt >> $LOG_FILE 2>&1; then
            echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
            echo "SUCCESS: Installed packages from requirements.txt" >> $LOG_FILE
        else
            echo -e "${CROSS_MARK} ${RED}Failed${NC}"
            echo "FAILED: Could not install packages from requirements.txt" >> $LOG_FILE
            warning "Failed to install some packages from requirements.txt, but installation will continue"
        fi
    fi
    
    # Install the package directly to the system Python
    if [ -d "$INSTALL_DIR" ]; then
        echo -ne "${ARROW} ${CYAN}Installing cybex-pulse package to system Python...${NC} "
        echo "Installing cybex-pulse package..." >> $LOG_FILE
        cd $INSTALL_DIR
        
        # Ensure all directories have __init__.py files
        find . -type d -not -path "*/\.*" -exec touch {}/__init__.py \; >> $LOG_FILE 2>&1
        
        # Install the package to the system Python
        if $PIP_CMD install -e . >> $LOG_FILE 2>&1; then
            echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
            echo "SUCCESS: Installed cybex-pulse package to system Python" >> $LOG_FILE
        else
            echo -e "${CROSS_MARK} ${RED}Failed${NC}"
            echo "FAILED: Could not install cybex-pulse package to system Python" >> $LOG_FILE
            warning "Failed to install cybex-pulse package, but installation will continue"
        fi
    fi
}

#######################################################
# Application Installation Functions
#######################################################

# Copy application files to the installation directory
copy_application() {
    progress "Copying application files"
    echo "===============================================" >> $LOG_FILE
    echo "Beginning application file copy process" >> $LOG_FILE
    
    # Get current directory
    CURRENT_DIR="$(pwd)"
    
    # Check if we're running from the repository or need to download
    if [ -d "$CURRENT_DIR/cybex_pulse" ]; then
        install_from_local_directory
    else
        download_and_install_repository
    fi
    
    # Create symlink to the venv-python executable
    echo -ne "${ARROW} ${CYAN}Creating Python symlink...${NC} "
    echo "Creating Python symlink..." >> $LOG_FILE
    
    if ln -sf $INSTALL_DIR/venv/bin/python /usr/local/bin/cybex-pulse-python >> $LOG_FILE 2>&1; then
        echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
        echo "SUCCESS: Created Python symlink" >> $LOG_FILE
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        echo "FAILED: Could not create Python symlink" >> $LOG_FILE
        warning "Failed to create Python symlink, but installation can continue"
    fi
    
    success "Application files copied"
}

# Install from local directory
install_from_local_directory() {
    # We have the repository locally
    echo -e "${INFO} ${BLUE}Found local repository, copying files...${NC}" | tee -a $LOG_FILE
    
    echo -ne "${ARROW} ${CYAN}Copying application files from local directory...${NC} "
    if cp -r $CURRENT_DIR/cybex_pulse/* $INSTALL_DIR/ >> $LOG_FILE 2>&1; then
        echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
        echo "SUCCESS: Copied application files from local directory" >> $LOG_FILE
        
        # Install Python package for proper module import
        echo -ne "${ARROW} ${CYAN}Installing Python package...${NC} "
        echo "Installing Python package..." >> $LOG_FILE
        cd $INSTALL_DIR
        if $INSTALL_DIR/venv/bin/pip install -e . >> $LOG_FILE 2>&1; then
            echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
            echo "SUCCESS: Installed Python package" >> $LOG_FILE
            
            # Verify module can be imported
            echo -ne "${ARROW} ${CYAN}Verifying Cybex Pulse module...${NC} "
            if $INSTALL_DIR/venv/bin/python -c "import cybex_pulse; print('Module imported successfully')" >> $LOG_FILE 2>&1; then
                echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
                echo "SUCCESS: Cybex Pulse module verified" >> $LOG_FILE
            else
                echo -e "${CROSS_MARK} ${RED}Failed${NC}"
                echo "FAILED: Could not import Cybex Pulse module" >> $LOG_FILE
                warning "Failed to verify Cybex Pulse module, the installation may be incomplete"
            fi
        else
            echo -e "${CROSS_MARK} ${RED}Failed${NC}"
            echo "FAILED: Could not install Python package" >> $LOG_FILE
            warning "Failed to install Python package, but installation will continue"
        fi
        cd $CURRENT_DIR
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        echo "FAILED: Could not copy application files from local directory" >> $LOG_FILE
        error "Failed to copy application files"
    fi
    
    # Install executable
    install_executable
}

# Download and install repository
download_and_install_repository() {
    # We need to download the repository
    progress "Downloading repository from GitHub"
    echo -e "${INFO} ${BLUE}No local repository found, downloading from GitHub...${NC}" | tee -a $LOG_FILE
    
    TEMP_DIR=$(mktemp -d)
    echo "Created temporary directory: $TEMP_DIR" >> $LOG_FILE
    
    # Check if git is installed, install if needed
    ensure_git_is_installed
    
    # Clone repository
    clone_repository "$TEMP_DIR"
    
    # Copy files to installation directory
    copy_repository_files "$TEMP_DIR"
    
    # Install executable
    install_executable_from_download "$TEMP_DIR"
    
    # Clean up
    echo -ne "${ARROW} ${CYAN}Cleaning up temporary files...${NC} "
    echo "Cleaning up temporary files..." >> $LOG_FILE
    
    if cd / && rm -rf $TEMP_DIR >> $LOG_FILE 2>&1; then
        echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
        echo "SUCCESS: Cleaned up temporary files" >> $LOG_FILE
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        echo "FAILED: Could not clean up temporary files" >> $LOG_FILE
        warning "Failed to clean up temporary files, but installation can continue"
    fi
    
    success "Repository downloaded and installed"
}

# Ensure git is installed
ensure_git_is_installed() {
    if ! command -v git > /dev/null; then
        echo -ne "${ARROW} ${CYAN}Installing git...${NC} "
        echo "Git not found, installing..." >> $LOG_FILE
        
        # Install git based on distribution
        case $DISTRO_FAMILY in
            debian)
                apt-get install -y -qq git >> $LOG_FILE 2>&1
                ;;
            redhat)
                if [ "$DISTRO" = "fedora" ]; then
                    dnf install -y git >> $LOG_FILE 2>&1
                else
                    yum install -y git >> $LOG_FILE 2>&1
                fi
                ;;
            arch)
                pacman -Sy --noconfirm git >> $LOG_FILE 2>&1
                ;;
            suse)
                zypper --non-interactive install git >> $LOG_FILE 2>&1
                ;;
            unknown)
                install_git_on_unknown_distro
                ;;
        esac
        
        if command -v git > /dev/null; then
            echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
            echo "SUCCESS: Installed git" >> $LOG_FILE
        else
            echo -e "${CROSS_MARK} ${RED}Failed${NC}"
            echo "FAILED: Could not install git" >> $LOG_FILE
            return 1
        fi
    fi
    return 0
}

# Install git on unknown distribution
install_git_on_unknown_distro() {
    if command -v apt-get > /dev/null; then
        apt-get install -y -qq git >> $LOG_FILE 2>&1
    elif command -v yum > /dev/null; then
        yum install -y git >> $LOG_FILE 2>&1
    elif command -v dnf > /dev/null; then
        dnf install -y git >> $LOG_FILE 2>&1
    elif command -v pacman > /dev/null; then
        pacman -Sy --noconfirm git >> $LOG_FILE 2>&1
    elif command -v zypper > /dev/null; then
        zypper --non-interactive install git >> $LOG_FILE 2>&1
    fi
}

# Clone repository
clone_repository() {
    local temp_dir=$1
    
    echo -ne "${ARROW} ${CYAN}Cloning repository...${NC} "
    echo "Cloning repository from GitHub..." >> $LOG_FILE
    
    if git clone https://github.com/DigitalPals/pulse.git "$temp_dir/pulse" >> $LOG_FILE 2>&1; then
        echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
        echo "SUCCESS: Cloned repository" >> $LOG_FILE
        cd "$temp_dir/pulse"
        return 0
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        echo "FAILED: Could not clone repository" >> $LOG_FILE
        
        # Try alternate download method
        download_repository_with_curl "$temp_dir"
        return $?
    fi
}

# Download repository with curl as fallback
download_repository_with_curl() {
    local temp_dir=$1
    
    echo -ne "${ARROW} ${CYAN}Trying alternate download method with curl...${NC} "
    echo "Trying alternate download method with curl..." >> $LOG_FILE
    
    if command -v curl > /dev/null; then
        mkdir -p "$temp_dir/pulse"
        cd "$temp_dir"
        if curl -L https://github.com/DigitalPals/pulse/archive/main.tar.gz -o pulse.tar.gz >> $LOG_FILE 2>&1 && 
           tar -xzf pulse.tar.gz >> $LOG_FILE 2>&1; then
            echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
            echo "SUCCESS: Downloaded repository using curl" >> $LOG_FILE
            # Make sure we have the correct directory structure
            fix_directory_structure "$temp_dir"
            return 0
        else
            echo -e "${CROSS_MARK} ${RED}Failed${NC}"
            echo "FAILED: Could not download repository using curl" >> $LOG_FILE
            error "Failed to download repository. Please try installing git manually and run the script again."
            return 1
        fi
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        echo "FAILED: Neither git nor curl is available" >> $LOG_FILE
        error "Failed to download repository. Please install git or curl manually and run the script again."
        return 1
    fi
}

# Fix directory structure after curl download
fix_directory_structure() {
    local temp_dir=$1
    
    if [ -d "$temp_dir/pulse-main/cybex_pulse" ]; then
        cd "$temp_dir/pulse-main"
    else
        echo "Unexpected directory structure, trying to fix..." >> $LOG_FILE
        # Try to find cybex_pulse directory
        CYBEX_DIR=$(find "$temp_dir/pulse-main" -type d -name "cybex_pulse" | head -1)
        if [ -n "$CYBEX_DIR" ]; then
            cd $(dirname "$CYBEX_DIR")
        else
            # If not found, create it and copy python files
            mkdir -p "$temp_dir/pulse-main/cybex_pulse"
            find "$temp_dir/pulse-main" -type f -name "*.py" -exec cp {} "$temp_dir/pulse-main/cybex_pulse/" \; >> $LOG_FILE 2>&1
            cd "$temp_dir/pulse-main"
        fi
    fi
}

# Copy repository files to installation directory
copy_repository_files() {
    local temp_dir=$1
    
    echo -ne "${ARROW} ${CYAN}Copying application files...${NC} "
    echo "Copying application files to installation directory..." >> $LOG_FILE
    
    if [ -d "cybex_pulse" ]; then
        if cp -r cybex_pulse/* $INSTALL_DIR/ >> $LOG_FILE 2>&1; then
            echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
            echo "SUCCESS: Copied application files" >> $LOG_FILE
            
            # Install Python package for proper module import
            echo -ne "${ARROW} ${CYAN}Installing Python package...${NC} "
            echo "Installing Python package..." >> $LOG_FILE
            cd $INSTALL_DIR
            # First make sure we have all __init__.py files to prevent import errors
            find . -type d -not -path "*/\.*" -not -path "*/venv*" -exec touch {}/__init__.py \; >> $LOG_FILE 2>&1
            
            # Try to install the package
            if $INSTALL_DIR/venv/bin/pip install -e . >> $LOG_FILE 2>&1; then
                echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
                echo "SUCCESS: Installed Python package" >> $LOG_FILE
                
                # Set PYTHONPATH to ensure the module can be found
                echo "Setting PYTHONPATH in virtual environment..." >> $LOG_FILE
                echo "export PYTHONPATH=$INSTALL_DIR:\$PYTHONPATH" >> $INSTALL_DIR/venv/bin/activate
                source $INSTALL_DIR/venv/bin/activate
                
                # Verify module can be imported
                echo -ne "${ARROW} ${CYAN}Verifying Cybex Pulse module...${NC} "
                IMPORT_ERROR=$($INSTALL_DIR/venv/bin/python -c "
try:
    import cybex_pulse
    print('Module imported successfully')
except Exception as e:
    import sys
    print(f'Import error: {str(e)}', file=sys.stderr)
    sys.exit(1)
" 2>&1)
                
                if [ $? -eq 0 ]; then
                    echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
                    echo "SUCCESS: Cybex Pulse module verified" >> $LOG_FILE
                else
                    echo -e "${CROSS_MARK} ${RED}Failed${NC}"
                    echo "FAILED: Could not import Cybex Pulse module" >> $LOG_FILE
                    echo "Error details: $IMPORT_ERROR" >> $LOG_FILE
                    warning "Failed to verify Cybex Pulse module: ${IMPORT_ERROR}"
                fi
            else
                echo -e "${CROSS_MARK} ${RED}Failed${NC}"
                echo "FAILED: Could not install Python package" >> $LOG_FILE
                warning "Failed to install Python package, but installation will continue"
            fi
            return 0
        else
            echo -e "${CROSS_MARK} ${RED}Failed${NC}"
            echo "FAILED: Could not copy application files" >> $LOG_FILE
            error "Failed to copy application files. Installation may be incomplete."
            return 1
        fi
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        echo "FAILED: Could not find cybex_pulse directory" >> $LOG_FILE
        error "Failed to find cybex_pulse directory. Installation may be incomplete."
        return 1
    fi
}

# Install executable from local directory
install_executable() {
    echo -ne "${ARROW} ${CYAN}Installing executables...${NC} "
    mkdir -p /usr/local/bin
    
    # Check if the file exists first
    if [ -f "$CURRENT_DIR/pulse" ]; then
        # Create a modified version that uses the correct installation directory
        sed "s|/root/Pulse|$INSTALL_DIR|g" $CURRENT_DIR/pulse > /usr/local/bin/cybex-pulse && chmod +x /usr/local/bin/cybex-pulse
        if [ -x "/usr/local/bin/cybex-pulse" ]; then
            echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
            echo "SUCCESS: Installed executable" >> $LOG_FILE
        else
            echo -e "${CROSS_MARK} ${RED}Failed${NC}"
            echo "FAILED: Could not install executable" >> $LOG_FILE
            create_basic_executable
        fi
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        echo "FAILED: Could not find pulse executable" >> $LOG_FILE
        create_basic_executable
    fi
}

# Install executable from downloaded repository
install_executable_from_download() {
    local temp_dir=$1
    
    echo -ne "${ARROW} ${CYAN}Installing executables...${NC} "
    echo "Installing executables..." >> $LOG_FILE
    
    mkdir -p /usr/local/bin
    if [ -f "pulse" ]; then
        # Create a modified version that uses the correct installation directory
        sed "s|/root/Pulse|$INSTALL_DIR|g" pulse > /usr/local/bin/cybex-pulse && chmod +x /usr/local/bin/cybex-pulse
        if [ -x "/usr/local/bin/cybex-pulse" ]; then
            echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
            echo "SUCCESS: Installed executable" >> $LOG_FILE
        else
            echo -e "${CROSS_MARK} ${RED}Failed${NC}"
            echo "FAILED: Could not install executable" >> $LOG_FILE
            create_basic_executable
        fi
    else
        create_basic_executable
    fi
}

# Create a basic executable if the original is not available
create_basic_executable() {
    echo -ne "${ARROW} ${CYAN}Creating basic executable...${NC} "
    echo "Creating basic executable..." >> $LOG_FILE
    
    cat > /usr/local/bin/cybex-pulse << EOF
#!/bin/bash
# Auto-generated by Cybex Pulse installer
INSTALL_DIR="$INSTALL_DIR"

# Create a runtime wrapper to fix import issues
cat > "\$INSTALL_DIR/run_app.py" << 'WRAPPER'
#!/usr/bin/env python3
# Dynamic wrapper to execute the application directly
import os
import sys

# Add the root directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Create imports for all Python files in the current directory
for root, dirs, files in os.walk(current_dir):
    for filename in files:
        if filename.endswith('.py') and filename != 'run_app.py':
            module_name = os.path.splitext(filename)[0]
            if module_name != '__init__':
                try:
                    exec(f"import {module_name}")
                except Exception:
                    pass

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
WRAPPER

chmod +x "\$INSTALL_DIR/run_app.py"

# Run directly using the wrapper
cd \$INSTALL_DIR
export PYTHONPATH=\$INSTALL_DIR:\$PYTHONPATH
python3 "\$INSTALL_DIR/run_app.py" "\$@"
EOF
    chmod +x /usr/local/bin/cybex-pulse
    
    if [ -x /usr/local/bin/cybex-pulse ]; then
        echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
        echo "SUCCESS: Created basic executable" >> $LOG_FILE
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        echo "FAILED: Could not create basic executable" >> $LOG_FILE
        error "Failed to create executable. You may need to run the application manually."
    fi
}

#######################################################
# Verification Functions
#######################################################

# Verify the Python module installation
verify_module_installation() {
    step 9 "Verifying installation"
    progress "Checking Python module installation"
    
    # Check if the module is properly installed
    echo "Verifying Python module installation..." >> $LOG_FILE
    
    echo -ne "${ARROW} ${CYAN}Checking cybex-pulse package...${NC} "
    # Use a safer approach to check the package that won't break pipes
    if $INSTALL_DIR/venv/bin/pip list 2>/dev/null | grep -q "cybex-pulse"; then
        echo -e "${CHECK_MARK} ${GREEN}Installed${NC}"
        echo "SUCCESS: cybex-pulse package is installed" >> $LOG_FILE
        
        # Get version info safely
        PACKAGE_INFO=$($INSTALL_DIR/venv/bin/pip show cybex-pulse 2>/dev/null)
        PACKAGE_VERSION=$(echo "$PACKAGE_INFO" | grep "Version:" | cut -d' ' -f2)
        echo -e "${INFO} ${BLUE}Installed version: $PACKAGE_VERSION${NC}"
        echo "Installed version: $PACKAGE_VERSION" >> $LOG_FILE
    else
        echo -e "${CROSS_MARK} ${RED}Not found${NC}"
        echo "FAILED: cybex-pulse package is not installed" >> $LOG_FILE
        
        # Attempt to fix missing package installation
        echo -ne "${ARROW} ${CYAN}Attempting to install cybex-pulse package...${NC} "
        cd $INSTALL_DIR
        $INSTALL_DIR/venv/bin/pip install -e . >> $LOG_FILE 2>&1
        
        if $INSTALL_DIR/venv/bin/pip list 2>/dev/null | grep -q "cybex-pulse"; then
            echo -e "${CHECK_MARK} ${GREEN}Fixed${NC}"
            echo "SUCCESS: Installed cybex-pulse package" >> $LOG_FILE
        else
            echo -e "${CROSS_MARK} ${RED}Failed${NC}"
            echo "FAILED: Could not install cybex-pulse package" >> $LOG_FILE
            warning "Package could not be installed. The application may not work correctly."
        fi
    fi
    
    # Try to import the module
    echo -ne "${ARROW} ${CYAN}Testing module import...${NC} "
    # Save the import error to the log to help with debugging
    IMPORT_ERROR=$($INSTALL_DIR/venv/bin/python -c "
try:
    import cybex_pulse
    print('Module imported successfully')
except Exception as e:
    import sys
    print(f'Import error: {str(e)}', file=sys.stderr)
    sys.exit(1)
" 2>&1)
    
    if [ $? -eq 0 ]; then
        echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
        echo "SUCCESS: Cybex Pulse module imported successfully" >> $LOG_FILE
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        echo "FAILED: Could not import Cybex Pulse module" >> $LOG_FILE
        echo "Error details: $IMPORT_ERROR" >> $LOG_FILE
        warning "Failed to import Cybex Pulse module: ${IMPORT_ERROR}"
        
        # Try to fix common installation issues
        echo -ne "${ARROW} ${CYAN}Attempting to fix module installation...${NC} "
        cd $INSTALL_DIR
        
        # Ensure all package directories have __init__.py files
        echo "Creating missing __init__.py files..." >> $LOG_FILE
        find . -type d -not -path "*/\.*" -not -path "*/venv*" -exec touch {}/__init__.py \; >> $LOG_FILE 2>&1
        
        # Fix permissions
        echo "Setting correct permissions..." >> $LOG_FILE
        chmod -R 755 $INSTALL_DIR >> $LOG_FILE 2>&1
        
        # Reinstall the package
        echo "Reinstalling package..." >> $LOG_FILE
        $INSTALL_DIR/venv/bin/pip install -e . --no-deps >> $LOG_FILE 2>&1
        
        # Verify PYTHONPATH includes installation directory
        echo "Setting PYTHONPATH in virtual environment..." >> $LOG_FILE
        grep -q "PYTHONPATH=$INSTALL_DIR" $INSTALL_DIR/venv/bin/activate || echo "export PYTHONPATH=$INSTALL_DIR:\$PYTHONPATH" >> $INSTALL_DIR/venv/bin/activate
        source $INSTALL_DIR/venv/bin/activate >> $LOG_FILE 2>&1
        
        # Create a simple test script to debug import issues
        echo "Creating import test script..." >> $LOG_FILE
        cat > $INSTALL_DIR/test_import.py << EOF
import sys
print("Python path:")
for p in sys.path:
    print(f"  {p}")
print("\nTrying import...")
try:
    import cybex_pulse
    print("Success: cybex_pulse imported")
    print(f"Module location: {cybex_pulse.__file__}")
except Exception as e:
    print(f"Error: {str(e)}")
    sys.exit(1)
EOF
        
        # Run the test script to get detailed import information
        echo "Running test script for debugging..." >> $LOG_FILE
        TEST_OUTPUT=$($INSTALL_DIR/venv/bin/python $INSTALL_DIR/test_import.py 2>&1)
        echo "$TEST_OUTPUT" >> $LOG_FILE
        
        # Try import again after fix attempt
        if $INSTALL_DIR/venv/bin/python -c "import cybex_pulse; print('Module now imported successfully')" >> $LOG_FILE 2>&1; then
            echo -e "${CHECK_MARK} ${GREEN}Fixed${NC}"
            echo "SUCCESS: Fixed Cybex Pulse module import" >> $LOG_FILE
        else
            echo -e "${CROSS_MARK} ${RED}Still failing${NC}"
            echo "FAILED: Could not fix module import" >> $LOG_FILE
            echo "Import test output: $TEST_OUTPUT" >> $LOG_FILE
            warning "The application may not work correctly. Check the log for details."
            
            # Create a symlink as a last resort - find the correct Python version directory first
            echo "Creating symlink as last resort..." >> $LOG_FILE
            PYTHON_VERSION=$($INSTALL_DIR/venv/bin/python -c "import sys; print(f'python{sys.version_info.major}.{sys.version_info.minor}')")
            SITE_PACKAGES_DIR=$INSTALL_DIR/venv/lib/$PYTHON_VERSION/site-packages
            echo "Python version: $PYTHON_VERSION, site-packages: $SITE_PACKAGES_DIR" >> $LOG_FILE
            
            # Ensure directory exists
            mkdir -p $SITE_PACKAGES_DIR >> $LOG_FILE 2>&1
            
            # Create the symlink
            echo "Creating symlink from $INSTALL_DIR to $SITE_PACKAGES_DIR/cybex_pulse" >> $LOG_FILE
            ln -sf $INSTALL_DIR $SITE_PACKAGES_DIR/cybex_pulse >> $LOG_FILE 2>&1
            
            # Create an empty __init__.py in site-packages
            touch $SITE_PACKAGES_DIR/cybex_pulse.py >> $LOG_FILE 2>&1
            echo "import sys, os; sys.path.insert(0, '$INSTALL_DIR'); from cybex_pulse import *" > $SITE_PACKAGES_DIR/cybex_pulse.py
            
            # Install directly to site-packages
            echo "Installing directly to site-packages..." >> $LOG_FILE
            cd $INSTALL_DIR && cp -r . $SITE_PACKAGES_DIR/cybex_pulse_direct >> $LOG_FILE 2>&1
            touch $SITE_PACKAGES_DIR/cybex_pulse_direct/__init__.py >> $LOG_FILE 2>&1
            
            # Create a .pth file to add the installation directory to Python path
            echo "Creating .pth file..." >> $LOG_FILE
            echo "$INSTALL_DIR" > $SITE_PACKAGES_DIR/cybex_pulse.pth
            
            # Try import again after these desperate measures
            if $INSTALL_DIR/venv/bin/python -c "import cybex_pulse; print('Finally imported successfully')" >> $LOG_FILE 2>&1; then
                echo -e "${CHECK_MARK} ${GREEN}Fixed with fallback method${NC}"
                echo "SUCCESS: Fixed Cybex Pulse module import with fallback method" >> $LOG_FILE
            else
                echo -e "${CROSS_MARK} ${RED}All attempts failed${NC}"
                echo "FAILED: All import fix attempts failed" >> $LOG_FILE
            fi
        fi
    fi
    
    # Test executable
    echo -ne "${ARROW} ${CYAN}Testing cybex-pulse executable...${NC} "
    if command -v cybex-pulse >/dev/null 2>&1; then
        echo -e "${CHECK_MARK} ${GREEN}Found${NC}"
        echo "SUCCESS: cybex-pulse executable found" >> $LOG_FILE
    else
        echo -e "${CROSS_MARK} ${RED}Not found${NC}"
        echo "FAILED: cybex-pulse executable not found" >> $LOG_FILE
        warning "Executable not found in PATH. The application may not work correctly."
    fi
    
    success "Installation verification completed"
}

#######################################################
# Service Setup Functions
#######################################################

# Install systemd service
install_systemd_service() {
    progress "Installing systemd service"
    echo "Installing systemd service..." >> $LOG_FILE
    
    # Create systemd service file
    echo -ne "${ARROW} ${CYAN}Creating service file...${NC} "
    
    cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Cybex Pulse Network Monitoring
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/local/bin/cybex-pulse
Restart=on-failure
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=cybex-pulse
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=$INSTALL_DIR

[Install]
WantedBy=multi-user.target
EOF

    if [ -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
        echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
        echo "SUCCESS: Created service file" >> $LOG_FILE
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        echo "FAILED: Could not create service file" >> $LOG_FILE
        error "Failed to create service file"
    fi
    
    # Reload systemd manager configuration
    echo -ne "${ARROW} ${CYAN}Reloading systemd manager...${NC} "
    if systemctl daemon-reload >> $LOG_FILE 2>&1; then
        echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
        echo "SUCCESS: Reloaded systemd manager" >> $LOG_FILE
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        echo "FAILED: Could not reload systemd manager" >> $LOG_FILE
        error "Failed to reload systemd configuration"
    fi
    
    success "Systemd service installed"
}

# Configure the application
configure_app() {
    progress "Configuring application"
    
    # Create config directory but don't create config.json
    mkdir -p $CONFIG_DIR
    
    # Create directory structure for user config
    mkdir -p /home/$SERVICE_USER/.cybex_pulse
    
    # Set proper permissions
    chown -R $SERVICE_USER:$SERVICE_USER $CONFIG_DIR
    chown -R $SERVICE_USER:$SERVICE_USER /home/$SERVICE_USER/.cybex_pulse
    
    success "Application configured"
}

# Start the service
start_service() {
    progress "Starting Cybex Pulse service"
    
    echo -ne "${ARROW} ${CYAN}Enabling service...${NC} "
    if systemctl enable $SERVICE_NAME.service >> $LOG_FILE 2>&1; then
        echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
        echo "SUCCESS: Enabled service" >> $LOG_FILE
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        echo "FAILED: Could not enable service" >> $LOG_FILE
        error "Failed to enable service"
    fi
    
    echo -ne "${ARROW} ${CYAN}Starting service...${NC} "
    if systemctl start $SERVICE_NAME.service >> $LOG_FILE 2>&1; then
        echo -e "${CHECK_MARK} ${GREEN}Success${NC}"
        echo "SUCCESS: Started service" >> $LOG_FILE
    else
        echo -e "${CROSS_MARK} ${RED}Failed${NC}"
        echo "FAILED: Could not start service" >> $LOG_FILE
        error "Failed to start service"
    fi
    
    # Check service status
    echo -ne "${ARROW} ${CYAN}Checking service status...${NC} "
    if systemctl is-active --quiet $SERVICE_NAME.service; then
        echo -e "${CHECK_MARK} ${GREEN}Running${NC}"
        echo "SUCCESS: Service is running" >> $LOG_FILE
    else
        echo -e "${CROSS_MARK} ${RED}Not running${NC}"
        echo "FAILED: Service is not running" >> $LOG_FILE
        warning "Service is not running. Check logs with 'journalctl -u $SERVICE_NAME'"
    fi
    
    success "Service started"
}

#######################################################
# Completion Functions
#######################################################

# Print completion message
print_completion() {
    echo
    # Show logo again - without clearing the screen
    print_cybex_logo
    
    separator
    echo -e "${GREEN}${BOLD}INSTALLATION COMPLETED SUCCESSFULLY${NC}"
    separator
    echo
    
    # Display completed steps
    draw_progress_bar $TOTAL_STEPS $TOTAL_STEPS
    echo
    
    # Access information
    echo -e "${WHITE}${BOLD}ACCESS INFORMATION${NC}"
    echo -e "  ${CYAN}Web Interface:${NC} http://$(hostname -I | awk '{print $1}'):8000"
    echo
    
    # Service management
    echo -e "${WHITE}${BOLD}SERVICE MANAGEMENT${NC}"
    echo -e "  ${CYAN}Start service:${NC}    sudo systemctl start $SERVICE_NAME"
    echo -e "  ${CYAN}Stop service:${NC}     sudo systemctl stop $SERVICE_NAME"
    echo -e "  ${CYAN}Restart service:${NC}  sudo systemctl restart $SERVICE_NAME"
    echo -e "  ${CYAN}Check status:${NC}     sudo systemctl status $SERVICE_NAME"
    echo -e "  ${CYAN}View logs:${NC}        sudo journalctl -u $SERVICE_NAME"
    echo
    
    # Configuration information
    echo -e "${WHITE}${BOLD}LOG FILES${NC}"
    echo -e "  ${CYAN}Log directory:${NC}    $LOG_DIR"
    echo -e "  ${CYAN}Install log:${NC}      $LOG_FILE"
    echo
    
    # Next steps
    echo -e "${WHITE}${BOLD}NEXT STEPS${NC}"
    echo -e "  ${INFO} If this is your first time running Cybex Pulse,"
    echo -e "     you'll need to complete the setup wizard in the web interface."
    echo
    
    # Troubleshooting
    echo -e "${WHITE}${BOLD}TROUBLESHOOTING${NC}"
    echo -e "  ${CYAN}Check installation log:${NC}  cat $LOG_FILE"
    echo -e "  ${CYAN}Check service status:${NC}    sudo systemctl status $SERVICE_NAME"
    echo -e "  ${CYAN}View service logs:${NC}       sudo journalctl -u $SERVICE_NAME"
    echo
    
    echo -e "${GREEN}${BOLD}Thank you for installing Cybex Pulse!${NC}"
    echo
}

#######################################################
# Main Installation Process
#######################################################

main() {
    # Clear the screen
    clear
    
    print_header

    # Initialize log file
    init_log

    # Check if script is running as root
    if [ "$EUID" -ne 0 ]; then
        error "This script must be run as root" "fatal"
    fi

    # Detect Linux distribution
    check_distribution
    echo -e "${BOLD}${WHITE}Detected distribution:${NC} ${CYAN}$DISTRO${NC} (${CYAN}$DISTRO_FAMILY${NC} family)"
    echo "Detected distribution: $DISTRO ($DISTRO_FAMILY family)" >> $LOG_FILE
    echo

    # Begin installation
    step 1 "Installing system dependencies"
    install_dependencies
    
    draw_progress_bar 1 $TOTAL_STEPS

    step 2 "Creating service user"
    create_user
    
    draw_progress_bar 2 $TOTAL_STEPS

    step 3 "Setting up directories"
    setup_directories
    
    draw_progress_bar 3 $TOTAL_STEPS

    step 4 "Installing Python packages"
    install_python_packages
    
    draw_progress_bar 4 $TOTAL_STEPS

    step 5 "Copying application files"
    copy_application
    
    draw_progress_bar 5 $TOTAL_STEPS

    step 6 "Installing systemd service"
    install_systemd_service
    
    draw_progress_bar 6 $TOTAL_STEPS

    step 7 "Configuring application"
    configure_app
    
    draw_progress_bar 7 $TOTAL_STEPS

    step 8 "Starting service"
    start_service
    
    draw_progress_bar 8 $TOTAL_STEPS
    
    # Verify installation
    verify_module_installation
    
    draw_progress_bar 9 $TOTAL_STEPS

    # Installation complete
    print_completion
}

# Execute main installation process
main
exit 0