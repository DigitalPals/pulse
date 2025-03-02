"""
Alerting module for Cybex Pulse.
"""
import json
import logging
import time
from typing import Dict, Optional

from cybex_pulse.database.db_manager import DatabaseManager
from cybex_pulse.utils.config import Config

class AlertManager:
    """Alert manager for sending notifications."""
    
    def __init__(self, config: Config, db_manager: DatabaseManager, logger: logging.Logger):
        """Initialize the alert manager.
        
        Args:
            config: Configuration manager
            db_manager: Database manager
            logger: Logger instance
        """
        self.config = config
        self.db_manager = db_manager
        self.logger = logger
        
        # Initialize Telegram bot if enabled
        self.telegram_bot = None
        if self.config.get("telegram", "enabled"):
            self._init_telegram()
    
    def _init_telegram(self) -> None:
        """Initialize Telegram bot."""
        try:
            # Import here to avoid dependency if feature is disabled
            import telegram
            
            api_token = self.config.get("telegram", "api_token")
            if not api_token:
                self.logger.error("Telegram API token not configured")
                return
            
            self.telegram_bot = telegram.Bot(token=api_token)
            self.logger.info("Telegram bot initialized")
        except ImportError:
            self.logger.error("python-telegram-bot not installed. Telegram alerts disabled.")
        except Exception as e:
            self.logger.error(f"Error initializing Telegram bot: {e}")
    
    def send_alert(self, title: str, message: str, severity: str = "info") -> bool:
        """Send an alert.
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity (info, warning, error)
            
        Returns:
            bool: True if alert was sent successfully, False otherwise
        """
        if not self.config.get("alerts", "enabled"):
            return False
        
        # Log the alert
        self.logger.info(f"Alert: {title} - {message}")
        
        # Log to database
        self.db_manager.log_event(
            self.db_manager.EVENT_ALERT,
            severity,
            title,
            message
        )
        
        # Send via Telegram if enabled
        telegram_sent = False
        if self.config.get("telegram", "enabled") and self.telegram_bot:
            telegram_sent = self._send_telegram_alert(title, message)
        
        return telegram_sent
    
    def _send_telegram_alert(self, title: str, message: str) -> bool:
        """Send an alert via Telegram.
        
        Args:
            title: Alert title
            message: Alert message
            
        Returns:
            bool: True if alert was sent successfully, False otherwise
        """
        try:
            chat_id = self.config.get("telegram", "chat_id")
            if not chat_id:
                self.logger.error("Telegram chat ID not configured")
                return False
            
            # Format message
            formatted_message = f"*{title}*\n\n{message}"
            
            # Send message
            self.telegram_bot.send_message(
                chat_id=chat_id,
                text=formatted_message,
                parse_mode="Markdown"
            )
            
            self.logger.debug(f"Telegram alert sent: {title}")
            return True
        except Exception as e:
            self.logger.error(f"Error sending Telegram alert: {e}")
            return False