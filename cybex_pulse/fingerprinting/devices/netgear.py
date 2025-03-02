"""
Signature definitions for Netgear network devices.
"""

# Dictionary of device signatures for Netgear devices
SIGNATURES = {
    # Netgear Smart Managed Pro Switch
    'netgear_managed_switch': {
        'device_type': 'Switch',
        'manufacturer': 'Netgear',
        'model': 'Smart Managed Pro Switch',
        'mac_prefix': ['00:14:6C', '20:E5:2A', '28:80:88', '84:1B:5E', 'C4:3D:C7', '9C:3D:CF'],
        'open_ports': [22, 23, 80, 443, 161],
        'http_signature': {
            'Server': 'Netgear.*',
            'WWW-Authenticate': '.*NETGEAR.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*NETGEAR.*Switch.*',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.4526.*'
        }
    },
    
    # Netgear Nighthawk Router
    'netgear_nighthawk': {
        'device_type': 'Router',
        'manufacturer': 'Netgear',
        'model': 'Nighthawk',
        'mac_prefix': ['00:14:6C', '20:E5:2A', '28:80:88', '84:1B:5E', 'C4:3D:C7', '9C:3D:CF'],
        'open_ports': [80, 443, 5000],
        'http_signature': {
            'Server': 'Netgear.*',
            'WWW-Authenticate': '.*NETGEAR.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*NETGEAR.*Nighthawk.*',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.4526.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'NETGEAR.*'
        }
    },
    
    # Netgear Orbi Mesh System
    'netgear_orbi': {
        'device_type': 'Router',
        'manufacturer': 'Netgear',
        'model': 'Orbi',
        'mac_prefix': ['00:14:6C', '20:E5:2A', '28:80:88', '9C:3D:CF', 'B0:B9:8A'],
        'open_ports': [80, 443],
        'http_signature': {
            'Server': 'Netgear.*',
            'WWW-Authenticate': '.*Orbi.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*NETGEAR.*Orbi.*',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.4526.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'Orbi.*'
        }
    },
    
    # Netgear ReadyNAS
    'netgear_readynas': {
        'device_type': 'NAS',
        'manufacturer': 'Netgear',
        'model': 'ReadyNAS',
        'mac_prefix': ['00:14:6C', '20:E5:2A', '28:80:88', '9C:3D:CF'],
        'open_ports': [22, 80, 443, 445, 139, 111, 2049, 3689],
        'http_signature': {
            'Server': 'Apache.*',
            'X-Frame-Options': 'SAMEORIGIN'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*ReadyNAS.*',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.4526.*'
        },
        'mdns_signature': {
            'service_type': '_afpovertcp._tcp',
            'service_name': 'ReadyNAS.*'
        }
    }
}