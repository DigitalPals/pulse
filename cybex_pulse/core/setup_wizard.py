"""
Setup wizard for Cybex Pulse.

This module provides an interactive command-line setup wizard that helps users:
- Configure network settings
- Set up alerting channels
- Configure the web interface
- Enable and configure device fingerprinting
- Set up additional monitoring features
"""
import ipaddress
import json
import logging
import os
import re
import socket
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from cybex_pulse.database.db_manager import DatabaseManager
from cybex_pulse.utils.config import Config

logger = logging.getLogger("cybex_pulse.setup_wizard")

class SetupWizard:
    """Setup wizard for Cybex Pulse application.
    
    This class provides a user-friendly command-line interface for initial system configuration,
    walking users through each configuration section with appropriate prompts, validation,
    and auto-detection where possible.
    """
    
    def __init__(self, config: Config, db_manager: DatabaseManager):
        """Initialize setup wizard.
        
        Args:
            config: Configuration manager
            db_manager: Database manager
        """
        self.config = config
        self.db_manager = db_manager
    
    def run(self) -> bool:
        """Run the setup wizard.
        
        Returns:
            bool: True if setup completed successfully, False otherwise
        """
        print("\n" + "=" * 60)
        print("Welcome to Cybex Pulse - Home Network Monitoring Setup Wizard")
        print("=" * 60 + "\n")
        
        print("This wizard will guide you through the initial setup of Cybex Pulse.")
        print("You can change these settings later through the web interface.\n")
        
        try:
            # Network configuration
            if not self._setup_network():
                return False
            
            # Telegram alerts configuration
            self._setup_telegram()
            
            # Web interface configuration
            self._setup_web_interface()
            
            # Device fingerprinting configuration
            self._setup_fingerprinting()
            
            # Additional monitoring features
            self._setup_additional_features()
            
            # Mark as configured
            self.config.mark_as_configured()
            
            print("\n" + "=" * 60)
            print("Setup completed successfully!")
            print("You can now start using Cybex Pulse.")
            print("The web interface will be available at:")
            host = self.config.get("web_interface", "host")
            port = self.config.get("web_interface", "port")
            print(f"http://{host}:{port}")
            print("=" * 60 + "\n")
            
            return True
            
        except KeyboardInterrupt:
            print("\nSetup cancelled by user.")
            return False
        except Exception as e:
            logger.exception("Error during setup: %s", str(e))
            print(f"\nAn error occurred during setup: {str(e)}")
            return False
    
    def _setup_network(self) -> bool:
        """Configure network settings.
        
        Returns:
            bool: True if successful, False otherwise
        """
        print("\n--- Network Configuration ---\n")
        
        # Auto-detect subnet
        subnet = self._detect_subnet()
        if subnet:
            print(f"Detected subnet: {subnet}")
            use_detected = input("Use this subnet? (Y/n): ").strip().lower() != "n"
            
            if use_detected:
                self.config.set("network", "subnet", subnet)
            else:
                custom_subnet = input("Enter subnet to scan (e.g., 192.168.1.0/24): ").strip()
                if not custom_subnet:
                    print("Subnet cannot be empty. Using detected subnet.")
                    self.config.set("network", "subnet", subnet)
                else:
                    self.config.set("network", "subnet", custom_subnet)
        else:
            print("Could not auto-detect subnet.")
            custom_subnet = input("Enter subnet to scan (e.g., 192.168.1.0/24): ").strip()
            if not custom_subnet:
                print("Subnet cannot be empty. Setup cannot continue.")
                return False
            self.config.set("network", "subnet", custom_subnet)
        
        # Configure scan interval
        scan_interval = self.config.get("general", "scan_interval")
        custom_interval = input(f"Enter network scan interval in seconds (default: {scan_interval}): ").strip()
        if custom_interval and custom_interval.isdigit() and int(custom_interval) > 0:
            self.config.set("general", "scan_interval", int(custom_interval))
        
        return True
    
    def _setup_telegram(self) -> None:
        """Configure Telegram alerts."""
        print("\n--- Telegram Alerts Configuration ---\n")
        
        enable_telegram = input("Do you want to enable Telegram alerts? (y/N): ").strip().lower() == "y"
        self.config.set("telegram", "enabled", enable_telegram)
        
        if enable_telegram:
            print("\nTo use Telegram alerts, you need a Telegram Bot API token.")
            print("If you don't have one, you can create a bot by talking to @BotFather on Telegram.")
            
            api_token = input("Enter your Telegram Bot API token: ").strip()
            if api_token:
                self.config.set("telegram", "api_token", api_token)
            
            chat_id = input("Enter your Telegram chat ID: ").strip()
            if chat_id:
                self.config.set("telegram", "chat_id", chat_id)
            
            if not api_token or not chat_id:
                print("Warning: Telegram alerts are enabled but configuration is incomplete.")
                print("You can complete the configuration later through the web interface.")
    
    def _setup_web_interface(self) -> None:
        """Configure web interface."""
        print("\n--- Web Interface Configuration ---\n")
        
        enable_web = input("Do you want to enable the web interface? (Y/n): ").strip().lower() != "n"
        self.config.set("web_interface", "enabled", enable_web)
        
        if enable_web:
            # Host configuration
            default_host = self.config.get("web_interface", "host")
            host = input(f"Enter web interface host (default: {default_host}): ").strip()
            if host:
                self.config.set("web_interface", "host", host)
            
            # Port configuration
            default_port = self.config.get("web_interface", "port")
            port_input = input(f"Enter web interface port (default: {default_port}): ").strip()
            if port_input and port_input.isdigit() and 1024 <= int(port_input) <= 65535:
                self.config.set("web_interface", "port", int(port_input))
            
            # Authentication
            setup_auth = input("Do you want to set up authentication for the web interface? (y/N): ").strip().lower() == "y"
            if setup_auth:
                import hashlib
                import getpass
                
                username = input("Enter username: ").strip()
                if username:
                    self.config.set("web_interface", "username", username)
                
                password = getpass.getpass("Enter password: ")
                if password:
                    # Simple password hashing - in a real app, use a proper password hashing library
                    password_hash = hashlib.sha256(password.encode()).hexdigest()
                    self.config.set("web_interface", "password_hash", password_hash)
    
    def _setup_fingerprinting(self) -> None:
        """Configure device fingerprinting."""
        print("\n--- Device Fingerprinting Configuration ---\n")
        
        print("Device fingerprinting allows Cybex Pulse to automatically identify")
        print("device types, manufacturers, and models on your network by analyzing")
        print("their network signatures, open ports, and service responses.")
        
        # Enable fingerprinting
        enable_fingerprinting = input("Do you want to enable device fingerprinting? (y/N): ").strip().lower() == "y"
        
        # Initialize fingerprinting config if it doesn't exist
        if "fingerprinting" not in self.config.config:
            self.config.config["fingerprinting"] = {
                "enabled": False,
                "confidence_threshold": 0.5,
                "max_threads": 10,
                "timeout": 2
            }
        
        # Set fingerprinting enabled state
        self.config.set("fingerprinting", "enabled", enable_fingerprinting)
        
        if enable_fingerprinting:
            # Confidence threshold
            default_confidence = self.config.get("fingerprinting", "confidence_threshold", default=0.5)
            confidence_input = input(f"Enter minimum confidence threshold (0.1-1.0, default: {default_confidence}): ").strip()
            if confidence_input and 0.1 <= float(confidence_input) <= 1.0:
                self.config.set("fingerprinting", "confidence_threshold", float(confidence_input))
            
            # Max threads
            default_threads = self.config.get("fingerprinting", "max_threads", default=10)
            threads_input = input(f"Enter maximum concurrent threads (1-20, default: {default_threads}): ").strip()
            if threads_input and threads_input.isdigit() and 1 <= int(threads_input) <= 20:
                self.config.set("fingerprinting", "max_threads", int(threads_input))
            
            # Timeout
            default_timeout = self.config.get("fingerprinting", "timeout", default=2)
            timeout_input = input(f"Enter fingerprinting timeout in seconds (1-10, default: {default_timeout}): ").strip()
            if timeout_input and timeout_input.isdigit() and 1 <= int(timeout_input) <= 10:
                self.config.set("fingerprinting", "timeout", int(timeout_input))

    def _setup_additional_features(self) -> None:
        """Configure additional monitoring features."""
        print("\n--- Additional Features Configuration ---\n")
        
        # Internet health check
        enable_health = input("Do you want to enable internet health checks? (y/N): ").strip().lower() == "y"
        self.config.set("monitoring", "internet_health", {"enabled": enable_health, "interval": 3600})
        
        # Website monitoring
        enable_websites = input("Do you want to enable website monitoring? (y/N): ").strip().lower() == "y"
        self.config.set("monitoring", "websites", {"enabled": enable_websites, "urls": [], "interval": 300})
        
        if enable_websites:
            print("\nYou can add up to 5 websites to monitor.")
            websites = []
            for i in range(5):
                url = input(f"Enter website URL #{i+1} (or leave empty to skip): ").strip()
                if not url:
                    break
                websites.append(url)
            
            if websites:
                self.config.get("monitoring", "websites")["urls"] = websites
        
        # Security scanning
        enable_security = input("Do you want to enable security scanning? (y/N): ").strip().lower() == "y"
        self.config.set("monitoring", "security", {"enabled": enable_security, "interval": 86400})
        
        if enable_security:
            print("\nNote: Security scanning requires elevated permissions and additional tools.")
            print("Make sure you have nmap installed and proper permissions to use it.")
    
    def _detect_subnet(self) -> Optional[str]:
        """Auto-detect the local subnet.
        
        Returns:
            str: Detected subnet in CIDR notation or None if detection failed
        """
        try:
            # Get the hostname
            hostname = socket.gethostname()
            # Default IP address from hostname
            ip_address = socket.gethostbyname(hostname)
            detected_subnet = None
            
            # Try to get the network interface information
            if os.name == "posix":  # Linux/Mac
                try:
                    # First try to get subnet directly from 'ip route' command
                    result = subprocess.run(
                        ["ip", "route"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    # Look for default gateway and its associated subnet
                    for line in result.stdout.splitlines():
                        # Match default route
                        if line.startswith("default via"):
                            # Now look for the corresponding subnet definition
                            gateway_match = re.search(r"via\s+(\d+\.\d+\.\d+\.\d+)", line)
                            if gateway_match:
                                gateway = gateway_match.group(1)
                                # Get the interface from default route
                                iface_match = re.search(r"dev\s+(\S+)", line)
                                if iface_match:
                                    iface = iface_match.group(1)
                                    # Now find the subnet for this interface
                                    for iface_line in result.stdout.splitlines():
                                        if iface in iface_line and "proto kernel" in iface_line:
                                            subnet_match = re.search(r"(\d+\.\d+\.\d+\.\d+/\d+)", iface_line)
                                            if subnet_match:
                                                detected_subnet = subnet_match.group(1)
                                                break
                    
                    # If subnet not found, try to get source IP from ip route get
                    if not detected_subnet:
                        result = subprocess.run(
                            ["ip", "route", "get", "1.1.1.1"],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        
                        # Parse the output to get the source IP
                        match = re.search(r"src\s+(\d+\.\d+\.\d+\.\d+)", result.stdout)
                        if match:
                            ip_address = match.group(1)
                except (subprocess.SubprocessError, FileNotFoundError):
                    # Fallback to ifconfig
                    try:
                        result = subprocess.run(
                            ["ifconfig"],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        
                        # Look for inet addr pattern
                        for line in result.stdout.splitlines():
                            match = re.search(r"inet\s+(?:addr:)?(\d+\.\d+\.\d+\.\d+)", line)
                            if match and not match.group(1).startswith("127."):
                                ip_address = match.group(1)
                                break
                    except (subprocess.SubprocessError, FileNotFoundError):
                        # Use the hostname method as fallback
                        pass
            
            # If we found a subnet directly from ip route, return it
            if detected_subnet:
                return detected_subnet
                
            # Otherwise convert IP to subnet intelligently
            ip_obj = ipaddress.IPv4Address(ip_address)
            
            # Try to infer from common network patterns
            first_octet = ip_obj.packed[0]
            if first_octet == 10:  # Class A private networks often use /8, /16, /23, or /24
                # Check for special case of 10.10.x.y which might be a /23
                if ip_obj.packed[1] == 10 and (ip_obj.packed[2] in [0, 1]):
                    network = ipaddress.IPv4Network(f"10.10.0.0/23", strict=False)
                else:
                    # Default to /24 for other 10.x.y.z networks
                    network = ipaddress.IPv4Network(f"{ip_obj.packed[0]}.{ip_obj.packed[1]}.{ip_obj.packed[2]}.0/24", strict=False)
            elif first_octet == 172 and 16 <= ip_obj.packed[1] <= 31:  # Class B private
                network = ipaddress.IPv4Network(f"{ip_obj.packed[0]}.{ip_obj.packed[1]}.{ip_obj.packed[2]}.0/24", strict=False)
            elif first_octet == 192 and ip_obj.packed[1] == 168:  # Class C private
                network = ipaddress.IPv4Network(f"{ip_obj.packed[0]}.{ip_obj.packed[1]}.{ip_obj.packed[2]}.0/24", strict=False)
            else:  # Default for other networks
                network = ipaddress.IPv4Network(f"{ip_obj.packed[0]}.{ip_obj.packed[1]}.{ip_obj.packed[2]}.0/24", strict=False)
            
            return str(network)
        except Exception as e:
            logger.error(f"Error detecting subnet: {e}")
            return None