"""
Tests for TP-Link device signatures.
"""
import pytest
from cybex_pulse.fingerprinting.engine import FingerprintEngine
from cybex_pulse.fingerprinting.devices.tplink import SIGNATURES


def test_tplink_signatures_structure():
    """Test that TP-Link signatures are correctly structured."""
    # Check that we have multiple signatures
    assert len(SIGNATURES) > 0
    
    # Check that each signature has required fields
    for sig_id, signature in SIGNATURES.items():
        assert 'device_type' in signature
        assert 'manufacturer' in signature
        assert 'model' in signature
        assert 'mac_prefix' in signature
        assert isinstance(signature['mac_prefix'], list)
        
        # Signature ID should contain 'tplink'
        assert 'tplink' in sig_id


@pytest.fixture
def tplink_archer_device_data():
    """Mock device data for a TP-Link Archer router."""
    return {
        'ip_address': '192.168.0.1',
        'mac_address': '94:D9:B3:12:34:56',
        'open_ports': [80, 443],
        'http_headers': {
            'Server': 'TP-LINK Router',
            'WWW-Authenticate': 'Basic realm="TP-LINK Archer C7"',
            'Content-Type': 'text/html',
            'Connection': 'close'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'TP-LINK Archer C7 AC1750 Wireless Router',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.11863',
            'SNMPv2-MIB::sysName.0': 'Archer C7'
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'TP-LINK-ARCHER-C7'
        }
    }


@pytest.fixture
def tplink_eap_device_data():
    """Mock device data for a TP-Link EAP access point."""
    return {
        'ip_address': '192.168.0.100',
        'mac_address': '18:A6:F7:AB:CD:EF',
        'open_ports': [22, 80, 443, 8043],
        'http_headers': {
            'Server': 'TP-LINK EAP',
            'Content-Type': 'text/html',
            'Connection': 'keep-alive'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'TP-LINK EAP225 AC1350 Wireless Access Point',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.11863',
            'SNMPv2-MIB::sysName.0': 'EAP225'
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'EAP225'
        }
    }


@pytest.fixture
def tplink_kasa_device_data():
    """Mock device data for a TP-Link Kasa smart device."""
    return {
        'ip_address': '192.168.0.200',
        'mac_address': '50:C7:BF:11:22:33',
        'open_ports': [80, 9999],
        'http_headers': {
            'Server': 'TP-LINK Kasa Smart Plug',
            'Content-Type': 'application/json',
        },
        'snmp_data': {},
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'Kasa-Smart-Plug'
        }
    }


def test_archer_identification(tplink_archer_device_data):
    """Test identification of a TP-Link Archer router."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(tplink_archer_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the TP-Link Archer
    best_match = matches[0]
    assert best_match['signature_id'] == 'tplink_archer'
    assert best_match['manufacturer'] == 'TP-Link'
    assert best_match['device_type'] == 'Router'
    assert best_match['confidence'] > 0.7  # High confidence


def test_eap_identification(tplink_eap_device_data):
    """Test identification of a TP-Link EAP Access Point."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(tplink_eap_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the TP-Link EAP
    best_match = matches[0]
    assert best_match['signature_id'] == 'tplink_eap'
    assert best_match['manufacturer'] == 'TP-Link'
    assert best_match['device_type'] == 'Access Point'
    assert best_match['confidence'] > 0.7  # High confidence


def test_kasa_identification(tplink_kasa_device_data):
    """Test identification of a TP-Link Kasa smart device."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(tplink_kasa_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the TP-Link Kasa
    best_match = matches[0]
    assert best_match['signature_id'] == 'tplink_kasa'
    assert best_match['manufacturer'] == 'TP-Link'
    assert best_match['device_type'] == 'Smart Home'
    assert best_match['confidence'] > 0.7  # High confidence


def test_partial_tplink_matches():
    """Test partial matches for TP-Link devices with limited data."""
    engine = FingerprintEngine()
    
    # Device with only TP-Link MAC address
    mac_only = {
        'ip_address': '192.168.0.50',
        'mac_address': '14:CC:20:11:22:33',  # TP-Link MAC
        'open_ports': [80, 443],
        'http_headers': {},
        'snmp_data': {},
        'mdns_data': {}
    }
    
    matches = engine.identify_device(mac_only)
    
    # Should have matches for TP-Link
    assert len(matches) > 0
    assert any('tplink' in match['signature_id'] for match in matches)
    
    # But confidence should be lower
    assert matches[0]['confidence'] < 0.5


def test_negative_identification():
    """Test that non-TP-Link devices are not identified as TP-Link."""
    engine = FingerprintEngine()
    
    # Device that is clearly not TP-Link
    non_tplink_device = {
        'ip_address': '192.168.0.60',
        'mac_address': '00:14:6C:11:22:33',  # Netgear MAC
        'open_ports': [80, 443],
        'http_headers': {
            'Server': 'Netgear R7000',
            'WWW-Authenticate': 'Basic realm="NETGEAR R7000"',
            'Content-Type': 'text/html'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'NETGEAR Nighthawk Router',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.4526'
        },
        'mdns_data': {}
    }
    
    matches = engine.identify_device(non_tplink_device)
    
    # Should not have a high-confidence TP-Link match at the top
    if len(matches) > 0:
        if 'tplink' in matches[0]['signature_id']:
            assert matches[0]['confidence'] < 0.5  # Low confidence if matched at all