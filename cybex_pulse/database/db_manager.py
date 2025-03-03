"""
Database management for Cybex Pulse.
"""
import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("cybex_pulse.database")

class DatabaseManager:
    """SQLite database manager for Cybex Pulse application."""
    
    def __init__(self, db_path: Path):
        """Initialize database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.local = threading.local()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get SQLite connection, creating it if necessary.
        
        Creates a thread-local connection to ensure thread safety.
        """
        if not hasattr(self.local, 'conn') or self.local.conn is None:
            self.local.conn = sqlite3.connect(self.db_path)
            self.local.conn.row_factory = sqlite3.Row
        return self.local.conn
    
    def initialize_database(self) -> None:
        """Initialize database schema if not exists."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create devices table with all columns
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address TEXT UNIQUE NOT NULL,
            ip_address TEXT,
            hostname TEXT,
            vendor TEXT,
            first_seen INTEGER NOT NULL,
            last_seen INTEGER NOT NULL,
            is_important BOOLEAN DEFAULT 0,
            is_known BOOLEAN DEFAULT 1,
            notes TEXT,
            device_type TEXT,
            device_model TEXT,
            device_manufacturer TEXT,
            fingerprint_confidence REAL,
            fingerprint_date INTEGER,
            never_fingerprint BOOLEAN DEFAULT 0
        )
        ''')
        
        # Create events table for logging
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            details TEXT
        )
        ''')
        
        # Create speed tests table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS speed_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            download_speed REAL,
            upload_speed REAL,
            ping REAL,
            isp TEXT,
            server_name TEXT,
            error TEXT
        )
        ''')
        
        # Create website monitoring table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS website_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            status_code INTEGER,
            response_time REAL,
            is_up BOOLEAN,
            error_message TEXT
        )
        ''')
        
        # Create security scans table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS security_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            open_ports TEXT,
            vulnerabilities TEXT,
            FOREIGN KEY (device_id) REFERENCES devices (id)
        )
        ''')
        
        # Check for missing columns in devices table and add them if needed
        cursor.execute("PRAGMA table_info(devices)")
        existing_device_columns = [column[1] for column in cursor.fetchall()]
        
        # Add device_type column if it doesn't exist
        if 'device_type' not in existing_device_columns:
            logger.info("Adding missing device_type column to devices table")
            cursor.execute("ALTER TABLE devices ADD COLUMN device_type TEXT")
            
        # Add device_model column if it doesn't exist
        if 'device_model' not in existing_device_columns:
            logger.info("Adding missing device_model column to devices table")
            cursor.execute("ALTER TABLE devices ADD COLUMN device_model TEXT")
            
        # Add device_manufacturer column if it doesn't exist
        if 'device_manufacturer' not in existing_device_columns:
            logger.info("Adding missing device_manufacturer column to devices table")
            cursor.execute("ALTER TABLE devices ADD COLUMN device_manufacturer TEXT")
            
        # Add fingerprint_confidence column if it doesn't exist
        if 'fingerprint_confidence' not in existing_device_columns:
            logger.info("Adding missing fingerprint_confidence column to devices table")
            cursor.execute("ALTER TABLE devices ADD COLUMN fingerprint_confidence REAL")
            
        # Add fingerprint_date column if it doesn't exist
        if 'fingerprint_date' not in existing_device_columns:
            logger.info("Adding missing fingerprint_date column to devices table")
            cursor.execute("ALTER TABLE devices ADD COLUMN fingerprint_date INTEGER")
            
        # Add never_fingerprint column if it doesn't exist
        if 'never_fingerprint' not in existing_device_columns:
            logger.info("Adding missing never_fingerprint column to devices table")
            cursor.execute("ALTER TABLE devices ADD COLUMN never_fingerprint BOOLEAN DEFAULT 0")
            
        # Check for missing columns in speed_tests table and add them if needed
        cursor.execute("PRAGMA table_info(speed_tests)")
        existing_speed_test_columns = [column[1] for column in cursor.fetchall()]
        
        # Add error column to speed_tests if it doesn't exist
        if 'error' not in existing_speed_test_columns:
            logger.info("Adding missing error column to speed_tests table")
            cursor.execute("ALTER TABLE speed_tests ADD COLUMN error TEXT")
            
        conn.commit()
        logger.info("Database initialized successfully")
    
    def close(self) -> None:
        """Close database connection for the current thread."""
        if hasattr(self.local, 'conn') and self.local.conn:
            self.local.conn.close()
            self.local.conn = None
    
    # Device management methods
    
    def add_device(self, mac_address: str, ip_address: str, hostname: str = "", 
                  vendor: str = "", is_important: bool = False, **kwargs) -> int:
        """Add a new device to the database.
        
        Args:
            mac_address: MAC address of the device
            ip_address: IP address of the device
            hostname: Hostname of the device (if available)
            vendor: Vendor/manufacturer of the device (if available)
            is_important: Whether this is an important device
            **kwargs: Additional device attributes (device_type, device_model, etc.)
            
        Returns:
            int: ID of the newly added device
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        current_time = int(time.time())
        
        # Extract additional fields from kwargs
        device_type = kwargs.get('device_type', '')
        device_model = kwargs.get('device_model', '')
        device_manufacturer = kwargs.get('device_manufacturer', '')
        fingerprint_confidence = kwargs.get('fingerprint_confidence', None)
        fingerprint_date = kwargs.get('fingerprint_date', None)
        
        try:
            cursor.execute('''
            INSERT INTO devices (mac_address, ip_address, hostname, vendor, 
                               first_seen, last_seen, is_important, 
                               device_type, device_model, device_manufacturer,
                               fingerprint_confidence, fingerprint_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (mac_address, ip_address, hostname, vendor, 
                 current_time, current_time, is_important,
                 device_type, device_model, device_manufacturer,
                 fingerprint_confidence, fingerprint_date))
            
            conn.commit()
            device_id = cursor.lastrowid
            logger.info(f"Added new device: {mac_address} ({ip_address})")
            return device_id
        except sqlite3.IntegrityError:
            # Device already exists, update it instead
            self.update_device(mac_address, ip_address, hostname, vendor)
            # Also update metadata if provided
            if any(key in kwargs for key in ['device_type', 'device_model', 'device_manufacturer', 
                                           'fingerprint_confidence', 'fingerprint_date']):
                self.update_device_metadata(mac_address, {
                    'device_type': device_type,
                    'device_model': device_model, 
                    'device_manufacturer': device_manufacturer,
                    'fingerprint_confidence': fingerprint_confidence,
                    'fingerprint_date': fingerprint_date
                })
            cursor.execute('SELECT id FROM devices WHERE mac_address = ?', (mac_address,))
            return cursor.fetchone()[0]
    
    def update_device(self, mac_address: str, ip_address: str = None, 
                     hostname: str = None, vendor: str = None, 
                     notes: str = None, never_fingerprint: bool = None) -> bool:
        """Update an existing device in the database.
        
        Args:
            mac_address: MAC address of the device
            ip_address: IP address of the device (if changed)
            hostname: Hostname of the device (if changed)
            vendor: Vendor/manufacturer of the device (if changed)
            notes: Device notes
            never_fingerprint: Whether to never fingerprint this device again
            
        Returns:
            bool: True if successful, False if device not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        current_time = int(time.time())
        
        # Build update query dynamically based on provided parameters
        update_fields = ['last_seen = ?']
        params = [current_time]
        
        if ip_address is not None:
            update_fields.append('ip_address = ?')
            params.append(ip_address)
        
        if hostname is not None:
            update_fields.append('hostname = ?')
            params.append(hostname)
        
        if vendor is not None:
            update_fields.append('vendor = ?')
            params.append(vendor)
            
        if notes is not None:
            update_fields.append('notes = ?')
            params.append(notes)
            
        if never_fingerprint is not None:
            update_fields.append('never_fingerprint = ?')
            params.append(never_fingerprint)
        
        params.append(mac_address)
        
        query = f'''
        UPDATE devices 
        SET {', '.join(update_fields)}
        WHERE mac_address = ?
        '''
        
        cursor.execute(query, params)
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.debug(f"Updated device: {mac_address}")
            return True
        else:
            logger.warning(f"Attempted to update non-existent device: {mac_address}")
            return False
            
    def update_device_metadata(self, mac_address: str, metadata: Dict[str, Any]) -> bool:
        """Update device metadata such as device type, model, manufacturer, etc.
        
        Args:
            mac_address: MAC address of the device
            metadata: Dictionary of metadata to update
            
        Returns:
            bool: True if successful, False if device not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Build update query dynamically based on provided metadata
        update_fields = []
        params = []
        
        valid_fields = [
            'device_type', 'device_model', 'device_manufacturer', 
            'fingerprint_confidence', 'fingerprint_date'
        ]
        
        for field, value in metadata.items():
            if field in valid_fields and value is not None:
                update_fields.append(f'{field} = ?')
                params.append(value)
        
        if not update_fields:
            logger.warning(f"No valid metadata fields to update for device: {mac_address}")
            return False
        
        params.append(mac_address)
        
        query = f'''
        UPDATE devices 
        SET {', '.join(update_fields)}
        WHERE mac_address = ?
        '''
        
        cursor.execute(query, params)
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.debug(f"Updated device metadata: {mac_address}")
            return True
        else:
            logger.warning(f"Attempted to update metadata for non-existent device: {mac_address}")
            return False
    
    def get_device(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Get device information by MAC address.
        
        Args:
            mac_address: MAC address of the device
            
        Returns:
            Dict containing device information or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices WHERE mac_address = ?', (mac_address,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get all devices in the database.
        
        Returns:
            List of dictionaries containing device information
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices ORDER BY last_seen DESC')
        return [dict(row) for row in cursor.fetchall()]
    
    def mark_device_important(self, mac_address: str, important: bool = True) -> bool:
        """Mark a device as important or not.
        
        Args:
            mac_address: MAC address of the device
            important: Whether the device is important
            
        Returns:
            bool: True if successful, False if device not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE devices 
        SET is_important = ?
        WHERE mac_address = ?
        ''', (important, mac_address))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"Marked device {mac_address} as {'important' if important else 'not important'}")
            return True
        else:
            logger.warning(f"Attempted to mark non-existent device as important: {mac_address}")
            return False
            
    def clear_device_fingerprint(self, mac_address: str) -> bool:
        """Clear the fingerprint data for a device.
        
        Args:
            mac_address: MAC address of the device
            
        Returns:
            bool: True if successful, False if device not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE devices 
        SET device_type = NULL,
            device_model = NULL,
            device_manufacturer = NULL,
            fingerprint_confidence = NULL,
            fingerprint_date = NULL
        WHERE mac_address = ?
        ''', (mac_address,))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"Cleared fingerprint data for device: {mac_address}")
            return True
        else:
            logger.warning(f"Attempted to clear fingerprint data for non-existent device: {mac_address}")
            return False
    
    # Event logging methods
    
    # Standard event types
    EVENT_DEVICE_DETECTED = "device_detected"
    EVENT_DEVICE_OFFLINE = "device_offline"
    EVENT_DEVICE_FINGERPRINTED = "device_fingerprinted"
    EVENT_ALERT = "alert"
    EVENT_SPEED_TEST = "speed_test"
    EVENT_WEBSITE_CHECK = "website_check"
    EVENT_SECURITY_SCAN = "security_scan"
    EVENT_SYSTEM = "system"

    def log_event(self, event_type: str, severity: str, message: str, 
                 details: str = None) -> int:
        """Log an event to the database.
        
        Args:
            event_type: Type of event (e.g., EVENT_DEVICE_DETECTED, EVENT_ALERT)
            severity: Severity level (e.g., 'info', 'warning', 'error')
            message: Event message
            details: Additional details (JSON or text)
            
        Returns:
            int: ID of the newly added event
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        current_time = int(time.time())
        
        cursor.execute('''
        INSERT INTO events (timestamp, event_type, severity, message, details)
        VALUES (?, ?, ?, ?, ?)
        ''', (current_time, event_type, severity, message, details))
        
        conn.commit()
        event_id = cursor.lastrowid
        
        # Use consistent logging format based on severity
        if severity == 'error':
            logger.error(f"Event [{event_type}]: {message}")
        elif severity == 'warning':
            logger.warning(f"Event [{event_type}]: {message}")
        else:
            logger.info(f"Event [{event_type}]: {message}")
            
        return event_id
    
    def get_recent_events(self, limit: int = 100,
                          event_type: str = None,
                          severity: str = None,
                          show_alerts: bool = False) -> List[Dict[str, Any]]:
        """Get recent events from the database.
        
        Args:
            limit: Maximum number of events to return
            event_type: Filter by event type (optional)
            severity: Filter by severity level (optional)
            show_alerts: If True, include ALERT events, otherwise filter them out (default: False)
            
        Returns:
            List of dictionaries containing event information
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM events'
        params = []
        
        where_clauses = []
        if event_type:
            where_clauses.append('event_type = ?')
            params.append(event_type)
        elif not show_alerts:
            # If not specifically requesting alerts and show_alerts is False, exclude alert events
            where_clauses.append('event_type != ?')
            params.append(self.EVENT_ALERT)
        
        if severity:
            where_clauses.append('severity = ?')
            params.append(severity)
        
        if where_clauses:
            query += ' WHERE ' + ' AND '.join(where_clauses)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # Speed test methods
    def add_speed_test(self, download_speed: Optional[float] = None, upload_speed: Optional[float] = None,
                       ping: Optional[float] = None, isp: str = "", server_name: str = "",
                       error: Optional[str] = None) -> int:
        """Add a new speed test result to the database.
        
        Args:
            download_speed: Download speed in Mbps (None if test failed)
            upload_speed: Upload speed in Mbps (None if test failed)
            ping: Ping latency in ms (None if test failed)
            isp: Internet Service Provider name
            server_name: Speed test server name
            error: Error message if the test failed
            
        Returns:
            int: ID of the newly added speed test
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        current_time = int(time.time())
        
        cursor.execute('''
        INSERT INTO speed_tests (timestamp, download_speed, upload_speed, ping, isp, server_name, error)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (current_time, download_speed, upload_speed, ping, isp, server_name, error))
        
        conn.commit()
        test_id = cursor.lastrowid
        
        if error:
            logger.warning(f"Added failed speed test result: {error}")
        else:
            # Only log speeds if they're not None
            download_str = f"{download_speed:.2f}" if download_speed is not None else "N/A"
            upload_str = f"{upload_speed:.2f}" if upload_speed is not None else "N/A"
            ping_str = f"{ping:.2f}" if ping is not None else "N/A"
            logger.info(f"Added speed test result: {download_str}/{upload_str} Mbps, {ping_str} ms")
            
        return test_id
        return test_id
    
    def get_recent_speed_tests(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent speed test results from the database.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of dictionaries containing speed test information
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM speed_tests
        ORDER BY timestamp DESC
        LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # Website monitoring methods
    
    def add_website_check(self, url: str, status_code: int = None, 
                         response_time: float = None, is_up: bool = False,
                         error_message: str = None) -> int:
        """Add a new website check result to the database.
        
        Args:
            url: Website URL
            status_code: HTTP status code
            response_time: Response time in seconds
            is_up: Whether the website is up
            error_message: Error message if any
            
        Returns:
            int: ID of the newly added website check
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        current_time = int(time.time())
        
        cursor.execute('''
        INSERT INTO website_checks (url, timestamp, status_code, response_time, is_up, error_message)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (url, current_time, status_code, response_time, is_up, error_message))
        
        conn.commit()
        check_id = cursor.lastrowid
        
        if is_up:
            logger.info(f"Website check: {url} is up (status: {status_code}, time: {response_time:.2f}s)")
        else:
            logger.warning(f"Website check: {url} is down ({error_message})")
            
        return check_id
    
    def get_website_checks(self, url: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get website check results from the database.
        
        Args:
            url: Filter by URL (optional)
            limit: Maximum number of results to return
            
        Returns:
            List of dictionaries containing website check information
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if url:
            cursor.execute('''
            SELECT * FROM website_checks
            WHERE url = ?
            ORDER BY timestamp DESC
            LIMIT ?
            ''', (url, limit))
        else:
            cursor.execute('''
            SELECT * FROM website_checks
            ORDER BY timestamp DESC
            LIMIT ?
            ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # Security scan methods
    
    def add_security_scan(self, device_id: int, open_ports: str, 
                         vulnerabilities: str = None) -> int:
        """Add a new security scan result to the database.
        
        Args:
            device_id: ID of the device
            open_ports: JSON string of open ports
            vulnerabilities: JSON string of vulnerabilities
            
        Returns:
            int: ID of the newly added security scan
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        current_time = int(time.time())
        
        cursor.execute('''
        INSERT INTO security_scans (device_id, timestamp, open_ports, vulnerabilities)
        VALUES (?, ?, ?, ?)
        ''', (device_id, current_time, open_ports, vulnerabilities))
        
        conn.commit()
        scan_id = cursor.lastrowid
        
        logger.info(f"Added security scan for device ID {device_id}")
        return scan_id
    
    def get_security_scans(self, device_id: int = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get security scan results from the database.
        
        Args:
            device_id: Filter by device ID (optional)
            limit: Maximum number of results to return
            
        Returns:
            List of dictionaries containing security scan information
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if device_id:
            cursor.execute('''
            SELECT * FROM security_scans
            WHERE device_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            ''', (device_id, limit))
        else:
            cursor.execute('''
            SELECT * FROM security_scans
            ORDER BY timestamp DESC
            LIMIT ?
            ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
        
    def clear_all_devices(self) -> int:
        """Delete all devices from the database.
        
        Returns:
            int: Number of devices deleted
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # First get count to report back how many were deleted
        cursor.execute('SELECT COUNT(*) FROM devices')
        count = cursor.fetchone()[0]
        
        # Delete all records from the devices table
        cursor.execute('DELETE FROM devices')
        
        # Also delete related security scans as they have foreign key constraints
        cursor.execute('DELETE FROM security_scans')
        
        # Clear all events
        cursor.execute('DELETE FROM events')
        
        # Clear speed tests
        cursor.execute('DELETE FROM speed_tests')
        
        # Clear website checks
        cursor.execute('DELETE FROM website_checks')
        
        conn.commit()
        
        logger.info(f"Cleared all {count} devices and all related data from the database")
        return count
        
    def remove_database(self) -> bool:
        """Completely remove the database file from the filesystem.
        
        This is more drastic than clear_all_devices() as it removes the entire database file
        rather than just clearing the data within it.
        
        Returns:
            bool: True if the database was successfully removed, False otherwise
        """
        # Close any existing connections
        self.close()
        
        try:
            # Check if the file exists before attempting to remove it
            if self.db_path.exists():
                # Remove the database file
                self.db_path.unlink()
                logger.warning(f"Database file completely removed: {self.db_path}")
                return True
            else:
                logger.warning(f"Database file does not exist: {self.db_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to remove database file: {e}")
            return False