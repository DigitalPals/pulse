"""
Icon mapper utility for Cybex Pulse.
"""
import re
from typing import Dict, Tuple

class IconMapper:
    """Utility class for mapping device names and vendors to appropriate Font Awesome icons."""
    
    def __init__(self):
        """Initialize the icon mapper."""
        # Mapping of keywords to Font Awesome icon classes
        self.icon_mappings = {
            # Vendor name mappings
            'apple': ('fab', 'apple'),
            'google': ('fab', 'google'),
            'microsoft': ('fab', 'microsoft'),
            'windows': ('fab', 'windows'),
            'linux': ('fab', 'linux'),
            'android': ('fab', 'android'),
            'amazon': ('fab', 'amazon'),
            'aws': ('fab', 'aws'),
            'raspberry': ('fab', 'raspberry-pi'),
            'ubuntu': ('fab', 'ubuntu'),
            'debian': ('fab', 'debian'),
            'fedora': ('fab', 'fedora'),
            'redhat': ('fab', 'redhat'),
            'centos': ('fab', 'centos'),
            'suse': ('fab', 'suse'),
            'freebsd': ('fab', 'freebsd'),
            'github': ('fab', 'github'),
            'gitlab': ('fab', 'gitlab'),
            'bitbucket': ('fab', 'bitbucket'),
            'docker': ('fab', 'docker'),
            'php': ('fab', 'php'),
            'python': ('fab', 'python'),
            'java': ('fab', 'java'),
            'js': ('fab', 'js'),
            'node': ('fab', 'node'),
            'npm': ('fab', 'npm'),
            'react': ('fab', 'react'),
            'angular': ('fab', 'angular'),
            'vuejs': ('fab', 'vuejs'),
            'wordpress': ('fab', 'wordpress'),
            'joomla': ('fab', 'joomla'),
            'drupal': ('fab', 'drupal'),
            'magento': ('fab', 'magento'),
            'shopify': ('fab', 'shopify'),
            'woocommerce': ('fab', 'woocommerce'),
            'paypal': ('fab', 'paypal'),
            'stripe': ('fab', 'stripe'),
            'cc-visa': ('fab', 'cc-visa'),
            'cc-mastercard': ('fab', 'cc-mastercard'),
            'cc-amex': ('fab', 'cc-amex'),
            'cc-discover': ('fab', 'cc-discover'),
            'cc-paypal': ('fab', 'cc-paypal'),
            'cc-stripe': ('fab', 'cc-stripe'),
            'bitcoin': ('fab', 'bitcoin'),
            'ethereum': ('fab', 'ethereum'),
            'facebook': ('fab', 'facebook'),
            'twitter': ('fab', 'twitter'),
            'instagram': ('fab', 'instagram'),
            'linkedin': ('fab', 'linkedin'),
            'youtube': ('fab', 'youtube'),
            'twitch': ('fab', 'twitch'),
            'discord': ('fab', 'discord'),
            'slack': ('fab', 'slack'),
            'telegram': ('fab', 'telegram'),
            'whatsapp': ('fab', 'whatsapp'),
            'viber': ('fab', 'viber'),
            'skype': ('fab', 'skype'),
            'dropbox': ('fab', 'dropbox'),
            'spotify': ('fab', 'spotify'),
            'soundcloud': ('fab', 'soundcloud'),
            'itunes': ('fab', 'itunes'),
            'playstation': ('fab', 'playstation'),
            'xbox': ('fab', 'xbox'),
            'nintendo': ('fab', 'nintendo-switch'),
            'steam': ('fab', 'steam'),
            'twitch': ('fab', 'twitch'),
            'chrome': ('fab', 'chrome'),
            'firefox': ('fab', 'firefox'),
            'edge': ('fab', 'edge'),
            'safari': ('fab', 'safari'),
            'opera': ('fab', 'opera'),
            'internet-explorer': ('fab', 'internet-explorer'),
            
            # Device type mappings
            'sonos': ('fas', 'volume-up'),  # Audio device
            'speaker': ('fas', 'volume-up'),
            'audio': ('fas', 'volume-up'),
            'sound': ('fas', 'volume-up'),
            'music': ('fas', 'music'),
            'headphone': ('fas', 'headphones'),
            'earphone': ('fas', 'headphones'),
            'microphone': ('fas', 'microphone'),
            'mic': ('fas', 'microphone'),
            
            'ubiquiti': ('fas', 'wifi'),  # Network devices
            'unifi': ('fas', 'wifi'),
            'router': ('fas', 'network-wired'),
            'switch': ('fas', 'network-wired'),
            'access point': ('fas', 'wifi'),
            'ap': ('fas', 'wifi'),
            'wifi': ('fas', 'wifi'),
            'wireless': ('fas', 'wifi'),
            'network': ('fas', 'network-wired'),
            'ethernet': ('fas', 'ethernet'),
            'modem': ('fas', 'hdd'),
            'gateway': ('fas', 'network-wired'),
            'firewall': ('fas', 'shield-alt'),
            'vpn': ('fas', 'shield-alt'),
            'cisco': ('fas', 'network-wired'),
            'netgear': ('fas', 'network-wired'),
            'linksys': ('fas', 'network-wired'),
            'tp-link': ('fas', 'network-wired'),
            'asus': ('fas', 'network-wired'),
            'dlink': ('fas', 'network-wired'),
            'd-link': ('fas', 'network-wired'),
            
            'camera': ('fas', 'camera'),  # Camera devices
            'webcam': ('fas', 'camera'),
            'security camera': ('fas', 'video'),
            'cctv': ('fas', 'video'),
            'surveillance': ('fas', 'video'),
            'doorbell': ('fas', 'bell'),
            'ring': ('fas', 'bell'),
            'nest': ('fas', 'home'),
            
            'tv': ('fas', 'tv'),  # Media devices
            'television': ('fas', 'tv'),
            'monitor': ('fas', 'desktop'),
            'display': ('fas', 'desktop'),
            'screen': ('fas', 'desktop'),
            'projector': ('fas', 'film'),
            'media': ('fas', 'play-circle'),
            'player': ('fas', 'play'),
            'roku': ('fas', 'tv'),
            'chromecast': ('fas', 'cast'),
            'apple tv': ('fab', 'apple'),
            'fire tv': ('fab', 'amazon'),
            'streaming': ('fas', 'stream'),
            
            'phone': ('fas', 'mobile-alt'),  # Mobile devices
            'smartphone': ('fas', 'mobile-alt'),
            'mobile': ('fas', 'mobile-alt'),
            'cell': ('fas', 'mobile-alt'),
            'iphone': ('fab', 'apple'),
            'android': ('fab', 'android'),
            'tablet': ('fas', 'tablet-alt'),
            'ipad': ('fab', 'apple'),
            
            'laptop': ('fas', 'laptop'),  # Computer devices
            'notebook': ('fas', 'laptop'),
            'desktop': ('fas', 'desktop'),
            'computer': ('fas', 'desktop'),
            'pc': ('fas', 'desktop'),
            'server': ('fas', 'server'),
            'workstation': ('fas', 'desktop'),
            'terminal': ('fas', 'terminal'),
            'mainframe': ('fas', 'server'),
            'nas': ('fas', 'database'),
            'storage': ('fas', 'database'),
            'synology': ('fas', 'database'),
            'qnap': ('fas', 'database'),
            
            'printer': ('fas', 'print'),  # Printer devices
            'scanner': ('fas', 'print'),
            'copier': ('fas', 'copy'),
            'fax': ('fas', 'fax'),
            
            'thermostat': ('fas', 'thermometer-half'),  # Smart home devices
            'temperature': ('fas', 'thermometer-half'),
            'climate': ('fas', 'temperature-high'),
            'hvac': ('fas', 'fan'),
            'air conditioner': ('fas', 'snowflake'),
            'heater': ('fas', 'fire'),
            'fan': ('fas', 'fan'),
            'light': ('fas', 'lightbulb'),
            'bulb': ('fas', 'lightbulb'),
            'lamp': ('fas', 'lightbulb'),
            'switch': ('fas', 'toggle-on'),
            'outlet': ('fas', 'plug'),
            'plug': ('fas', 'plug'),
            'sensor': ('fas', 'eye'),
            'motion': ('fas', 'running'),
            'door': ('fas', 'door-open'),
            'window': ('fas', 'window-maximize'),
            'blind': ('fas', 'blinds'),
            'shade': ('fas', 'blinds'),
            'curtain': ('fas', 'blinds'),
            'lock': ('fas', 'lock'),
            'security': ('fas', 'shield-alt'),
            'alarm': ('fas', 'bell'),
            'smoke': ('fas', 'smoking'),
            'carbon monoxide': ('fas', 'cloud'),
            'water': ('fas', 'tint'),
            'leak': ('fas', 'tint-slash'),
            'valve': ('fas', 'faucet'),
            'irrigation': ('fas', 'faucet'),
            'sprinkler': ('fas', 'faucet'),
            'vacuum': ('fas', 'broom'),
            'robot': ('fas', 'robot'),
            
            'watch': ('fas', 'clock'),  # Wearable devices
            'smartwatch': ('fas', 'clock'),
            'fitness': ('fas', 'heartbeat'),
            'health': ('fas', 'heartbeat'),
            'fitbit': ('fas', 'heartbeat'),
            'garmin': ('fas', 'heartbeat'),
            
            'game': ('fas', 'gamepad'),  # Gaming devices
            'gaming': ('fas', 'gamepad'),
            'console': ('fas', 'gamepad'),
            'controller': ('fas', 'gamepad'),
            'playstation': ('fab', 'playstation'),
            'xbox': ('fab', 'xbox'),
            'nintendo': ('fab', 'nintendo-switch'),
            'switch': ('fab', 'nintendo-switch'),
            'wii': ('fas', 'gamepad'),
            
            'car': ('fas', 'car'),  # Vehicle devices
            'vehicle': ('fas', 'car'),
            'automotive': ('fas', 'car'),
            'tesla': ('fas', 'car'),
            'ev': ('fas', 'charging-station'),
            'charging': ('fas', 'charging-station'),
            
            'battery': ('fas', 'battery-full'),  # Power devices
            'ups': ('fas', 'plug'),
            'power': ('fas', 'bolt'),
            'energy': ('fas', 'bolt'),
            'solar': ('fas', 'sun'),
            'generator': ('fas', 'bolt'),
            
            'hub': ('fas', 'circle-nodes'),  # Hub devices
            'bridge': ('fas', 'exchange-alt'),
            'zigbee': ('fas', 'project-diagram'),
            'zwave': ('fas', 'project-diagram'),
            'bluetooth': ('fab', 'bluetooth'),
            'remote': ('fas', 'remote'),
            'control': ('fas', 'sliders-h'),
            'ir': ('fas', 'rss'),
            'infrared': ('fas', 'rss'),
            'rf': ('fas', 'broadcast-tower'),
            'radio': ('fas', 'broadcast-tower'),
            
            # Default for unknown devices
            'unknown': ('fas', 'question-circle'),
            'default': ('fas', 'laptop'),
        }
    
    def get_icon_for_device(self, vendor: str = None, device_name: str = None) -> Tuple[str, str]:
        """Get the appropriate Font Awesome icon for a device.
        
        Args:
            vendor: Vendor name of the device
            device_name: Name of the device
            
        Returns:
            Tuple of (icon_family, icon_name) for Font Awesome
        """
        # Normalize inputs to lowercase and handle None
        vendor_lower = (vendor or '').lower()
        device_name_lower = (device_name or '').lower()
        
        # First check if the vendor name matches any of our mappings
        for keyword, icon in self.icon_mappings.items():
            if keyword in vendor_lower:
                return icon
        
        # If no vendor match, check if the device name matches any of our mappings
        for keyword, icon in self.icon_mappings.items():
            if keyword in device_name_lower:
                return icon
        
        # If no match found, return a default icon
        return self.icon_mappings['default']
    
    def get_icon_html(self, vendor: str = None, device_name: str = None) -> str:
        """Get the HTML for a Font Awesome icon for a device.
        
        Args:
            vendor: Vendor name of the device
            device_name: Name of the device
            
        Returns:
            HTML string for the Font Awesome icon
        """
        icon_family, icon_name = self.get_icon_for_device(vendor, device_name)
        return f'<i class="{icon_family} fa-{icon_name}"></i>'