"""
Signature definitions for additional network equipment.
"""

# Dictionary of device signatures for network devices
SIGNATURES = {
    # MikroTik RouterOS
    'mikrotik_router': {
        'device_type': 'Router',
        'manufacturer': 'MikroTik',
        'model': 'RouterOS',
        'mac_prefix': ['4C:5E:0C', '64:D1:54', 'B8:69:F4', 'E4:8D:8C', '2C:C8:1B', 'CC:2D:E0', 'DC:2C:6E'],
        'open_ports': [22, 23, 80, 443, 8291, 8728, 8729],
        'http_signature': {
            'Server': 'MikroTik.*',
            'WWW-Authenticate': '.*MikroTik.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*RouterOS.*',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.14988.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'MikroTik.*'
        }
    },
    
    # MikroTik Switch
    'mikrotik_switch': {
        'device_type': 'Switch',
        'manufacturer': 'MikroTik',
        'model': 'CRS Switch',
        'mac_prefix': ['4C:5E:0C', '64:D1:54', 'B8:69:F4', 'E4:8D:8C', '2C:C8:1B', 'CC:2D:E0', 'DC:2C:6E'],
        'open_ports': [22, 23, 80, 443, 8291, 8728, 8729],
        'http_signature': {
            'Server': 'MikroTik.*',
            'WWW-Authenticate': '.*MikroTik.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*SwOS.*|.*CRS.*',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.14988.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'MikroTik.*'
        }
    },
    
    # Aruba Access Point
    'aruba_ap': {
        'device_type': 'Access Point',
        'manufacturer': 'Aruba',
        'model': 'Access Point',
        'mac_prefix': ['00:0B:86', '00:1A:1E', '04:BD:88', '24:DE:C6', '94:B4:0F', 'D8:C7:C8', 'AC:A3:1E'],
        'open_ports': [22, 80, 443],
        'http_signature': {
            'Server': 'Aruba.*',
            'WWW-Authenticate': '.*Aruba.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Aruba.*',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.14823.*'
        },
        'mdns_signature': {
            'service_type': '_airwave-discovery._tcp',
            'service_name': 'Aruba.*'
        }
    },
    
    # Aruba Switch
    'aruba_switch': {
        'device_type': 'Switch',
        'manufacturer': 'Aruba',
        'model': 'Switch',
        'mac_prefix': ['00:0B:86', '00:1A:1E', '04:BD:88', '24:DE:C6', '94:B4:0F', 'D8:C7:C8', 'AC:A3:1E'],
        'open_ports': [22, 23, 80, 443, 161, 162],
        'http_signature': {
            'Server': 'Aruba.*',
            'WWW-Authenticate': '.*Aruba.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Aruba.*Switch.*',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.14823.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'Aruba.*'
        }
    },
    
    # Aruba Instant On
    'aruba_instant_on': {
        'device_type': 'Access Point',
        'manufacturer': 'Aruba',
        'model': 'Instant On',
        'mac_prefix': ['00:0B:86', '00:1A:1E', '04:BD:88', '24:DE:C6', '94:B4:0F', 'D8:C7:C8', 'AC:A3:1E'],
        'open_ports': [80, 443, 8080, 8082],
        'http_signature': {
            'Server': 'Aruba.*Instant.*On.*',
            'WWW-Authenticate': '.*Aruba.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Aruba.*Instant.*On.*',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.14823.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': '.*Instant.*On.*'
        }
    }
}