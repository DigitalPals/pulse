#!/bin/bash

#######################################################
# Cybex Pulse Installation Script
# This script installs Cybex Pulse on various Linux distributions
#######################################################

# Don't exit on errors, we'll handle them manually
set +e

# Log file for installation details
LOG_FILE="/tmp/cybex-pulse-install.log"

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

# ANSI color codes based on web interface
# Theme colors from Cybex Pulse web interface
RED='\033[0;31m'            # --accent: #d93a3a;
DARK_RED='\033[38;2;185;46;46m'  # --accent-dark: #b92e2e;
GREEN='\033[38;2;76;175;80m'     # --success: #4CAF50;
YELLOW='\033[38;2;255;193;7m'    # --warning: #FFC107;
BLUE='\033[38;2;58;133;217m'     # --highlight-blue: #3a85d9;
ORANGE='\033[38;2;255;152;0m'    # --orange: #FF9800;
WHITE='\033[0;37m'          # --text: #ffffff;
GRAY='\033[38;2;160;160;160m'    # --text-muted: #a0a0a0;
DARK_BG='\033[48;2;26;26;26m'    # --main-bg: #1a1a1a;
DARKER_BG='\033[48;2;14;14;14m'  # --sidebar-bg: #0e0e0e;
NC='\033[0m'                # No Color
BOLD='\033[1m'
UNDERLINE='\033[4m'
BLINK='\033[5m'

# Special characters
CHECK_MARK="✓"
X_MARK="✗"
ARROW="→"
PULSE_SYMBOL="▮▯"
GEAR="⚙"
WAITING_SYMBOL="⟳"

# Configuration
INSTALL_DIR="/opt/cybex-pulse"
SERVICE_USER="cybexpulse"
CONFIG_DIR="/etc/cybex-pulse"
LOG_DIR="/var/log/cybex-pulse"
SERVICE_NAME="cybex-pulse"

# Functions
print_cybex_logo() {
    echo -e "${RED}"
    echo -e "   ▄████▄  ▓██   ██▓ ▄▄▄▄   ▓█████ ▒██   ██▒    ${WHITE} ██▓███   █    ██  ██▓      ██████ ▓█████ ${NC}"
    echo -e "  ▒██▀ ▀█   ▒██  ██▒▓█████▄ ▓█   ▀ ▒▒ █ █ ▒░    ${WHITE}▓██░  ██▒ ██  ▓██▒▓██▒    ▒██    ▒ ▓█   ▀ ${NC}"
    echo -e "  ▒▓█    ▄   ▒██ ██░▒██▒ ▄██▒███   ░░  █   ░    ${WHITE}▓██░ ██▓▒▓██  ▒██░▒██░    ░ ▓██▄   ▒███   ${NC}"
    echo -e "  ▒▓▓▄ ▄██▒  ░ ▐██▓░▒██░█▀  ▒▓█  ▄  ░ █ █ ▒     ${WHITE}▒██▄█▓▒ ▒▓▓█  ░██░▒██░      ▒   ██▒▒▓█  ▄ ${NC}"
    echo -e "  ▒ ▓███▀ ░  ░ ██▒▓░░▓█  ▀█▓░▒████▒▒██▒ ▒██▒    ${WHITE}▒██▒ ░  ░▒▒█████▓ ░██████▒▒██████▒▒░▒████▒${NC}"
    echo -e "  ░ ░▒ ▒  ░   ██▒▒▒ ░▒▓███▀▒░░ ▒░ ░▒▒ ░ ░▓ ░    ${WHITE}▒▓▒░ ░  ░░▒▓▒ ▒ ▒ ░ ▒░▓  ░▒ ▒▓▒ ▒ ░░░ ▒░ ░${NC}"
    echo -e "    ░  ▒    ▓██ ░▒░ ▒░▒   ░  ░ ░  ░░░   ░▒ ░    ${WHITE}░▒ ░     ░░▒░ ░ ░ ░ ░ ▒  ░░ ░▒  ░ ░ ░ ░  ░${NC}"
    echo -e "  ░         ▒ ▒ ░░   ░    ░    ░    ░    ░      ${WHITE}░░        ░░░ ░ ░   ░ ░   ░  ░  ░     ░   ${NC}"
    echo -e "  ░ ░       ░ ░      ░         ░  ░ ░    ░      ${WHITE}            ░         ░  ░      ░     ░  ░${NC}"
    echo -e "  ░         ░ ░           ░                      ${WHITE}                                          ${NC}"
    echo
}

print_header() {
    clear
    print_cybex_logo
    
    echo -e "${DARK_BG}${RED}╔════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${DARK_BG}${RED}║                                                                                ║${NC}"
    echo -e "${DARK_BG}${RED}║  ${BOLD}${WHITE}Network Monitoring Installation                                            ${RED}║${NC}"
    echo -e "${DARK_BG}${RED}║  ${GRAY}Version 1.0.0                                                              ${RED}║${NC}"
    echo -e "${DARK_BG}${RED}╚════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo

    # Animation
    echo -ne "${GRAY}Initializing installation"
    for i in {1..5}; do
        echo -ne "${PULSE_SYMBOL}"
        sleep 0.1
    done
    echo -e "${NC}\n"
}

show_spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏' # Braille pattern spinner (smoother)
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " ${BLUE}%c${NC}  " "${spinstr:0:1}"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

animate_progress() {
    local text=$1
    local duration=$2
    local frames=("${PULSE_SYMBOL}" " ${PULSE_SYMBOL}" "  ${PULSE_SYMBOL}" "   ${PULSE_SYMBOL}" "    ${PULSE_SYMBOL}" "     ${PULSE_SYMBOL}")
    local frames_count=${#frames[@]}
    local start_time=$(date +%s)
    local end_time=$((start_time + duration))
    
    echo -ne "${BOLD}${text}${NC}"
    
    while [ $(date +%s) -lt $end_time ]; do
        for (( i=0; i<frames_count; i++ )); do
            echo -ne "\r${BOLD}${text}${NC} ${BLUE}${frames[$i]}${NC}"
            sleep 0.1
            if [ $(date +%s) -ge $end_time ]; then
                break
            fi
        done
    done
    echo
}

progress() {
    local text=$1
    echo -ne "${BOLD}${BLUE}${ARROW} ${text}...${NC} "
}

success() {
    echo -e "\r${BOLD}${BLUE}${ARROW} ${1}...${NC} ${GREEN}${CHECK_MARK}${NC}"
}

error() {
    echo -e "\r${BOLD}${BLUE}${ARROW} ${1}...${NC} ${RED}${X_MARK}${NC}"
    echo "ERROR: $1" >> $LOG_FILE
    echo
    if [ "$2" = "fatal" ]; then
        echo -e "${RED}${BOLD}Installation failed. Please check the error above.${NC}"
        exit 1
    else
        echo -e "${YELLOW}Continuing with installation despite error...${NC}"
        # Don't exit, try to continue
    fi
}

warning() {
    echo -e "${ORANGE}${BOLD}⚠️  $1${NC}"
    echo "WARNING: $1" >> $LOG_FILE
}

show_task_result() {
    local result=$1
    if [ "$result" = "true" ]; then
        echo -e "${GREEN}${CHECK_MARK}${NC}"
    else
        echo -e "${RED}${X_MARK}${NC}"
    fi
}

install_package() {
    local package=$1
    local package_manager=$2
    
    echo -ne "  ${WHITE}Installing ${BOLD}${package}${NC}${WHITE}...${NC} "
    echo "Trying to install: $package with $package_manager" >> $LOG_FILE
    
    # Start a background spinner animation
    (
        i=1
        sp='⣾⣽⣻⢿⡿⣟⣯⣷'
        while true; do
            echo -ne "\b${BLUE}${sp:i++%8:1}${NC}"
            sleep 0.1
        done
    ) &
    
    SPINNER_PID=$!
    
    # Make sure the spinner dies if the script exits
    trap "kill $SPINNER_PID 2>/dev/null" EXIT
    
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
    
    # Kill the spinner
    kill $SPINNER_PID 2>/dev/null
    wait $SPINNER_PID 2>/dev/null
    trap - EXIT
    
    if [ $result -eq 0 ]; then
        echo -e "\b${GREEN}${CHECK_MARK}${NC}"
        echo "SUCCESS: Installed $package" >> $LOG_FILE
        return 0
    else
        echo -e "\b${RED}${X_MARK}${NC}"
        echo "FAILED: Could not install $package" >> $LOG_FILE
        return 1
    fi
}

step() {
    local step_num=$1
    local description=$2
    local step_percentage=$((step_num * 100 / TOTAL_STEPS))
    local progress_bar_width=50
    
    # Calculate how many filled blocks
    local filled_width=$((progress_bar_width * step_num / TOTAL_STEPS))
    local empty_width=$((progress_bar_width - filled_width))
    
    # Create the progress bar
    local progress_bar=""
    for ((i=0; i<filled_width; i++)); do
        progress_bar="${progress_bar}█"
    done
    
    for ((i=0; i<empty_width; i++)); do
        progress_bar="${progress_bar}░"
    done
    
    # Display header with animation
    echo -ne "\n${RED}${GEAR} "
    for (( i=0; i<${#description}; i++ )); do
        echo -ne "${RED}${BOLD}${description:$i:1}${NC}"
        sleep 0.01
    done
    echo
    
    # Display progress bar
    echo -e "${DARK_BG}  ${WHITE}[${RED}${progress_bar}${WHITE}] ${step_percentage}%${NC}"
    echo -e "${GRAY}  Step ${step_num} of ${TOTAL_STEPS}${NC}\n"
    
    # Short pause for effect
    sleep 0.3
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
    echo "===============================================" >> $LOG_FILE
    echo "Beginning dependency installation" >> $LOG_FILE
    
    local pkg_manager=""
    local core_pkgs=()
    local optional_pkgs=()
    
    # Determine package manager and packages based on distribution
    case $DISTRO_FAMILY in
        debian)
            pkg_manager="apt"
            echo "Running apt-get update..." | tee -a $LOG_FILE
            apt-get update -qq >> $LOG_FILE 2>&1
            
            # Core packages (required)
            core_pkgs=("python3" "python3-pip" "python3-venv" "curl" "git")
            
            # Optional packages (nice to have)
            # Separate Ubuntu-specific packages that might not exist in all Debian-based distros
            if [ "$DISTRO" = "ubuntu" ]; then
                optional_pkgs=("nmap" "net-tools" "iproute2" "avahi-utils" "snmp" "arp-scan")
                # In Ubuntu, the package is called snmp, not net-snmp-tools
            else
                optional_pkgs=("nmap" "net-tools" "iproute2" "avahi-utils" "snmp" "arp-scan")
            fi
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
                    echo "Installing EPEL repository..." | tee -a $LOG_FILE
                    yum install -y epel-release >> $LOG_FILE 2>&1
                fi
                core_pkgs=("python3" "python3-pip" "curl" "git")
                optional_pkgs=("nmap" "net-tools" "iproute" "avahi-tools" "net-snmp-utils" "arp-scan")
            fi
            ;;
        arch)
            pkg_manager="pacman"
            echo "Updating pacman..." | tee -a $LOG_FILE
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
            warning "Attempting to detect package manager for unknown distribution..."
            # Try different package managers
            if command -v apt-get > /dev/null; then
                pkg_manager="apt"
                echo "Using apt-get package manager..." | tee -a $LOG_FILE
                apt-get update -qq >> $LOG_FILE 2>&1
                core_pkgs=("python3" "python3-pip" "python3-venv" "curl" "git")
                optional_pkgs=("nmap" "net-tools" "iproute2" "avahi-utils" "snmp" "arp-scan")
            elif command -v yum > /dev/null; then
                pkg_manager="yum"
                echo "Using yum package manager..." | tee -a $LOG_FILE
                core_pkgs=("python3" "python3-pip" "curl" "git")
                optional_pkgs=("nmap" "net-tools" "iproute" "avahi-tools" "net-snmp-utils" "arp-scan")
            elif command -v dnf > /dev/null; then
                pkg_manager="dnf"
                echo "Using dnf package manager..." | tee -a $LOG_FILE
                core_pkgs=("python3" "python3-pip" "curl" "git")
                optional_pkgs=("nmap" "net-tools" "iproute" "avahi-tools" "net-snmp-utils" "arp-scan")
            elif command -v pacman > /dev/null; then
                pkg_manager="pacman"
                echo "Using pacman package manager..." | tee -a $LOG_FILE
                pacman -Sy --noconfirm >> $LOG_FILE 2>&1
                core_pkgs=("python" "python-pip" "curl" "git")
                optional_pkgs=("nmap" "net-tools" "iproute2" "avahi" "net-snmp" "arp-scan")
            elif command -v zypper > /dev/null; then
                pkg_manager="zypper"
                echo "Using zypper package manager..." | tee -a $LOG_FILE
                core_pkgs=("python3" "python3-pip" "curl" "git")
                optional_pkgs=("nmap" "net-tools" "iproute2" "avahi" "net-snmp" "arp-scan")
            else
                error "No supported package manager found" "fatal"
            fi
            ;;
    esac
    
    # Install core packages (required packages)
    echo -e "\n${BOLD}Installing core packages:${NC}"
    local core_success=true
    for pkg in "${core_pkgs[@]}"; do
        if ! install_package "$pkg" "$pkg_manager"; then
            core_success=false
        fi
    done
    
    if [ "$core_success" = false ]; then
        error "Some core packages failed to install. The application may not function correctly."
    else
        success "All core packages installed successfully"
    fi
    
    # Install optional packages
    echo -e "\n${BOLD}Installing optional packages (some may not be available):${NC}"
    echo "Beginning optional package installation..." >> $LOG_FILE
    
    for pkg in "${optional_pkgs[@]}"; do
        install_package "$pkg" "$pkg_manager" || warning "Optional package $pkg could not be installed, but installation will continue"
    done
    
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
    echo "===============================================" >> $LOG_FILE
    echo "Setting up Python environment..." >> $LOG_FILE
    
    # Create and activate Python virtual environment
    echo -ne "${CYAN}Creating Python virtual environment...${NC} "
    echo "Creating Python virtual environment..." >> $LOG_FILE
    
    if python3 -m venv $INSTALL_DIR/venv >> $LOG_FILE 2>&1; then
        echo -e "${GREEN}Success${NC}"
    else
        echo -e "${RED}Failed${NC}"
        error "Failed to create virtual environment (see $LOG_FILE for details)"
        
        # Try alternate approach if venv module fails
        echo -ne "${CYAN}Trying alternate approach with virtualenv...${NC} "
        echo "Trying alternate approach with virtualenv..." >> $LOG_FILE
        
        # First try to install virtualenv if it's not already available
        if ! command -v virtualenv > /dev/null; then
            pip3 install virtualenv >> $LOG_FILE 2>&1
        fi
        
        if virtualenv $INSTALL_DIR/venv >> $LOG_FILE 2>&1; then
            echo -e "${GREEN}Success${NC}"
        else
            echo -e "${RED}Failed${NC}"
            error "Failed to create Python virtual environment. Continuing without isolation."
            # Create directory anyway, we'll try to use system Python
            mkdir -p $INSTALL_DIR/venv/bin
            ln -sf $(which python3) $INSTALL_DIR/venv/bin/python
            ln -sf $(which pip3) $INSTALL_DIR/venv/bin/pip
        fi
    fi
    
    # Use the full path to pip to ensure we're using the venv
    echo -ne "${CYAN}Upgrading pip...${NC} "
    echo "Upgrading pip..." >> $LOG_FILE
    
    if $INSTALL_DIR/venv/bin/pip install --upgrade pip >> $LOG_FILE 2>&1; then
        echo -e "${GREEN}Success${NC}"
    else
        echo -e "${RED}Failed${NC}"
        warning "Failed to upgrade pip, but continuing with installation"
    fi
    
    success "Python virtual environment created"
    
    # Install Python packages one by one so we can continue if some fail
    echo -e "\n${BOLD}Installing Python dependencies:${NC}"
    echo "Installing Python packages..." >> $LOG_FILE
    
    # Define core Python packages
    python_core_pkgs=("flask" "requests" "python-nmap")
    python_optional_pkgs=("speedtest-cli" "python-telegram-bot" "pyyaml" "click")
    
    # Install core Python packages
    local py_core_success=true
    for pkg in "${python_core_pkgs[@]}"; do
        echo -ne "  ${CYAN}Installing ${pkg}...${NC} "
        echo "Installing Python package: $pkg" >> $LOG_FILE
        
        if $INSTALL_DIR/venv/bin/pip install $pkg >> $LOG_FILE 2>&1; then
            echo -e "${GREEN}Success${NC}"
            echo "SUCCESS: Installed Python package $pkg" >> $LOG_FILE
        else
            echo -e "${RED}Failed${NC}"
            echo "FAILED: Could not install Python package $pkg" >> $LOG_FILE
            py_core_success=false
        fi
    done
    
    if [ "$py_core_success" = false ]; then
        error "Some core Python packages failed to install. The application may not function correctly."
    else
        success "All core Python packages installed successfully"
    fi
    
    # Install optional Python packages
    echo -e "\n${BOLD}Installing optional Python packages:${NC}"
    for pkg in "${python_optional_pkgs[@]}"; do
        echo -ne "  ${CYAN}Installing ${pkg}...${NC} "
        echo "Installing optional Python package: $pkg" >> $LOG_FILE
        
        if $INSTALL_DIR/venv/bin/pip install $pkg >> $LOG_FILE 2>&1; then
            echo -e "${GREEN}Success${NC}"
            echo "SUCCESS: Installed Python package $pkg" >> $LOG_FILE
        else
            echo -e "${RED}Failed${NC}"
            echo "FAILED: Could not install Python package $pkg" >> $LOG_FILE
            warning "Optional Python package $pkg could not be installed, but installation will continue"
        fi
    done
    
    # Check if requirements.txt exists (when we have the repository)
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        echo -ne "${CYAN}Installing packages from requirements.txt...${NC} "
        echo "Installing requirements from requirements.txt..." >> $LOG_FILE
        
        if $INSTALL_DIR/venv/bin/pip install -r $INSTALL_DIR/requirements.txt >> $LOG_FILE 2>&1; then
            echo -e "${GREEN}Success${NC}"
            echo "SUCCESS: Installed packages from requirements.txt" >> $LOG_FILE
        else
            echo -e "${RED}Failed${NC}"
            echo "FAILED: Could not install packages from requirements.txt" >> $LOG_FILE
            warning "Failed to install some packages from requirements.txt, but installation will continue"
        fi
    fi
    
    success "Python dependencies installed"
}

copy_application() {
    progress "Copying application files"
    echo "===============================================" >> $LOG_FILE
    echo "Beginning application file copy process" >> $LOG_FILE
    
    # Get current directory
    CURRENT_DIR="$(pwd)"
    
    # Check if we're running from the repository or via curl pipe
    if [ -d "$CURRENT_DIR/cybex_pulse" ]; then
        # We have the repository locally
        echo "Found local repository, copying files..." | tee -a $LOG_FILE
        
        echo -ne "${CYAN}Copying application files from local directory...${NC} "
        if cp -r $CURRENT_DIR/cybex_pulse/* $INSTALL_DIR/ >> $LOG_FILE 2>&1; then
            echo -e "${GREEN}Success${NC}"
            echo "SUCCESS: Copied application files from local directory" >> $LOG_FILE
        else
            echo -e "${RED}Failed${NC}"
            echo "FAILED: Could not copy application files from local directory" >> $LOG_FILE
            error "Failed to copy application files"
        fi
        
        # Copy pulse executable script to bin
        echo -ne "${CYAN}Installing executables...${NC} "
        mkdir -p /usr/local/bin
        if cp $CURRENT_DIR/pulse /usr/local/bin/cybex-pulse >> $LOG_FILE 2>&1 && chmod +x /usr/local/bin/cybex-pulse >> $LOG_FILE 2>&1; then
            echo -e "${GREEN}Success${NC}"
            echo "SUCCESS: Installed executable" >> $LOG_FILE
        else
            echo -e "${RED}Failed${NC}"
            echo "FAILED: Could not install executable" >> $LOG_FILE
            error "Failed to install executable"
        fi
    else
        # We need to download the repository
        progress "Downloading repository from GitHub"
        echo "No local repository found, downloading from GitHub..." | tee -a $LOG_FILE
        
        TEMP_DIR=$(mktemp -d)
        echo "Created temporary directory: $TEMP_DIR" >> $LOG_FILE
        
        # Check if git is installed
        if ! command -v git > /dev/null; then
            echo -ne "${CYAN}Installing git...${NC} "
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
                    ;;
            esac
            
            if command -v git > /dev/null; then
                echo -e "${GREEN}Success${NC}"
                echo "SUCCESS: Installed git" >> $LOG_FILE
            else
                echo -e "${RED}Failed${NC}"
                echo "FAILED: Could not install git" >> $LOG_FILE
                
                # Try alternate download method if git fails
                echo -ne "${CYAN}Trying alternate download method with curl...${NC} "
                echo "Trying alternate download method with curl..." >> $LOG_FILE
                
                if command -v curl > /dev/null; then
                    mkdir -p $TEMP_DIR/pulse
                    cd $TEMP_DIR
                    if curl -L https://github.com/DigitalPals/pulse/archive/main.tar.gz -o pulse.tar.gz >> $LOG_FILE 2>&1 && 
                       tar -xzf pulse.tar.gz >> $LOG_FILE 2>&1; then
                        echo -e "${GREEN}Success${NC}"
                        echo "SUCCESS: Downloaded repository using curl" >> $LOG_FILE
                        mv pulse-main/* .
                    else
                        echo -e "${RED}Failed${NC}"
                        echo "FAILED: Could not download repository using curl" >> $LOG_FILE
                        error "Failed to download repository. Please try installing git manually and run the script again."
                    fi
                else
                    echo -e "${RED}Failed${NC}"
                    echo "FAILED: Neither git nor curl is available" >> $LOG_FILE
                    error "Failed to download repository. Please install git or curl manually and run the script again."
                fi
            fi
        fi
        
        # Clone repository
        echo -ne "${CYAN}Cloning repository...${NC} "
        echo "Cloning repository from GitHub..." >> $LOG_FILE
        
        if git clone https://github.com/DigitalPals/pulse.git $TEMP_DIR/pulse >> $LOG_FILE 2>&1; then
            echo -e "${GREEN}Success${NC}"
            echo "SUCCESS: Cloned repository" >> $LOG_FILE
            cd $TEMP_DIR/pulse
        else
            echo -e "${RED}Failed${NC}"
            echo "FAILED: Could not clone repository" >> $LOG_FILE
            
            # Try alternate download method if git clone fails
            echo -ne "${CYAN}Trying alternate download method...${NC} "
            echo "Trying alternate download method..." >> $LOG_FILE
            
            cd $TEMP_DIR
            if curl -L https://github.com/DigitalPals/pulse/archive/main.tar.gz -o pulse.tar.gz >> $LOG_FILE 2>&1 && 
               tar -xzf pulse.tar.gz >> $LOG_FILE 2>&1; then
                echo -e "${GREEN}Success${NC}"
                echo "SUCCESS: Downloaded repository using curl" >> $LOG_FILE
                cd pulse-main
            else
                echo -e "${RED}Failed${NC}"
                echo "FAILED: Could not download repository using alternate method" >> $LOG_FILE
                error "Failed to download repository. Installation cannot continue."
                return 1
            fi
        fi
        
        # Copy files
        echo -ne "${CYAN}Copying application files...${NC} "
        echo "Copying application files to installation directory..." >> $LOG_FILE
        
        if cp -r cybex_pulse/* $INSTALL_DIR/ >> $LOG_FILE 2>&1; then
            echo -e "${GREEN}Success${NC}"
            echo "SUCCESS: Copied application files" >> $LOG_FILE
        else
            echo -e "${RED}Failed${NC}"
            echo "FAILED: Could not copy application files" >> $LOG_FILE
            error "Failed to copy application files. Installation may be incomplete."
        fi
        
        # Copy pulse executable
        echo -ne "${CYAN}Installing executables...${NC} "
        echo "Installing executables..." >> $LOG_FILE
        
        mkdir -p /usr/local/bin
        if [ -f "pulse" ] && cp pulse /usr/local/bin/cybex-pulse >> $LOG_FILE 2>&1 && chmod +x /usr/local/bin/cybex-pulse >> $LOG_FILE 2>&1; then
            echo -e "${GREEN}Success${NC}"
            echo "SUCCESS: Installed executable" >> $LOG_FILE
        else
            echo -e "${RED}Failed${NC}"
            echo "FAILED: Could not install executable" >> $LOG_FILE
            
            # Create a basic executable if the original is not available
            echo -ne "${CYAN}Creating basic executable...${NC} "
            echo "Creating basic executable..." >> $LOG_FILE
            
            cat > /usr/local/bin/cybex-pulse << EOF
#!/bin/bash
# Auto-generated by Cybex Pulse installer
cd $INSTALL_DIR
$INSTALL_DIR/venv/bin/python -m cybex_pulse "\$@"
EOF
            chmod +x /usr/local/bin/cybex-pulse
            
            if [ -x /usr/local/bin/cybex-pulse ]; then
                echo -e "${GREEN}Success${NC}"
                echo "SUCCESS: Created basic executable" >> $LOG_FILE
            else
                echo -e "${RED}Failed${NC}"
                echo "FAILED: Could not create basic executable" >> $LOG_FILE
                error "Failed to create executable. You may need to run the application manually."
            fi
        fi
        
        # Clean up
        echo -ne "${CYAN}Cleaning up temporary files...${NC} "
        echo "Cleaning up temporary files..." >> $LOG_FILE
        
        if cd / && rm -rf $TEMP_DIR >> $LOG_FILE 2>&1; then
            echo -e "${GREEN}Success${NC}"
            echo "SUCCESS: Cleaned up temporary files" >> $LOG_FILE
        else
            echo -e "${RED}Failed${NC}"
            echo "FAILED: Could not clean up temporary files" >> $LOG_FILE
            warning "Failed to clean up temporary files, but installation can continue"
        fi
        
        success "Repository downloaded and installed"
    fi
    
    # Create symlink to the venv-python executable
    echo -ne "${CYAN}Creating Python symlink...${NC} "
    echo "Creating Python symlink..." >> $LOG_FILE
    
    if ln -sf $INSTALL_DIR/venv/bin/python /usr/local/bin/cybex-pulse-python >> $LOG_FILE 2>&1; then
        echo -e "${GREEN}Success${NC}"
        echo "SUCCESS: Created Python symlink" >> $LOG_FILE
    else
        echo -e "${RED}Failed${NC}"
        echo "FAILED: Could not create Python symlink" >> $LOG_FILE
        warning "Failed to create Python symlink, but installation can continue"
    fi
    
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
    # Clear screen for final display
    clear
    
    # Show logo again
    print_cybex_logo
    
    # Animated success message
    local success_msg="Installation Complete!"
    echo -ne "${GREEN}${BOLD}"
    for (( i=0; i<${#success_msg}; i++ )); do
        echo -ne "${success_msg:$i:1}"
        sleep 0.05
    done
    echo -e "${NC}\n"
    
    # ASCII success animation
    echo -e "${GREEN}"
    echo "  ██████╗ ██╗   ██╗ ██████╗ ██████╗███████╗███████╗███████╗██╗"
    echo "  ██╔══██╗██║   ██║██╔════╝██╔════╝██╔════╝██╔════╝██╔════╝██║"
    echo "  ██████╔╝██║   ██║██║     ██║     █████╗  ███████╗███████╗██║"
    echo "  ██╔═══╝ ██║   ██║██║     ██║     ██╔══╝  ╚════██║╚════██║╚═╝"
    echo "  ██║     ╚██████╔╝╚██████╗╚██████╗███████╗███████║███████║██╗"
    echo "  ╚═╝      ╚═════╝  ╚═════╝ ╚═════╝╚══════╝╚══════╝╚══════╝╚═╝"
    echo -e "${NC}\n"
    
    # Create fancy box
    local box_width=70
    local horizontal_line=""
    for ((i=0; i<box_width; i++)); do
        horizontal_line="${horizontal_line}═"
    done
    
    echo -e "${RED}╔${horizontal_line}╗${NC}"
    echo -e "${RED}║${DARK_BG}${WHITE}  Cybex Pulse has been successfully installed on your system!${GRAY}                  ${RED}║${NC}"
    echo -e "${RED}╚${horizontal_line}╝${NC}"
    echo
    
    # Access information with icons
    echo -e "${WHITE}${BOLD}🌐 Access Information${NC}"
    echo -e "  ${BLUE}${ARROW}${NC} Web Interface: ${GREEN}http://$(hostname -I | awk '{print $1}'):8000${NC}"
    echo
    
    # Service management with styled command boxes
    echo -e "${WHITE}${BOLD}⚙️  Service Management${NC}"
    echo -e "  ${BLUE}${ARROW}${NC} Start service:   ${DARK_BG}${RED} sudo systemctl start $SERVICE_NAME ${NC}"
    echo -e "  ${BLUE}${ARROW}${NC} Stop service:    ${DARK_BG}${RED} sudo systemctl stop $SERVICE_NAME ${NC}"
    echo -e "  ${BLUE}${ARROW}${NC} Restart service: ${DARK_BG}${RED} sudo systemctl restart $SERVICE_NAME ${NC}"
    echo -e "  ${BLUE}${ARROW}${NC} Check status:    ${DARK_BG}${RED} sudo systemctl status $SERVICE_NAME ${NC}"
    echo -e "  ${BLUE}${ARROW}${NC} View logs:       ${DARK_BG}${RED} sudo journalctl -u $SERVICE_NAME ${NC}"
    echo
    
    # Configuration information
    echo -e "${WHITE}${BOLD}🔧 Configuration${NC}"
    echo -e "  ${BLUE}${ARROW}${NC} Config file:     ${DARK_BG}${RED} $CONFIG_DIR/config.json ${NC}"
    echo -e "  ${BLUE}${ARROW}${NC} Log directory:   ${DARK_BG}${RED} $LOG_DIR ${NC}"
    echo -e "  ${BLUE}${ARROW}${NC} Install log:     ${DARK_BG}${RED} $LOG_FILE ${NC}"
    echo
    
    # Next steps
    echo -e "${WHITE}${BOLD}🔍 Next Steps${NC}"
    echo -e "  ${ORANGE}${BOLD}⚠️${NC}  If this is your first time running Cybex Pulse,"
    echo -e "      you'll need to complete the setup wizard in the web interface."
    echo
    
    # Troubleshooting
    echo -e "${WHITE}${BOLD}❓ Troubleshooting${NC}"
    echo -e "  ${BLUE}${ARROW}${NC} Check installation log: ${DARK_BG}${RED} cat $LOG_FILE ${NC}"
    echo -e "  ${BLUE}${ARROW}${NC} Check service status:   ${DARK_BG}${RED} sudo systemctl status $SERVICE_NAME ${NC}"
    echo -e "  ${BLUE}${ARROW}${NC} View service logs:      ${DARK_BG}${RED} sudo journalctl -u $SERVICE_NAME ${NC}"
    echo
    
    # Thank you message
    echo -e "${GREEN}${BOLD}Thank you for installing Cybex Pulse!${NC}"
    
    # Animated pulse at the end
    for ((i=0; i<3; i++)); do
        echo -ne "${RED}▮${NC}"
        sleep 0.2
        echo -ne "\b${RED}▯${NC}"
        sleep 0.2
        echo -ne "\b"
    done
    echo
}

# Main installation process
print_header

# Initialize log file
init_log

# Check if script is running as root
if [ "$EUID" -ne 0 ]; then
    error "This script must be run as root" "fatal"
fi

# Detect Linux distribution
check_distribution
echo -e "${BOLD}Detected distribution:${NC} $DISTRO ($DISTRO_FAMILY family)"
echo "Detected distribution: $DISTRO ($DISTRO_FAMILY family)" >> $LOG_FILE
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