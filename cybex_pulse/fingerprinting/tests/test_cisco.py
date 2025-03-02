"""
Tests for Cisco device signatures.
"""
import pytest
from cybex_pulse.fingerprinting.engine import FingerprintEngine
from cybex_pulse.fingerprinting.devices.cisco import SIGNATURES


def test_cisco_signatures_structure():
    """Test that Cisco signatures are correctly structured."""
    # Check that we have multiple signatures
    assert len(SIGNATURES) > 0
    
    # Check that each signature has required fields
    for sig_id, signature in SIGNATURES.items():
        assert 'device_type' in signature
        assert 'manufacturer' in signature
        assert 'model' in signature
        assert 'mac_prefix' in signature
        assert isinstance(signature['mac_prefix'], list)
        
        # Signature ID should contain 'cisco'
        assert 'cisco' in sig_id


@pytest.fixture
def cisco_catalyst_device_data():
    """Mock device data for a Cisco Catalyst switch."""
    return {
        'ip_address': '192.168.1.10',
        'mac_address': '00:0A:41:12:34:56',
        'open_ports': [22, 23, 80, 443, 161, 162, 514],
        'http_headers': {
            'Server': 'cisco-IOS',
            'Content-Type': 'text/html',
            'Connection': 'close'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'Cisco IOS Software, Catalyst 3750 Software',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.9.1.516',
            'SNMPv2-MIB::sysUpTime.0': '123456',
            'SNMPv2-MIB::sysName.0': 'CAT-SW-01'
        },
        'mdns_data': {}
    }


@pytest.fixture
def cisco_asa_device_data():
    """Mock device data for a Cisco ASA firewall."""
    return {
        'ip_address': '192.168.1.1',
        'mac_address': '00:0C:86:AB:CD:EF',
        'open_ports': [22, 23, 80, 443, 161, 162, 8443],
        'http_headers': {
            'Server': 'Adaptive Security Appliance HTTP/1.1',
            'Content-Type': 'text/html',
            'Connection': 'close'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'Cisco Adaptive Security Appliance Version 9.8(2)',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.9.1.1615',
            'SNMPv2-MIB::sysName.0': 'ASA-FW-01'
        },
        'mdns_data': {}
    }


def test_catalyst_identification(cisco_catalyst_device_data):
    """Test identification of a Cisco Catalyst switch."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(cisco_catalyst_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the Cisco Catalyst
    best_match = matches[0]
    assert best_match['signature_id'] == 'cisco_catalyst'
    assert best_match['manufacturer'] == 'Cisco'
    assert best_match['device_type'] == 'Switch'
    assert best_match['confidence'] > 0.7  # High confidence


def test_asa_identification(cisco_asa_device_data):
    """Test identification of a Cisco ASA firewall."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(cisco_asa_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the Cisco ASA
    best_match = matches[0]
    assert best_match['signature_id'] == 'cisco_asa'
    assert best_match['manufacturer'] == 'Cisco'
    assert best_match['device_type'] == 'Firewall'
    assert best_match['confidence'] > 0.7  # High confidence


def test_partial_cisco_matches():
    """Test partial matches for Cisco devices with limited data."""
    engine = FingerprintEngine()
    
    # Device with only Cisco MAC address
    mac_only = {
        'ip_address': '192.168.1.20',
        'mac_address': '00:0A:41:11:22:33',  # Cisco MAC
        'open_ports': [80, 443],
        'http_headers': {},
        'snmp_data': {},
        'mdns_data': {}
    }
    
    matches = engine.identify_device(mac_only)
    
    # Should have matches for Cisco
    assert len(matches) > 0
    assert any('cisco' in match['signature_id'] for match in matches)
    
    # But confidence should be lower
    assert matches[0]['confidence'] < 0.5


def test_negative_identification():
    """Test that non-Cisco devices are not identified as Cisco."""
    engine = FingerprintEngine()
    
    # Device that is clearly not Cisco
    non_cisco_device = {
        'ip_address': '192.168.1.30',
        'mac_address': 'B4:FB:E4:11:22:33',  # UniFi MAC
        'open_ports': [22, 80, 443],
        'http_headers': {
            'Server': 'UniFi',
            'Content-Type': 'text/html',
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'UniFi Security Gateway',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.41112'
        },
        'mdns_data': {}
    }
    
    matches = engine.identify_device(non_cisco_device)
    
    # Should not have a high-confidence Cisco match at the top
    if len(matches) > 0:
        if 'cisco' in matches[0]['signature_id']:
            assert matches[0]['confidence'] < 0.5  # Low confidence if matched at all