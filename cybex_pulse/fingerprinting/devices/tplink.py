"""
Signature definitions for TP-Link network devices.
"""

# Dictionary of device signatures for TP-Link devices
SIGNATURES = {
    # TP-Link Archer Router
    'tplink_archer': {
        'device_type': 'Router',
        'manufacturer': 'TP-Link',
        'model': 'Archer',
        'mac_prefix': ['14:CC:20', '14:CF:E2', '18:A6:F7', '1C:3B:F3', '1C:61:B4', '1C:FA:68', 
                     '54:C8:0F', '60:E3:27', '64:56:01', '90:F6:52', '94:D9:B3', 'BC:46:99'],
        'open_ports': [80, 443],
        'http_signature': {
            'Server': 'TP-LINK.*',
            'WWW-Authenticate': 'Basic realm="TP-LINK.*"'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*TP-LINK.*Archer.*',
            'SNMPv2-MIB::sysObjectID.0': '.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'TP-LINK.*'
        }
    },
    
    # TP-Link Deco Mesh System
    'tplink_deco': {
        'device_type': 'Router',
        'manufacturer': 'TP-Link',
        'model': 'Deco',
        'mac_prefix': ['14:CC:20', '14:CF:E2', '18:A6:F7', '1C:3B:F3', '1C:61:B4', '1C:FA:68',
                     '54:C8:0F', '60:E3:27', '90:F6:52'],
        'open_ports': [80, 443, 8080],
        'http_signature': {
            'Server': 'TP-LINK.*',
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*TP-LINK.*Deco.*',
            'SNMPv2-MIB::sysObjectID.0': '.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': '.*Deco.*'
        }
    },
    
    # TP-Link Smart Switch
    'tplink_switch': {
        'device_type': 'Switch',
        'manufacturer': 'TP-Link',
        'model': 'Smart Switch',
        'mac_prefix': ['14:CC:20', '14:CF:E2', '18:A6:F7', '1C:3B:F3', '1C:61:B4', '1C:FA:68',
                     '54:C8:0F', '60:E3:27', '64:56:01', '90:F6:52', '94:D9:B3'],
        'open_ports': [22, 23, 80, 443, 161],
        'http_signature': {
            'Server': 'TP-LINK.*',
            'WWW-Authenticate': 'Basic realm="TP-LINK.*"'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*TP-LINK.*Switch.*',
            'SNMPv2-MIB::sysObjectID.0': '.*'
        }
    },
    
    # TP-Link EAP Access Point
    'tplink_eap': {
        'device_type': 'Access Point',
        'manufacturer': 'TP-Link',
        'model': 'EAP',
        'mac_prefix': ['14:CC:20', '14:CF:E2', '18:A6:F7', '1C:3B:F3', '1C:61:B4', '1C:FA:68',
                     '54:C8:0F', '60:E3:27', '64:56:01', '90:F6:52', '94:D9:B3'],
        'open_ports': [22, 80, 443, 8043],
        'http_signature': {
            'Server': 'TP-LINK.*EAP.*',
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*TP-LINK.*EAP.*',
            'SNMPv2-MIB::sysObjectID.0': '.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': '.*EAP.*'
        }
    },
    
    # TP-Link Kasa Smart Device
    'tplink_kasa': {
        'device_type': 'Smart Home',
        'manufacturer': 'TP-Link',
        'model': 'Kasa',
        'mac_prefix': ['14:CC:20', '14:CF:E2', '18:A6:F7', '1C:3B:F3', '1C:61:B4', '1C:FA:68',
                     '54:C8:0F', '60:E3:27', '90:F6:52', '50:C7:BF', 'A8:57:4E'],
        'open_ports': [80, 9999],
        'http_signature': {
            'Server': 'TP-LINK.*Kasa.*',
        },
        'snmp_signature': {},
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': '.*Kasa.*'
        }
    }
}