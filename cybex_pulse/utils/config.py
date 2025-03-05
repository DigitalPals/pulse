"""
Configuration management for Cybex Pulse.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("cybex_pulse.config")

class Config:
    """Configuration manager for Cybex Pulse application."""
    
    DEFAULT_CONFIG = {
        "general": {
            "scan_interval": 60,  # seconds
            "configured": False,
            "debug_logging": False,  # Enable/disable debug logging
        },
        "network": {
            "subnet": "",  # Will be auto-detected during setup
            "scan_tool": "arp-scan",
            "important_devices": [],
        },
        "alerts": {
            "enabled": True,
            "new_device": True,
            "device_offline": True,
            "important_device_offline": True,
            "latency_threshold": 100,  # ms
            "website_error": True,
        },
        "telegram": {
            "enabled": False,
            "api_token": "",
            "chat_id": "",
        },
        "monitoring": {
            "internet_health": {
                "enabled": False,
                "interval": 3600,  # seconds
            },
            "websites": {
                "enabled": False,
                "urls": [],
                "interval": 300,  # seconds
            },
            "security": {
                "enabled": False,
                "interval": 86400,  # seconds
            },
        },
        "fingerprinting": {
            "enabled": False,
            "confidence_threshold": 0.5,
            "max_threads": 10,
            "timeout": 2,
            "scan_interval": 86400,  # Default to daily scanning (in seconds)
        },
        "web_interface": {
            "enabled": True,
            "host": "0.0.0.0",
            "port": 8080,
            "username": "",
            "password_hash": "",
        },
    }
    
    def __init__(self, config_path: Path):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default if not exists."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_path}")
                
                # Update with any missing default values
                self._update_with_defaults(config)
                return config
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
                logger.info("Using default configuration")
                return self.DEFAULT_CONFIG.copy()
        else:
            logger.info(f"Configuration file not found, creating default at {self.config_path}")
            config = self.DEFAULT_CONFIG.copy()
            # Save the default config to file
            try:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_path, "w") as f:
                    json.dump(config, f, indent=4)
                logger.info(f"Configuration saved to {self.config_path}")
            except Exception as e:
                logger.error(f"Error saving configuration: {e}")
            return config
    
    def _update_with_defaults(self, config: Dict[str, Any]) -> None:
        """Update configuration with any missing default values."""
        def update_nested(target, source):
            for key, value in source.items():
                if key not in target:
                    target[key] = value
                elif isinstance(value, dict) and isinstance(target[key], dict):
                    update_nested(target[key], value)
        
        update_nested(config, self.DEFAULT_CONFIG)
    
    def save(self) -> bool:
        """Save current configuration to file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key within section (if None, returns entire section)
            default: Default value to return if key is not found
            
        Returns:
            Configuration value, default value, or None if not found
        """
        if section not in self.config:
            return default
        
        if key is None:
            return self.config[section]
        
        if isinstance(self.config[section], dict):
            return self.config[section].get(key, default)
        
        return default
    
    def set(self, section: str, key: str, value: Any) -> bool:
        """Set configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key within section
            value: Value to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
        return self.save()
    
    def is_configured(self) -> bool:
        """Check if application has been configured."""
        return self.get("general", "configured") is True
    
    def mark_as_configured(self) -> bool:
        """Mark application as configured."""
        return self.set("general", "configured", True)