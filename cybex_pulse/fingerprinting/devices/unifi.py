"""
Signature definitions for Ubiquiti UniFi devices.
Enhanced with multiple detection methods to improve identification accuracy.
"""

# Ubiquiti MAC address OUI prefixes (first 3 bytes)
UBIQUITI_MAC_PREFIXES = [
    '00:15:6D',  # Ubiquiti Networks Inc.
    '00:27:22',  # Ubiquiti Networks Inc.
    '04:18:D6',  # Ubiquiti Networks Inc.
    '0C:80:63',  # Ubiquiti Networks Inc.
    '13:22:33',  # Ubiquiti Networks Inc.
    '18:E8:29',  # Ubiquiti Networks Inc.
    '24:5A:4C',  # Ubiquiti Networks Inc.
    '24:A4:3C',  # Ubiquiti Networks Inc.
    '28:24:FF',  # Ubiquiti Networks Inc.
    '30:B5:C2',  # Ubiquiti Networks Inc.
    '44:D9:E7',  # Ubiquiti Networks Inc.
    '58:D5:6E',  # Ubiquiti Networks Inc.
    '60:22:32',  # Ubiquiti Networks Inc.
    '60:E3:27',  # Ubiquiti Networks Inc.
    '68:72:51',  # Ubiquiti Networks Inc.
    '70:A7:41',  # Ubiquiti Networks Inc.
    '74:83:C2',  # Ubiquiti Networks Inc.
    '78:8A:20',  # Ubiquiti Networks Inc.
    '80:2A:A8',  # Ubiquiti Networks Inc.
    '94:9A:A9',  # Ubiquiti Networks Inc.
    '98:DA:C4',  # Ubiquiti Networks Inc.
    '9C:05:D6',  # Ubiquiti Networks Inc.
    'B4:FB:E4',  # Ubiquiti Networks Inc.
    'D8:0F:99',  # Ubiquiti Networks Inc.
    'DC:9F:DB',  # Ubiquiti Networks Inc.
    'E0:63:DA',  # Ubiquiti Networks Inc.
    'F0:9F:C2',  # Ubiquiti Networks Inc.
    'FC:EC:DA',  # Ubiquiti Networks Inc.
]

# Common ports used by Unifi devices
COMMON_UNIFI_PORTS = [
    22,     # SSH
    80,     # HTTP
    443,    # HTTPS 
    8080,   # HTTP management
    8443,   # HTTPS management 
    8880,   # HTTP portal redirect
    8843,   # HTTPS controller redirect
    6789,   # Mobile speed test
    3478,   # STUN service
    5514,   # Remote syslog capture
    27117,  # MongoDB service
    1900,   # UPnP
    161,    # SNMP
]

# Dream Machine Pro/Max/SE specific management paths
UDM_MANAGEMENT_PATHS = [
    '/manage',
    '/network',
    '/login',
    '/api/auth/login',
]

# Dictionary of device signatures for UniFi devices
SIGNATURES = {
    # UniFi Dream Machine
    'unifi_udm': {
        'device_type': 'Router',
        'manufacturer': 'Ubiquiti',
        'model': 'UniFi Dream Machine',
        'mac_prefix': UBIQUITI_MAC_PREFIXES,
        'open_ports': [22, 80, 443, 8080, 8443, 8880, 8843, 6789, 161],
        'http_signature': {
            'Server': 'UniFi.*',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'User-Agent': '.*UniFi Dream Machine.*',
            'X-Content-Contains-UniFi': 'true'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*UniFi.*Dream Machine.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Ubiquiti.*'
        },
        'hostname_patterns': [
            '.*udm.*',
            '.*dream.*machine.*',
            '.*ubnt.*',
            '.*unifi.*'
        ]
    },
    
    # UniFi Dream Machine Pro
    'unifi_udm_pro': {
        'device_type': 'Router',
        'manufacturer': 'Ubiquiti',
        'model': 'UniFi Dream Machine Pro',
        'mac_prefix': UBIQUITI_MAC_PREFIXES,
        'open_ports': [22, 80, 443, 8080, 8443, 8880, 8843, 6789, 161, 1900],
        'http_signature': {
            'Server': 'UniFi.*',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'User-Agent': '.*UDM.?Pro.*',
            'X-Content-Contains-UniFi': 'true'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*UniFi.*Dream Machine Pro.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Ubiquiti.*'
        },
        'hostname_patterns': [
            '.*udm.*pro.*',
            '.*dream.*machine.*pro.*',
            '.*ubnt.*',
            '.*unifi.*pro.*'
        ]
    },
    
    # UniFi Dream Machine Pro Max
    'unifi_udm_pro_max': {
        'device_type': 'Router',
        'manufacturer': 'Ubiquiti',
        'model': 'UniFi Dream Machine Pro Max',
        'mac_prefix': UBIQUITI_MAC_PREFIXES,
        'open_ports': [22, 80, 443, 8080, 8443, 8880, 8843, 6789, 161, 1900],
        'http_signature': {
            'Server': 'UniFi.*',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'User-Agent': '.*UDM.?Pro.?Max.*',
            'X-Content-Contains-UniFi': 'true',
            'X-Content-Contains-Model': '.*(UDM-Pro-Max|UDMPMAX).*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*UniFi.*Dream Machine Pro Max.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Ubiquiti.*'
        },
        'hostname_patterns': [
            '.*udm.*pro.*max.*',
            '.*dream.*machine.*pro.*max.*',
            '.*ubnt.*',
            '.*unifi.*pro.*max.*',
            '.*UDM-Pro-Max.*',
            '.*UDMPMAX.*'
        ]
    },
    
    # UniFi Dream Machine Special Edition
    'unifi_udm_se': {
        'device_type': 'Router',
        'manufacturer': 'Ubiquiti',
        'model': 'UniFi Dream Machine SE',
        'mac_prefix': UBIQUITI_MAC_PREFIXES,
        'open_ports': [22, 80, 443, 8080, 8443, 8880, 8843, 6789, 161, 1900],
        'http_signature': {
            'Server': 'UniFi.*',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'User-Agent': '.*UDM.?SE.*',
            'X-Content-Contains-UniFi': 'true',
            'X-Content-Contains-Model': '.*UDM-SE.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*UniFi.*Dream Machine SE.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Ubiquiti.*'
        },
        'hostname_patterns': [
            '.*udm.*se.*',
            '.*dream.*machine.*se.*',
            '.*ubnt.*',
            '.*unifi.*se.*',
            '.*UDM-SE.*'
        ]
    },
    
    # UniFi Security Gateway
    'unifi_usg': {
        'device_type': 'Router',
        'manufacturer': 'Ubiquiti',
        'model': 'UniFi Security Gateway',
        'mac_prefix': UBIQUITI_MAC_PREFIXES,
        'open_ports': [22, 80, 443, 8080, 8443],
        'http_signature': {
            'Server': 'lighttpd',
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*USG.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Ubiquiti.*'
        },
        'hostname_patterns': [
            '.*usg.*',
            '.*security.*gateway.*',
            '.*unifi.*gateway.*',
            '.*ubnt.*'
        ]
    },
    
    # UniFi Switch
    'unifi_switch': {
        'device_type': 'Switch',
        'manufacturer': 'Ubiquiti',
        'model': 'UniFi Switch',
        'mac_prefix': UBIQUITI_MAC_PREFIXES,
        'open_ports': [22, 80, 443, 161],
        'http_signature': {
            'Server': 'UniFi.*',
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*UniFi.*Switch.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Ubiquiti.*'
        },
        'hostname_patterns': [
            '.*unifi.*switch.*',
            '.*usw.*',
            '.*ubnt.*switch.*'
        ]
    },
    
    # UniFi Access Point
    'unifi_ap': {
        'device_type': 'Access Point',
        'manufacturer': 'Ubiquiti',
        'model': 'UniFi Access Point',
        'mac_prefix': UBIQUITI_MAC_PREFIXES,
        'open_ports': [22, 80, 443],
        'http_signature': {
            'Server': 'UniFi.*',
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*UniFi.*UAP.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Ubiquiti.*'
        },
        'mdns_signature': {
            'service_type': '_ubnt._tcp',
            'service_name': 'UAP.*'
        },
        'hostname_patterns': [
            '.*uap.*',
            '.*unifi.*ap.*',
            '.*access.*point.*',
            '.*ubnt.*ap.*'
        ]
    },
    
    # UniFi Cloud Key
    'unifi_cloudkey': {
        'device_type': 'Controller',
        'manufacturer': 'Ubiquiti',
        'model': 'UniFi Cloud Key',
        'mac_prefix': UBIQUITI_MAC_PREFIXES,
        'open_ports': [22, 80, 443, 8080, 8443, 8880, 8843],
        'http_signature': {
            'Server': 'UniFi.*',
            'X-Frame-Options': 'SAMEORIGIN',
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*UniFi.*Cloud Key.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Ubiquiti.*'
        },
        'hostname_patterns': [
            '.*cloud.*key.*',
            '.*uck.*',
            '.*unifi.*key.*',
            '.*ubnt.*key.*'
        ]
    }
}