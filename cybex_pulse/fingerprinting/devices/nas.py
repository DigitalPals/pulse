"""
Signature definitions for NAS (Network Attached Storage) devices.
"""

# Dictionary of device signatures for NAS devices
SIGNATURES = {
    # QNAP NAS
    'qnap_nas': {
        'device_type': 'NAS',
        'manufacturer': 'QNAP',
        'model': 'NAS',
        'mac_prefix': ['00:08:9B', '00:1F:1F', '24:5E:BE', '00:17:31', 'EC:A0:FB'],
        'open_ports': [22, 80, 443, 139, 445, 111, 2049, 8080, 6000, 10000],
        'http_signature': {
            'Server': 'http.*',
            'X-Powered-By': 'QTS.*',
            'Set-Cookie': '.*NASID.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*QNAP.*',
            'SNMPv2-MIB::sysObjectID.0': '.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'QNAP.*'
        },
        'hostname_patterns': [
            '.*qnap.*', '.*nas.*'
        ]
    },
    
    # TrueNAS
    'truenas': {
        'device_type': 'NAS',
        'manufacturer': 'iXsystems',
        'model': 'TrueNAS',
        'mac_prefix': [],  # No specific MAC prefix as it's software that runs on various hardware
        'open_ports': [22, 80, 443, 139, 445, 111, 2049, 9000],
        'http_signature': {
            'Server': 'nginx',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Powered-By': '.*freenas.*|.*truenas.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*TrueNAS.*|.*FreeNAS.*',
            'SNMPv2-MIB::sysObjectID.0': '.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'TrueNAS.*|FreeNAS.*'
        },
        'hostname_patterns': [
            '.*truenas.*', '.*freenas.*', '.*nas.*'
        ]
    },
    
    # Unraid
    'unraid': {
        'device_type': 'NAS',
        'manufacturer': 'Lime Technology',
        'model': 'Unraid',
        'mac_prefix': [],  # No specific MAC prefix as it's software that runs on various hardware
        'open_ports': [22, 80, 443, 139, 445, 111, 2049, 8080],
        'http_signature': {
            'Server': 'nginx',
            'X-Frame-Options': 'SAMEORIGIN',
            'Set-Cookie': '.*unraid.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Unraid.*',
            'SNMPv2-MIB::sysObjectID.0': '.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'Unraid.*'
        },
        'hostname_patterns': [
            '.*unraid.*', '.*tower.*', '.*server.*'
        ],
        # Add more specific login page indicators for Unraid
        'content_indicators': [
            'unraid webgui',
            'please enable cookies to use the unraid',
            'go to my servers dashboard',
            'password recovery'
        ]
    },
    
    # Western Digital MyCloud
    'wd_mycloud': {
        'device_type': 'NAS',
        'manufacturer': 'Western Digital',
        'model': 'MyCloud',
        'mac_prefix': ['00:90:A9', '00:15:B7', '00:24:FD', '00:1A:B1', 'C8:DE:C9'],
        'open_ports': [22, 80, 443, 139, 445, 111, 2049, 9000],
        'http_signature': {
            'Server': 'nginx|Apache',
            'WWW-Authenticate': '.*WD.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*WD.*MyCloud.*',
            'SNMPv2-MIB::sysObjectID.0': '.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': '.*MyCloud.*'
        },
        'hostname_patterns': [
            '.*mycloud.*', '.*wd.*', '.*western.*'
        ]
    },
    
    # Synology NAS
    'synology_nas': {
        'device_type': 'NAS',
        'manufacturer': 'Synology',
        'model': 'DiskStation',
        'mac_prefix': ['00:11:32', '00:24:8C', '00:C0:50', '90:09:D4', 'BC:EE:7B'],
        'open_ports': [22, 80, 443, 139, 445, 111, 2049, 5000, 5001, 5005, 5006],
        'http_signature': {
            'Server': 'nginx',
            'X-Powered-By': 'PHP.*',
            'X-DSM-Version': '.*',
            'Set-Cookie': '.*dsm_session.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Synology.*',
            'SNMPv2-MIB::sysObjectID.0': '.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': '.*DiskStation.*|.*RS[0-9]+.*'
        },
        'hostname_patterns': [
            '.*synology.*', '.*diskstation.*', '.*ds[0-9]+.*', '.*rs[0-9]+.*'
        ]
    },
    
    # ASUSTOR NAS
    'asustor_nas': {
        'device_type': 'NAS',
        'manufacturer': 'ASUSTOR',
        'model': 'NAS',
        'mac_prefix': ['00:08:9B', 'E4:E0:C5'],
        'open_ports': [22, 80, 443, 139, 445, 2049, 8000, 8001],
        'http_signature': {
            'Server': 'nginx',
            'Set-Cookie': '.*ASUSWEBSTORAGE.*'
        },
        'hostname_patterns': [
            '.*asustor.*', '.*as[0-9]+.*'
        ]
    },
    
    # TerraMaster NAS
    'terramaster_nas': {
        'device_type': 'NAS',
        'manufacturer': 'TerraMaster',
        'model': 'NAS',
        'mac_prefix': [],
        'open_ports': [22, 80, 443, 139, 445, 2049, 8181],
        'http_signature': {
            'Server': 'TOS.*'
        },
        'hostname_patterns': [
            '.*terramaster.*', '.*tnas.*', '.*f[0-9]+.*'
        ]
    }
}