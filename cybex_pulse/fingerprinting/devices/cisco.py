"""
Signature definitions for Cisco network devices.
"""

# Dictionary of device signatures for Cisco devices
SIGNATURES = {
    # Cisco Catalyst Switch
    'cisco_catalyst': {
        'device_type': 'Switch',
        'manufacturer': 'Cisco',
        'model': 'Catalyst',
        'mac_prefix': ['00:0A:41', '00:0B:45', '00:0C:86', '00:0D:65', '00:0E:38', '00:0F:23', 
                     '00:1A:A1', '00:1B:0C', '00:1C:57', '00:1D:A2', '70:81:05', 'F8:72:EA', 
                     '00:11:5C', '00:17:94', '7C:69:F6'],
        'open_ports': [22, 23, 80, 443, 161, 162, 514],
        'http_signature': {
            'Server': 'cisco.*',
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Cisco IOS.*Catalyst.*',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.9.*'
        }
    },
    
    # Cisco ISR Router
    'cisco_isr': {
        'device_type': 'Router',
        'manufacturer': 'Cisco',
        'model': 'ISR',
        'mac_prefix': ['00:0A:41', '00:0B:45', '00:0C:86', '00:0D:65', '00:0E:38', '00:0F:23', 
                     '00:1A:A1', '00:1B:0C', '00:1C:57', '00:1D:A2', '70:81:05', 'F8:72:EA'],
        'open_ports': [22, 23, 80, 443, 161, 162, 500, 514],
        'http_signature': {
            'Server': 'cisco.*',
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Cisco IOS.*ISR.*',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.9.*'
        }
    },
    
    # Cisco ASA Firewall
    'cisco_asa': {
        'device_type': 'Firewall',
        'manufacturer': 'Cisco',
        'model': 'ASA',
        'mac_prefix': ['00:0A:41', '00:0B:45', '00:0C:86', '00:0D:65', '00:1A:A1', '70:81:05', 'C4:7D:4F'],
        'open_ports': [22, 23, 80, 443, 161, 162, 443, 8443],
        'http_signature': {
            'Server': 'Adaptive Security Appliance.*',
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Cisco Adaptive Security Appliance.*',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.9.*'
        }
    },
    
    # Cisco Meraki Cloud Controller
    'cisco_meraki': {
        'device_type': 'Cloud Controller',
        'manufacturer': 'Cisco',
        'model': 'Meraki',
        'mac_prefix': ['0C:8D:DB', '34:56:FE', '88:15:44', 'E0:55:3D', '00:18:0A'],
        'open_ports': [80, 443, 8080, 8443],
        'http_signature': {
            'Server': 'nginx',
            'X-Meraki': '.*',
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Meraki.*',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.9.*'
        }
    },
    
    # Cisco Webex Device
    'cisco_webex': {
        'device_type': 'Conferencing',
        'manufacturer': 'Cisco',
        'model': 'Webex',
        'mac_prefix': ['00:21:A0', '64:EB:8C', 'BC:16:65', 'A0:F8:49'],
        'open_ports': [80, 443, 5060, 5061],
        'http_signature': {
            'Server': 'Cisco HTTP Server',
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Cisco Webex.*',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.9.*'
        }
    }
}