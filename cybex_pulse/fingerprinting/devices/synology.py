"""
Signature definitions for Synology NAS devices.
"""

# Dictionary of device signatures for Synology devices
SIGNATURES = {
    # Synology DiskStation (General)
    'synology_diskstation': {
        'device_type': 'NAS',
        'manufacturer': 'Synology',
        'model': 'DiskStation',
        'mac_prefix': ['00:11:32', '00:24:8D', '28:C6:8E', '90:FB:5B', 'BC:EE:7B', '00:C0:A8'],
        'open_ports': [22, 80, 443, 5000, 5001, 5005, 5006, 139, 445, 111, 2049],
        'http_signature': {
            'Server': 'nginx',
            'X-Powered-By': 'PHP.*',
            'Set-Cookie': '.*id=.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Synology.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Synology.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': '.*DiskStation.*'
        }
    },
    
    # Synology DS220+
    'synology_ds220plus': {
        'device_type': 'NAS',
        'manufacturer': 'Synology',
        'model': 'DS220+',
        'mac_prefix': ['00:11:32', '00:24:8D', '28:C6:8E', '90:FB:5B', 'BC:EE:7B', '00:C0:A8'],
        'open_ports': [22, 80, 443, 5000, 5001, 139, 445, 111, 2049],
        'http_signature': {
            'Server': 'nginx',
            'X-Powered-By': 'PHP.*',
            'Set-Cookie': '.*id=.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*DS220\\+.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Synology.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': '.*DS220\\+.*'
        }
    },
    
    # Synology DS920+
    'synology_ds920plus': {
        'device_type': 'NAS',
        'manufacturer': 'Synology',
        'model': 'DS920+',
        'mac_prefix': ['00:11:32', '00:24:8D', '28:C6:8E', '90:FB:5B', 'BC:EE:7B', '00:C0:A8'],
        'open_ports': [22, 80, 443, 5000, 5001, 139, 445, 111, 2049],
        'http_signature': {
            'Server': 'nginx',
            'X-Powered-By': 'PHP.*',
            'Set-Cookie': '.*id=.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*DS920\\+.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Synology.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': '.*DS920\\+.*'
        }
    },
    
    # Synology RS1221+
    'synology_rs1221plus': {
        'device_type': 'NAS',
        'manufacturer': 'Synology',
        'model': 'RS1221+',
        'mac_prefix': ['00:11:32', '00:24:8D', '28:C6:8E', '90:FB:5B', 'BC:EE:7B', '00:C0:A8'],
        'open_ports': [22, 80, 443, 5000, 5001, 139, 445, 111, 2049],
        'http_signature': {
            'Server': 'nginx',
            'X-Powered-By': 'PHP.*',
            'Set-Cookie': '.*id=.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*RS1221\\+.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Synology.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': '.*RS1221\\+.*'
        }
    },
    
    # Synology RT6600ax Router
    'synology_rt6600ax': {
        'device_type': 'Router',
        'manufacturer': 'Synology',
        'model': 'RT6600ax',
        'mac_prefix': ['00:11:32', '00:24:8D', '28:C6:8E', '90:FB:5B', 'BC:EE:7B', '00:C0:A8'],
        'open_ports': [22, 80, 443],
        'http_signature': {
            'Server': 'nginx',
            'X-Powered-By': 'PHP.*',
            'Set-Cookie': '.*id=.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*RT6600ax.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Synology.*'
        }
    }
}