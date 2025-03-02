"""
Tests for UniFi device signatures.
"""
import pytest
from cybex_pulse.fingerprinting.engine import FingerprintEngine
from cybex_pulse.fingerprinting.devices.unifi import SIGNATURES


def test_unifi_signatures_structure():
    """Test that UniFi signatures are correctly structured."""
    # Check that we have multiple signatures
    assert len(SIGNATURES) > 0
    
    # Check that each signature has required fields
    for sig_id, signature in SIGNATURES.items():
        assert 'device_type' in signature
        assert 'manufacturer' in signature
        assert 'model' in signature
        assert 'mac_prefix' in signature
        assert isinstance(signature['mac_prefix'], list)
        
        # Signature ID should contain 'unifi'
        assert 'unifi' in sig_id


def test_udm_identification(unifi_udm_device_data):
    """Test identification of a UniFi Dream Machine."""
    engine = FingerprintEngine()
    
    # Create a modified version that precisely matches a UDM Pro
    udm_pro_data = unifi_udm_device_data.copy()
    udm_pro_data['snmp_data']['SNMPv2-MIB::sysDescr.0'] = 'UniFi Dream Machine Pro v1.0.4'
    
    matches = engine.identify_device(udm_pro_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the UDM Pro
    best_match = matches[0]
    assert best_match['signature_id'] == 'unifi_udm_pro'
    assert best_match['manufacturer'] == 'Ubiquiti'
    assert best_match['confidence'] > 0.8  # High confidence


def test_usg_identification():
    """Test identification of a UniFi Security Gateway."""
    engine = FingerprintEngine()
    
    # Create a mock USG device
    usg_data = {
        'ip_address': '192.168.1.1',
        'mac_address': 'FC:EC:DA:11:22:33',  # UniFi MAC
        'open_ports': [22, 80, 443, 8080, 8443],
        'http_headers': {
            'Server': 'lighttpd',
            'Content-Type': 'text/html',
            'Connection': 'keep-alive'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'USG-PRO-4 Linux',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.41112'
        },
        'mdns_data': {}
    }
    
    matches = engine.identify_device(usg_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the USG
    best_match = matches[0]
    assert best_match['signature_id'] == 'unifi_usg'
    assert best_match['manufacturer'] == 'Ubiquiti'
    assert best_match['confidence'] > 0.7  # High confidence


def test_unifi_ap_identification():
    """Test identification of a UniFi Access Point."""
    engine = FingerprintEngine()
    
    # Create a mock UniFi AP device
    ap_data = {
        'ip_address': '192.168.1.5',
        'mac_address': '80:2A:A8:44:55:66',  # UniFi AP MAC
        'open_ports': [22, 80, 443],
        'http_headers': {
            'Server': 'UniFi',
            'Content-Type': 'text/html',
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'UAP-AC-PRO Linux',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.41112'
        },
        'mdns_data': {
            'service_type': '_ubnt._tcp',
            'service_name': 'UAP-AC-PRO'
        }
    }
    
    matches = engine.identify_device(ap_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the UniFi AP
    best_match = matches[0]
    assert best_match['signature_id'] == 'unifi_ap'
    assert best_match['manufacturer'] == 'Ubiquiti'
    assert best_match['device_type'] == 'Access Point'
    assert best_match['confidence'] > 0.7  # High confidence


def test_unifi_switch_identification():
    """Test identification of a UniFi Switch."""
    engine = FingerprintEngine()
    
    # Create a mock UniFi Switch device
    switch_data = {
        'ip_address': '192.168.1.6',
        'mac_address': '74:83:C2:77:88:99',  # UniFi Switch MAC
        'open_ports': [22, 80, 443, 161],
        'http_headers': {
            'Server': 'UniFi',
            'Content-Type': 'text/html',
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'UniFi Switch 24 PoE',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.41112'
        },
        'mdns_data': {}
    }
    
    matches = engine.identify_device(switch_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the UniFi Switch
    best_match = matches[0]
    assert best_match['signature_id'] == 'unifi_switch'
    assert best_match['manufacturer'] == 'Ubiquiti'
    assert best_match['device_type'] == 'Switch'
    assert best_match['confidence'] > 0.7  # High confidence


def test_partial_unifi_matches():
    """Test partial matches for UniFi devices with limited data."""
    engine = FingerprintEngine()
    
    # Device with only UniFi MAC address
    mac_only = {
        'ip_address': '192.168.1.10',
        'mac_address': 'FC:EC:DA:11:22:33',  # UniFi MAC
        'open_ports': [],
        'http_headers': {},
        'snmp_data': {},
        'mdns_data': {}
    }
    
    matches = engine.identify_device(mac_only)
    
    # Should have matches for UniFi
    assert len(matches) > 0
    assert any('unifi' in match['signature_id'] for match in matches)
    
    # But confidence should be lower
    assert matches[0]['confidence'] < 0.5