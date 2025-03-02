"""
Signature definitions for Smart Home/IoT devices.
"""

# Dictionary of device signatures for Smart Home/IoT devices
SIGNATURES = {
    # Shelly Smart Plug
    'shelly_plug': {
        'device_type': 'Smart Plug',
        'manufacturer': 'Shelly',
        'model': 'Plug',
        'mac_prefix': ['C4:5B:BE', 'CC:50:E3', 'E8:DB:84', '08:B6:1F', 'C8:2B:96'],
        'open_ports': [80, 443],
        'http_signature': {
            'Server': 'Mongoose/.*',
            'Content-Type': 'application/json'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'shelly.*'
        }
    },
    
    # Shelly 2.5
    'shelly_25': {
        'device_type': 'Smart Relay',
        'manufacturer': 'Shelly',
        'model': '2.5',
        'mac_prefix': ['C4:5B:BE', 'CC:50:E3', 'E8:DB:84', '08:B6:1F', 'C8:2B:96', 'BC:FF:4D'],
        'open_ports': [80, 443],
        'http_signature': {
            'Server': 'Mongoose/.*',
            'Content-Type': 'application/json'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'shelly.*'
        }
    },
    
    # Philips Hue Bridge
    'philips_hue_bridge': {
        'device_type': 'Smart Hub',
        'manufacturer': 'Philips',
        'model': 'Hue Bridge',
        'mac_prefix': ['00:17:88', 'EC:B5:FA'],
        'open_ports': [80, 443],
        'http_signature': {
            'Server': 'nginx',
            'Cache-Control': 'no-store',
            'X-XSS-Protection': '1'
        },
        'mdns_signature': {
            'service_type': '_hue._tcp',
            'service_name': 'Philips.*'
        }
    },
    
    # Sonos Speaker
    'sonos_speaker': {
        'device_type': 'Speaker',
        'manufacturer': 'Sonos',
        'model': 'Speaker',
        'mac_prefix': ['00:0E:58', '5C:AA:FD', 'B8:E9:37', '94:9F:3E', '48:A6:B8'],
        'open_ports': [80, 443, 1400, 1443],
        'http_signature': {
            'Server': 'Linux UPnP/.*',
            'Content-Type': 'text/xml'
        },
        'snmp_signature': {},
        'mdns_signature': {
            'service_type': '_sonos._tcp',
            'service_name': 'Sonos.*'
        }
    },
    
    # Home Assistant
    'home_assistant': {
        'device_type': 'Smart Hub',
        'manufacturer': 'Home Assistant',
        'model': 'Server',
        'mac_prefix': [],  # No specific MAC prefix as it runs on various hardware
        'open_ports': [80, 443, 8123],
        'http_signature': {
            'Server': 'Python/Werkzeug',
            'X-Home-Assistant': '.*'
        },
        'mdns_signature': {
            'service_type': '_home-assistant._tcp',
            'service_name': 'Home Assistant.*'
        }
    },
    
    # Raspberry Pi
    'raspberry_pi': {
        'device_type': 'Single Board Computer',
        'manufacturer': 'Raspberry Pi Foundation',
        'model': 'Raspberry Pi',
        'mac_prefix': ['B8:27:EB', 'DC:A6:32', 'E4:5F:01', '28:CD:C1'],
        'open_ports': [22, 80],
        'http_signature': {},
        'snmp_signature': {
            'SNMPv2-MIB::sysDescr.0': '.*Raspberry Pi.*'
        },
        'mdns_signature': {
            'service_type': '_ssh._tcp',
            'service_name': 'raspberrypi.*'
        }
    },
    
    # ESP8266
    'esp8266': {
        'device_type': 'Microcontroller',
        'manufacturer': 'Espressif',
        'model': 'ESP8266',
        'mac_prefix': ['18:FE:34', '5C:CF:7F', '60:01:94', 'A0:20:A6', 'A4:CF:12', 'EC:FA:BC'],
        'open_ports': [80],
        'http_signature': {
            'Server': 'ESP8266.*'
        },
        # Require these specific content indicators to match ESP8266
        'content_indicators': [
            'esp8266', 
            'espressif',
            'nodemcu'
        ]
    },
    
    # ESP32
    'esp32': {
        'device_type': 'Microcontroller',
        'manufacturer': 'Espressif',
        'model': 'ESP32',
        'mac_prefix': ['24:0A:C4', '24:62:AB', '30:AE:A4', '3C:61:05', '3C:71:BF', '48:3F:DA', '84:F3:EB', '94:B9:7E', 'A0:B7:65', 'AC:67:B2'],
        'open_ports': [80],
        'http_signature': {
            'Server': 'ESP32.*'
        }
    }
}