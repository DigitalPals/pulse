"""
Comprehensive tests for the device fingerprinting system.
Tests multiple device types and the ability to differentiate between similar devices.
"""
import pytest
from cybex_pulse.fingerprinting.engine import FingerprintEngine


def test_engine_loads_all_signature_files():
    """Test that the engine loads all signature files correctly."""
    engine = FingerprintEngine()
    
    # The engine should load at least the device modules we've created
    expected_modules = [
        'unifi', 'synology', 'cisco', 'netgear', 'tplink', 
        'nas', 'network', 'smarthome', 'media', 'printers'
    ]
    
    loaded_modules = engine.get_available_modules()
    
    # Check that we've loaded the expected modules
    for module in expected_modules:
        assert module in loaded_modules, f"Module {module} not loaded"
    
    # We should have a significant number of signatures
    signature_count = engine.get_signature_count()
    assert signature_count > 20, f"Only {signature_count} signatures loaded"


def test_manufacturer_identification_confidence():
    """Test that similar devices from different manufacturers are correctly identified."""
    engine = FingerprintEngine()
    
    # Test devices from different manufacturers that serve similar functions
    
    # TP-Link Router
    tplink_router = {
        'ip_address': '192.168.0.1',
        'mac_address': '14:CC:20:11:22:33',  # TP-Link MAC
        'open_ports': [80, 443],
        'http_headers': {
            'Server': 'TP-LINK Router',
            'WWW-Authenticate': 'Basic realm="TP-LINK Archer C7"',
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'TP-LINK Archer C7',
        },
        'mdns_data': {}
    }
    
    # Netgear Router
    netgear_router = {
        'ip_address': '192.168.1.1',
        'mac_address': '9C:3D:CF:11:22:33',  # Netgear MAC
        'open_ports': [80, 443],
        'http_headers': {
            'Server': 'Netgear Router',
            'WWW-Authenticate': 'Basic realm="NETGEAR R7000"',
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'NETGEAR R7000',
        },
        'mdns_data': {}
    }
    
    # Get matches for both
    tplink_matches = engine.identify_device(tplink_router)
    netgear_matches = engine.identify_device(netgear_router)
    
    # Each router should be identified as the correct manufacturer
    assert any('tplink' in match['signature_id'] for match in tplink_matches[:3])
    assert any('netgear' in match['signature_id'] for match in netgear_matches[:3])
    
    # They should not be confused with each other
    assert not any('netgear' in match['signature_id'] for match in tplink_matches[:3])
    assert not any('tplink' in match['signature_id'] for match in netgear_matches[:3])


def test_multi_factor_identification():
    """
    Test that devices are more confidently identified when multiple
    identification factors are present.
    """
    engine = FingerprintEngine()
    
    # Create device data with increasing levels of identification factors
    
    # Start with just a MAC address
    synology_device = {
        'ip_address': '192.168.1.100',
        'mac_address': '00:11:32:AB:CD:EF',  # Synology MAC
        'open_ports': [],
        'http_headers': {},
        'snmp_data': {},
        'mdns_data': {}
    }
    
    # Get initial match with just MAC
    mac_only_matches = engine.identify_device(synology_device)
    
    # Add open ports typical for a NAS
    synology_device['open_ports'] = [22, 80, 443, 139, 445, 111, 2049, 5000, 5001]
    ports_matches = engine.identify_device(synology_device)
    
    # Add HTTP headers
    synology_device['http_headers'] = {
        'Server': 'nginx',
        'X-Powered-By': 'PHP/7.3',
        'Set-Cookie': 'id=DSM'
    }
    http_matches = engine.identify_device(synology_device)
    
    # Add SNMP data
    synology_device['snmp_data'] = {
        'SNMPv2-MIB::sysDescr.0': 'Linux DSM 4.4.59+ #42962',
        'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.8072.3.2.10',
        'SNMPv2-MIB::sysName.0': 'Synology'
    }
    snmp_matches = engine.identify_device(synology_device)
    
    # Add mDNS data
    synology_device['mdns_data'] = {
        'service_type': '_http._tcp',
        'service_name': 'Synology-DS920'
    }
    full_matches = engine.identify_device(synology_device)
    
    # Check that confidence increases with more factors
    if len(mac_only_matches) > 0 and len(ports_matches) > 0:
        assert ports_matches[0]['confidence'] > mac_only_matches[0]['confidence']
    
    if len(ports_matches) > 0 and len(http_matches) > 0:
        assert http_matches[0]['confidence'] > ports_matches[0]['confidence']
    
    if len(http_matches) > 0 and len(snmp_matches) > 0:
        assert snmp_matches[0]['confidence'] > http_matches[0]['confidence']
    
    if len(snmp_matches) > 0 and len(full_matches) > 0:
        assert full_matches[0]['confidence'] > snmp_matches[0]['confidence']
    
    # With all factors, we should have a high confidence match
    assert full_matches[0]['confidence'] > 0.8


def test_confidence_scoring_algorithm():
    """Test that the confidence scoring algorithm works as expected."""
    engine = FingerprintEngine()
    
    # Create a device with conflicting identification signals
    mixed_device = {
        'ip_address': '192.168.1.200',
        'mac_address': 'B4:FB:E4:11:22:33',  # UniFi MAC
        'open_ports': [22, 80, 443, 8291],   # 8291 is typical of MikroTik
        'http_headers': {
            'Server': 'nginx',               # Generic, used by many devices
            'Content-Type': 'text/html'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'RouterOS',  # MikroTik identifier
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.41112'  # Ubiquiti OID
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'Gateway'        # Generic name
        }
    }
    
    matches = engine.identify_device(mixed_device)
    
    # With conflicting signals, confidence should be lower
    assert matches[0]['confidence'] < 0.7
    
    # Fix the conflicting signals to all point to UniFi
    mixed_device['open_ports'] = [22, 80, 443, 8080, 8443]  # Typical UniFi ports
    mixed_device['http_headers']['Server'] = 'UniFi'
    mixed_device['snmp_data'] = {
        'SNMPv2-MIB::sysDescr.0': 'UniFi Security Gateway',
        'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.41112'
    }
    mixed_device['mdns_data']['service_name'] = 'USG'
    
    clear_matches = engine.identify_device(mixed_device)
    
    # Now with clear signals, confidence should be higher
    assert clear_matches[0]['confidence'] > 0.8
    
    # And it should be identified as a UniFi device
    assert 'unifi' in clear_matches[0]['signature_id']


def test_identification_priority():
    """Test that certain identification signals take priority over others."""
    engine = FingerprintEngine()
    
    # Create a device with a typical QNAP MAC address but SNMP data for a Synology
    mixed_nas = {
        'ip_address': '192.168.1.101',
        'mac_address': '00:08:9B:11:22:33',  # QNAP MAC
        'open_ports': [22, 80, 443, 139, 445, 2049],  # Generic NAS ports
        'http_headers': {
            'Server': 'nginx',
            'Content-Type': 'text/html'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'Linux DSM 4.4.59+ #42962',  # Synology identifier
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.8072.3.2.10',
            'SNMPv2-MIB::sysName.0': 'Synology'
        },
        'mdns_data': {}
    }
    
    matches = engine.identify_device(mixed_nas)
    
    # Check that we have both QNAP and Synology in the results
    assert any('qnap' in match['signature_id'] for match in matches)
    assert any('synology' in match['signature_id'] for match in matches)
    
    # SNMP data should generally be more reliable than MAC for determining model,
    # so Synology should have a higher confidence than QNAP despite the MAC
    synology_match = next((match for match in matches if 'synology' in match['signature_id']), None)
    qnap_match = next((match for match in matches if 'qnap' in match['signature_id']), None)
    
    if synology_match and qnap_match:
        assert synology_match['confidence'] > qnap_match['confidence']
    
    # Now add mdns data that clearly indicates Synology
    mixed_nas['mdns_data'] = {
        'service_type': '_http._tcp',
        'service_name': 'Synology-DS920'
    }
    
    updated_matches = engine.identify_device(mixed_nas)
    
    # Now Synology should be the clear winner
    assert updated_matches[0]['signature_id'].startswith('synology')