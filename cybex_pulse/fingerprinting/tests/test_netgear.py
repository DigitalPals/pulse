"""
Tests for Netgear device signatures.
"""
import pytest
from cybex_pulse.fingerprinting.engine import FingerprintEngine
from cybex_pulse.fingerprinting.devices.netgear import SIGNATURES


def test_netgear_signatures_structure():
    """Test that Netgear signatures are correctly structured."""
    # Check that we have multiple signatures
    assert len(SIGNATURES) > 0
    
    # Check that each signature has required fields
    for sig_id, signature in SIGNATURES.items():
        assert 'device_type' in signature
        assert 'manufacturer' in signature
        assert 'model' in signature
        assert 'mac_prefix' in signature
        assert isinstance(signature['mac_prefix'], list)
        
        # Signature ID should contain 'netgear'
        assert 'netgear' in sig_id


@pytest.fixture
def netgear_router_device_data():
    """Mock device data for a Netgear Nighthawk router."""
    return {
        'ip_address': '192.168.1.1',
        'mac_address': '9C:3D:CF:12:34:56',
        'open_ports': [80, 443, 5000],
        'http_headers': {
            'Server': 'Netgear R7000',
            'WWW-Authenticate': 'Basic realm="NETGEAR R7000"',
            'Content-Type': 'text/html',
            'Connection': 'close'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'NETGEAR Nighthawk AC1900 Router',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.4526.100.11',
            'SNMPv2-MIB::sysName.0': 'R7000'
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'NETGEAR-R7000'
        }
    }


@pytest.fixture
def netgear_readynas_device_data():
    """Mock device data for a Netgear ReadyNAS device."""
    return {
        'ip_address': '192.168.1.20',
        'mac_address': '00:14:6C:AB:CD:EF',
        'open_ports': [22, 80, 443, 445, 139, 111, 2049, 3689],
        'http_headers': {
            'Server': 'Apache/2.4.25',
            'X-Frame-Options': 'SAMEORIGIN',
            'Content-Type': 'text/html; charset=UTF-8',
            'Connection': 'keep-alive'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'ReadyNAS OS 6.10.8',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.4526.22.5',
            'SNMPv2-MIB::sysName.0': 'READYNAS'
        },
        'mdns_data': {
            'service_type': '_afpovertcp._tcp',
            'service_name': 'ReadyNAS-424'
        }
    }


def test_nighthawk_identification(netgear_router_device_data):
    """Test identification of a Netgear Nighthawk router."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(netgear_router_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the Netgear Nighthawk
    best_match = matches[0]
    assert best_match['signature_id'] == 'netgear_nighthawk'
    assert best_match['manufacturer'] == 'Netgear'
    assert best_match['device_type'] == 'Router'
    assert best_match['confidence'] > 0.7  # High confidence


def test_readynas_identification(netgear_readynas_device_data):
    """Test identification of a Netgear ReadyNAS device."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(netgear_readynas_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the Netgear ReadyNAS
    best_match = matches[0]
    assert best_match['signature_id'] == 'netgear_readynas'
    assert best_match['manufacturer'] == 'Netgear'
    assert best_match['device_type'] == 'NAS'
    assert best_match['confidence'] > 0.7  # High confidence


def test_partial_netgear_matches():
    """Test partial matches for Netgear devices with limited data."""
    engine = FingerprintEngine()
    
    # Device with only Netgear MAC address
    mac_only = {
        'ip_address': '192.168.1.30',
        'mac_address': '20:E5:2A:11:22:33',  # Netgear MAC
        'open_ports': [80, 443],
        'http_headers': {},
        'snmp_data': {},
        'mdns_data': {}
    }
    
    matches = engine.identify_device(mac_only)
    
    # Should have matches for Netgear
    assert len(matches) > 0
    assert any('netgear' in match['signature_id'] for match in matches)
    
    # But confidence should be lower
    assert matches[0]['confidence'] < 0.5


def test_negative_identification():
    """Test that non-Netgear devices are not identified as Netgear."""
    engine = FingerprintEngine()
    
    # Device that is clearly not Netgear
    non_netgear_device = {
        'ip_address': '192.168.1.40',
        'mac_address': '14:CC:20:11:22:33',  # TP-Link MAC
        'open_ports': [80, 443],
        'http_headers': {
            'Server': 'TP-LINK',
            'WWW-Authenticate': 'Basic realm="TP-LINK Archer"',
            'Content-Type': 'text/html',
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'TP-LINK Archer C7',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.11863'
        },
        'mdns_data': {}
    }
    
    matches = engine.identify_device(non_netgear_device)
    
    # Should not have a high-confidence Netgear match at the top
    if len(matches) > 0:
        if 'netgear' in matches[0]['signature_id']:
            assert matches[0]['confidence'] < 0.5  # Low confidence if matched at all