"""
Tests for additional network device signatures.
"""
import pytest
from cybex_pulse.fingerprinting.engine import FingerprintEngine
from cybex_pulse.fingerprinting.devices.network import SIGNATURES


def test_network_signatures_structure():
    """Test that network signatures are correctly structured."""
    # Check that we have multiple signatures
    assert len(SIGNATURES) > 0
    
    # Check that each signature has required fields
    for sig_id, signature in SIGNATURES.items():
        assert 'device_type' in signature
        assert 'manufacturer' in signature
        assert 'model' in signature
        assert 'mac_prefix' in signature
        assert isinstance(signature['mac_prefix'], list)


@pytest.fixture
def mikrotik_router_device_data():
    """Mock device data for a MikroTik router."""
    return {
        'ip_address': '192.168.1.1',
        'mac_address': '4C:5E:0C:12:34:56',
        'open_ports': [22, 23, 80, 443, 8291, 8728, 8729],
        'http_headers': {
            'Server': 'MikroTik/6.48',
            'WWW-Authenticate': 'Basic realm="MikroTik RouterOS"',
            'Content-Type': 'text/html',
            'Connection': 'close'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'RouterOS RB4011',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.14988.1',
            'SNMPv2-MIB::sysName.0': 'MikroTik'
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'MikroTik-Router'
        }
    }


@pytest.fixture
def aruba_ap_device_data():
    """Mock device data for an Aruba access point."""
    return {
        'ip_address': '192.168.1.2',
        'mac_address': '94:B4:0F:AB:CD:EF',
        'open_ports': [22, 80, 443],
        'http_headers': {
            'Server': 'Aruba',
            'WWW-Authenticate': 'Basic realm="Aruba AP"',
            'Content-Type': 'text/html',
            'Connection': 'close'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'Aruba AP-505',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.14823.1.2',
            'SNMPv2-MIB::sysName.0': 'Aruba-AP'
        },
        'mdns_data': {
            'service_type': '_airwave-discovery._tcp',
            'service_name': 'Aruba-AP-505'
        }
    }


@pytest.fixture
def aruba_switch_device_data():
    """Mock device data for an Aruba switch."""
    return {
        'ip_address': '192.168.1.3',
        'mac_address': '24:DE:C6:11:22:33',
        'open_ports': [22, 23, 80, 443, 161, 162],
        'http_headers': {
            'Server': 'Aruba',
            'WWW-Authenticate': 'Basic realm="Aruba Switch"',
            'Content-Type': 'text/html',
            'Connection': 'close'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'Aruba 2930F Switch, revision Y.11.77',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.14823.1.1',
            'SNMPv2-MIB::sysName.0': 'Aruba-Switch'
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'Aruba-2930F'
        }
    }


def test_mikrotik_router_identification(mikrotik_router_device_data):
    """Test identification of a MikroTik router."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(mikrotik_router_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the MikroTik router
    best_match = matches[0]
    assert best_match['signature_id'] == 'mikrotik_router'
    assert best_match['manufacturer'] == 'MikroTik'
    assert best_match['device_type'] == 'Router'
    assert best_match['confidence'] > 0.7  # High confidence


def test_aruba_ap_identification(aruba_ap_device_data):
    """Test identification of an Aruba access point."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(aruba_ap_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the Aruba AP
    best_match = matches[0]
    assert best_match['signature_id'] == 'aruba_ap'
    assert best_match['manufacturer'] == 'Aruba'
    assert best_match['device_type'] == 'Access Point'
    assert best_match['confidence'] > 0.7  # High confidence


def test_aruba_switch_identification(aruba_switch_device_data):
    """Test identification of an Aruba switch."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(aruba_switch_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the Aruba switch
    best_match = matches[0]
    assert best_match['signature_id'] == 'aruba_switch'
    assert best_match['manufacturer'] == 'Aruba'
    assert best_match['device_type'] == 'Switch'
    assert best_match['confidence'] > 0.7  # High confidence


def test_partial_network_matches():
    """Test partial matches for network devices with limited data."""
    engine = FingerprintEngine()
    
    # Device with only MikroTik MAC address
    mac_only = {
        'ip_address': '192.168.1.4',
        'mac_address': 'B8:69:F4:11:22:33',  # MikroTik MAC
        'open_ports': [80, 443],
        'http_headers': {},
        'snmp_data': {},
        'mdns_data': {}
    }
    
    matches = engine.identify_device(mac_only)
    
    # Should have matches for MikroTik
    assert len(matches) > 0
    assert any('mikrotik' in match['signature_id'] for match in matches)
    
    # But confidence should be lower
    assert matches[0]['confidence'] < 0.5


def test_distinguishing_between_similar_devices():
    """Test that we can distinguish between similar Aruba devices."""
    engine = FingerprintEngine()
    
    # Create a device that could be an AP or a switch
    ambiguous_device = {
        'ip_address': '192.168.1.5',
        'mac_address': 'AC:A3:1E:11:22:33',  # Aruba MAC
        'open_ports': [22, 80, 443],
        'http_headers': {
            'Server': 'Aruba',
            'WWW-Authenticate': 'Basic realm="Aruba"',
        },
        'snmp_data': {},
        'mdns_data': {}
    }
    
    # Initial match could be either AP or switch
    initial_matches = engine.identify_device(ambiguous_device)
    assert len(initial_matches) >= 2
    
    # Now add SNMP data specifically indicating it's a switch
    ambiguous_device['snmp_data'] = {
        'SNMPv2-MIB::sysDescr.0': 'Aruba 2540 Switch',
        'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.14823.1.1',
    }
    
    switch_matches = engine.identify_device(ambiguous_device)
    assert switch_matches[0]['signature_id'] == 'aruba_switch'
    
    # Now modify to look like an AP
    ambiguous_device['snmp_data'] = {
        'SNMPv2-MIB::sysDescr.0': 'Aruba AP-303',
        'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.14823.1.2',
    }
    
    ap_matches = engine.identify_device(ambiguous_device)
    assert ap_matches[0]['signature_id'] == 'aruba_ap'