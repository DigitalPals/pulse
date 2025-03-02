"""
Signature definitions for Printer devices.
"""

# Dictionary of device signatures for Printer devices
SIGNATURES = {
    # HP LaserJet
    'hp_laserjet': {
        'device_type': 'Printer',
        'manufacturer': 'HP',
        'model': 'LaserJet',
        'mac_prefix': ['00:05:9B', '00:0F:EA', '00:12:79', '00:18:71', '00:1C:C4', '00:23:9C', '00:25:B3', '00:26:55'],
        'open_ports': [80, 443, 515, 631, 9100],
        'http_signature': {
            'Server': 'HP-ChaiSOE.*',
            'Server': 'HP HTTP Server.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*HP LaserJet.*',
            'SNMPv2-MIB::sysObjectID.0': '.*HP.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'HP LaserJet.*'
        }
    },
    
    # HP OfficeJet
    'hp_officejet': {
        'device_type': 'Printer',
        'manufacturer': 'HP',
        'model': 'OfficeJet',
        'mac_prefix': ['00:05:9B', '00:0F:EA', '00:12:79', '00:18:71', '00:1C:C4', '00:1E:0B', '00:21:F7', '00:25:B3'],
        'open_ports': [80, 443, 515, 631, 9100],
        'http_signature': {
            'Server': 'HP-ChaiSOE.*',
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*HP Officejet.*',
            'SNMPv2-MIB::sysObjectID.0': '.*HP.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'HP OfficeJet.*'
        }
    },
    
    # Brother Printer
    'brother_printer': {
        'device_type': 'Printer',
        'manufacturer': 'Brother',
        'model': 'Printer',
        'mac_prefix': ['00:1B:A9', '00:80:77', '00:15:99', '00:17:61', '30:05:5C', '3C:2A:F4', '4C:9E:E4', '54:EE:75', '78:FD:94'],
        'open_ports': [80, 443, 515, 631, 9100],
        'http_signature': {
            'Server': 'IcHttpd.*',
            'Server': 'Brother.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Brother.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Brother.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'Brother.*'
        }
    },
    
    # Canon Printer
    'canon_printer': {
        'device_type': 'Printer',
        'manufacturer': 'Canon',
        'model': 'Printer',
        'mac_prefix': ['00:00:85', '00:10:79', '00:10:E0', '00:1E:8F', '00:24:BF', '00:30:C1', '00:D3:E0', '08:00:37'],
        'open_ports': [80, 443, 515, 631, 9100],
        'http_signature': {
            'Server': 'KS_HTTP.*',
            'Server': 'CANON HTTP Server.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Canon.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Canon.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'Canon.*'
        }
    },
    
    # Epson Printer
    'epson_printer': {
        'device_type': 'Printer',
        'manufacturer': 'Epson',
        'model': 'Printer',
        'mac_prefix': ['00:26:AB', '00:26:BB', '08:00:83', '00:00:48', '00:13:7A', '00:80:77', '44:D2:44', '8C:CF:5C', 'A4:E7:E4'],
        'open_ports': [80, 443, 515, 631, 9100],
        'http_signature': {
            'Server': 'EPSON.*',
            'Server': 'EPSON_Linux.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*EPSON.*',
            'SNMPv2-MIB::sysObjectID.0': '.*EPSON.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'EPSON.*'
        }
    },
    
    # Lexmark Printer
    'lexmark_printer': {
        'device_type': 'Printer',
        'manufacturer': 'Lexmark',
        'model': 'Printer',
        'mac_prefix': ['00:20:00', '00:40:98', '00:9D:8E', '08:00:11', '74:8F:3C', '9C:AF:CA'],
        'open_ports': [80, 443, 515, 631, 9100],
        'http_signature': {
            'Server': 'Lexmark.*',
            'Server': 'Lexmark-HTTP.*'
        },
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Lexmark.*',
            'SNMPv2-MIB::sysObjectID.0': '.*Lexmark.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'Lexmark.*'
        }
    }
}