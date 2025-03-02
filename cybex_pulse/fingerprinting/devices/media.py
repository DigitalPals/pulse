"""
Signature definitions for Media/Entertainment devices.
"""

# Dictionary of device signatures for Media/Entertainment devices
SIGNATURES = {
    # Roku
    'roku': {
        'device_type': 'Media Player',
        'manufacturer': 'Roku',
        'model': 'Streaming Player',
        'mac_prefix': ['00:0D:4B', 'DC:3A:5E', 'CC:6D:A0', 'D8:31:CF', 'B0:A7:37', 'BC:D1:1F'],
        'open_ports': [80, 8060, 1900],
        'http_signature': {
            'Server': 'Roku UPnP.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'Roku.*'
        }
    },
    
    # Roku TV
    'roku_tv': {
        'device_type': 'Smart TV',
        'manufacturer': 'Roku',
        'model': 'TV',
        'mac_prefix': ['00:0D:4B', 'DC:3A:5E', 'CC:6D:A0', 'D8:31:CF', 'B0:A7:37', 'BC:D1:1F'],
        'open_ports': [80, 8060, 1900],
        'http_signature': {
            'Server': 'Roku UPnP.*'
        },
        'mdns_signature': {
            'service_type': '_http._tcp',
            'service_name': 'Roku TV.*'
        }
    },
    
    # Apple TV
    'apple_tv': {
        'device_type': 'Media Player',
        'manufacturer': 'Apple',
        'model': 'Apple TV',
        'mac_prefix': ['00:25:00', '3C:07:54', '98:B8:E3', 'F0:D1:A9', 'F8:62:14', 'FC:41:DE'],
        'open_ports': [7000, 3689, 5353],
        'http_signature': {},
        'mdns_signature': {
            'service_type': '_airplay._tcp',
            'service_name': 'Apple TV.*'
        }
    },
    
    # Amazon Fire TV
    'amazon_fire_tv': {
        'device_type': 'Media Player',
        'manufacturer': 'Amazon',
        'model': 'Fire TV',
        'mac_prefix': ['00:BB:3A', '44:65:0D', '74:75:48', '84:D6:D0', 'A0:02:DC', 'B0:FC:0D'],
        'open_ports': [80, 1900, 7575, 8008],
        'http_signature': {
            'Server': 'AmazonWebServer'
        },
        'mdns_signature': {
            'service_type': '_amzn-wplay._tcp',
            'service_name': 'Fire TV.*'
        }
    },
    
    # Chromecast
    'chromecast': {
        'device_type': 'Media Player',
        'manufacturer': 'Google',
        'model': 'Chromecast',
        'mac_prefix': ['00:28:F8', '20:DF:B9', '43:A3:9B', '54:60:09', '6C:AD:F8', '94:EB:2C'],
        'open_ports': [8008, 8009, 1900, 5353],
        'http_signature': {
            'Server': 'Eureka/.*'
        },
        'mdns_signature': {
            'service_type': '_googlecast._tcp',
            'service_name': 'Chromecast.*'
        }
    },
    
    # Google TV
    'google_tv': {
        'device_type': 'Media Player',
        'manufacturer': 'Google',
        'model': 'Google TV',
        'mac_prefix': ['00:28:F8', '20:DF:B9', '43:A3:9B', '54:60:09', '6C:AD:F8', '94:EB:2C'],
        'open_ports': [8008, 8009, 1900, 5353],
        'http_signature': {
            'Server': 'Eureka/.*'
        },
        'mdns_signature': {
            'service_type': '_googlecast._tcp',
            'service_name': 'Google-TV.*'
        }
    },
    
    # Plex Media Server
    'plex_media_server': {
        'device_type': 'Media Server',
        'manufacturer': 'Plex',
        'model': 'Media Server',
        'mac_prefix': [],  # No specific MAC prefix as it runs on various hardware
        'open_ports': [32400, 3005, 8324, 32469],
        'http_signature': {
            'Server': 'Plex.*',
            'X-Plex-Protocol': '.*'
        },
        'mdns_signature': {
            'service_type': '_plex._tcp',
            'service_name': 'Plex Media Server.*'
        }
    }
}