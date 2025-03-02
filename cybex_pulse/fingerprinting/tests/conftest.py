"""
Test fixtures for device fingerprinting tests.
"""
import pytest
from typing import Dict, List, Any


@pytest.fixture
def unifi_udm_device_data() -> Dict[str, Any]:
    """Mock device data for a UniFi Dream Machine."""
    return {
        'ip_address': '192.168.1.1',
        'mac_address': 'B4:FB:E4:5A:11:22',
        'open_ports': [22, 80, 443, 8080, 8443, 8880, 8843, 6789, 161],
        'http_headers': {
            'Server': 'UniFi Dream Machine',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'Content-Type': 'text/html',
            'Connection': 'keep-alive'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'UniFi Dream Machine Pro v1.0.4',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.41112',
            'SNMPv2-MIB::sysUpTime.0': '123456',
            'SNMPv2-MIB::sysName.0': 'UDM-Pro'
        },
        'mdns_data': {}
    }


@pytest.fixture
def synology_nas_device_data() -> Dict[str, Any]:
    """Mock device data for a Synology NAS."""
    return {
        'ip_address': '192.168.1.2',
        'mac_address': '00:11:32:AA:BB:CC',
        'open_ports': [22, 80, 443, 5000, 5001, 139, 445, 111, 2049],
        'http_headers': {
            'Server': 'nginx',
            'X-Powered-By': 'PHP/7.3.19',
            'Set-Cookie': 'id=123456789',
            'Content-Type': 'text/html; charset=UTF-8',
            'Connection': 'keep-alive'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'Linux DS920+ 4.4.59+ #42962 SMP PREEMPT',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.8072.3.2.10',
            'SNMPv2-MIB::sysName.0': 'DS920+'
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'DS920+'
        }
    }


@pytest.fixture
def shelly_plug_device_data() -> Dict[str, Any]:
    """Mock device data for a Shelly smart plug."""
    return {
        'ip_address': '192.168.1.3',
        'mac_address': 'C4:5B:BE:11:22:33',
        'open_ports': [80],
        'http_headers': {
            'Server': 'Mongoose/6.15',
            'Content-Type': 'application/json',
            'Connection': 'close'
        },
        'snmp_data': {},
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'shelly-plug-s-1122'
        }
    }


@pytest.fixture
def roku_device_data() -> Dict[str, Any]:
    """Mock device data for a Roku streaming device."""
    return {
        'ip_address': '192.168.1.4',
        'mac_address': 'B0:A7:37:9A:8B:7C',
        'open_ports': [80, 8060, 1900],
        'http_headers': {
            'Server': 'Roku UPnP/1.0',
            'Connection': 'close',
            'Content-Type': 'text/html'
        },
        'snmp_data': {},
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'Roku Streaming Stick'
        }
    }


@pytest.fixture
def printer_device_data() -> Dict[str, Any]:
    """Mock device data for an HP printer."""
    return {
        'ip_address': '192.168.1.5',
        'mac_address': '00:18:71:FD:EC:BA',
        'open_ports': [80, 443, 515, 631, 9100],
        'http_headers': {
            'Server': 'HP-ChaiSOE/1.0',
            'Connection': 'keep-alive',
            'Content-Type': 'text/html'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'HP LaserJet Pro MFP M428fdw',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.11'
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'HP LaserJet Pro MFP M428fdw'
        }
    }


@pytest.fixture
def unknown_device_data() -> Dict[str, Any]:
    """Mock device data for an unknown device."""
    return {
        'ip_address': '192.168.1.6',
        'mac_address': '00:01:02:03:04:05',
        'open_ports': [22, 80],
        'http_headers': {
            'Server': 'nginx',
            'Connection': 'keep-alive',
            'Content-Type': 'text/html'
        },
        'snmp_data': {},
        'mdns_data': {}
    }


@pytest.fixture
def similar_device_data() -> Dict[str, Any]:
    """
    Mock device data for a device with similar characteristics to multiple devices.
    This could be mistaken for different devices.
    """
    return {
        'ip_address': '192.168.1.7',
        'mac_address': '00:26:AB:11:22:33',  # Epson MAC prefix
        'open_ports': [80, 443, 22],  # Common ports for many devices
        'http_headers': {
            'Server': 'nginx',  # Common server
            'Connection': 'keep-alive',
            'Content-Type': 'text/html'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'EPSON Built-in',  # Has Epson string
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.1248'
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'EPSON-DEVICE'  # Has Epson string
        }
    }