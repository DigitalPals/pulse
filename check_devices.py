#!/usr/bin/env python3
import sqlite3
from pathlib import Path

# Path to the database file
db_path = Path.home() / ".cybex_pulse" / "cybex_pulse.db"

print(f"Looking for database at: {db_path}")
print(f"File exists: {db_path.exists()}")

if not db_path.exists():
    print("Database file not found!")
    exit(1)

# Connect to the database
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print("Successfully connected to database")
except Exception as e:
    print(f"Error connecting to database: {e}")
    exit(1)

# Check if devices table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
if not cursor.fetchone():
    print("Devices table does not exist in the database!")
    exit(1)

# Count devices in the database
cursor.execute("SELECT COUNT(*) FROM devices")
device_count = cursor.fetchone()[0]
print(f"\nFound {device_count} devices in the database")

# List devices if any exist
if device_count > 0:
    print("\nDevices in database:")
    cursor.execute("SELECT id, mac_address, ip_address, hostname, vendor FROM devices")
    devices = cursor.fetchall()
    for device in devices:
        device_id, mac, ip, hostname, vendor = device
        print(f"ID: {device_id}, MAC: {mac}, IP: {ip}, Hostname: {hostname}, Vendor: {vendor}")
else:
    print("\nNo devices found in the database.")
    print("The security scanning thread won't have anything to scan.")
    print("Wait for the network scanner to discover devices first.")

# Check if any security scans have been performed
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='security_scans'")
if not cursor.fetchone():
    print("\nSecurity scans table does not exist in the database!")
else:
    cursor.execute("SELECT COUNT(*) FROM security_scans")
    scan_count = cursor.fetchone()[0]
    print(f"\nFound {scan_count} security scans in the database")
    
    if scan_count > 0:
        print("\nRecent security scans:")
        cursor.execute("SELECT device_id, timestamp, open_ports FROM security_scans ORDER BY timestamp DESC LIMIT 5")
        scans = cursor.fetchall()
        for scan in scans:
            device_id, timestamp, open_ports = scan
            print(f"Device ID: {device_id}, Timestamp: {timestamp}, Open Ports: {open_ports}")

# Close the connection
conn.close()