"""
Tests for Synology device signatures.
"""
import pytest
from cybex_pulse.fingerprinting.engine import FingerprintEngine
from cybex_pulse.fingerprinting.devices.synology import SIGNATURES


def test_synology_signatures_structure():
    """Test that Synology signatures are correctly structured."""
    # Check that we have multiple signatures
    assert len(SIGNATURES) > 0
    
    # Check that each signature has required fields
    for sig_id, signature in SIGNATURES.items():
        assert 'device_type' in signature
        assert 'manufacturer' in signature
        assert 'model' in signature
        assert 'mac_prefix' in signature
        assert isinstance(signature['mac_prefix'], list)
        
        # Signature ID should contain 'synology'
        assert 'synology' in sig_id


def test_synology_nas_identification(synology_nas_device_data):
    """Test identification of a Synology NAS."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(synology_nas_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the DS920+ model
    best_match = matches[0]
    assert best_match['signature_id'] == 'synology_ds920plus'
    assert best_match['manufacturer'] == 'Synology'
    assert best_match['device_type'] == 'NAS'
    assert best_match['confidence'] > 0.8  # High confidence


def test_generic_synology_identification():
    """Test identification of a generic Synology NAS."""
    engine = FingerprintEngine()
    
    # Create a mock generic Synology NAS
    generic_data = {
        'ip_address': '192.168.1.2',
        'mac_address': '00:11:32:AA:BB:CC',  # Synology MAC
        'open_ports': [22, 80, 443, 5000, 5001, 139, 445],
        'http_headers': {
            'Server': 'nginx',
            'X-Powered-By': 'PHP/7.3.19',
            'Set-Cookie': 'id=123456789',
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'Linux DiskStation 4.4.59+ #42962',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.8072.3.2.10',
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'DiskStation'
        }
    }
    
    matches = engine.identify_device(generic_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the generic DiskStation
    best_match = matches[0]
    assert best_match['signature_id'] == 'synology_diskstation'
    assert best_match['manufacturer'] == 'Synology'
    assert best_match['model'] == 'DiskStation'
    assert best_match['confidence'] > 0.7  # High confidence


def test_synology_router_identification():
    """Test identification of a Synology router."""
    engine = FingerprintEngine()
    
    # Create a mock Synology router
    router_data = {
        'ip_address': '192.168.1.1',
        'mac_address': '00:11:32:DD:EE:FF',  # Synology MAC
        'open_ports': [22, 80, 443],
        'http_headers': {
            'Server': 'nginx',
            'X-Powered-By': 'PHP/7.3',
            'Set-Cookie': 'id=123456789',
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'RT6600ax Router',
            'SNMPv2-MIB::sysObjectID.0': 'Synology Inc.',
        },
        'mdns_data': {}
    }
    
    matches = engine.identify_device(router_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the Synology router
    best_match = matches[0]
    assert best_match['signature_id'] == 'synology_rt6600ax'
    assert best_match['manufacturer'] == 'Synology'
    assert best_match['device_type'] == 'Router'
    assert best_match['confidence'] > 0.5  # Moderate confidence


def test_specific_nas_model_identification():
    """Test identification of specific Synology NAS models."""
    engine = FingerprintEngine()
    
    # Create data for RS1221+ model
    rs1221_data = {
        'ip_address': '192.168.1.3',
        'mac_address': '00:11:32:11:22:33',  # Synology MAC
        'open_ports': [22, 80, 443, 5000, 5001, 139, 445],
        'http_headers': {
            'Server': 'nginx',
            'X-Powered-By': 'PHP/7.4',
            'Set-Cookie': 'id=123456789',
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'Linux RS1221+ 4.4.180+ #42218',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.8072.3.2.10',
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'RS1221+'
        }
    }
    
    matches = engine.identify_device(rs1221_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the RS1221+ model
    best_match = matches[0]
    assert best_match['signature_id'] == 'synology_rs1221plus'
    assert best_match['manufacturer'] == 'Synology'
    assert best_match['model'] == 'RS1221+'
    assert best_match['confidence'] > 0.7  # High confidence


def test_partial_synology_match():
    """Test Synology identification with partial data."""
    engine = FingerprintEngine()
    
    # Only Synology MAC and a few ports
    partial_data = {
        'ip_address': '192.168.1.4',
        'mac_address': '00:11:32:AA:BB:CC',  # Synology MAC
        'open_ports': [80, 443, 5000],
        'http_headers': {},
        'snmp_data': {},
        'mdns_data': {}
    }
    
    matches = engine.identify_device(partial_data)
    
    # Should match a Synology device
    assert len(matches) > 0
    assert matches[0]['manufacturer'] == 'Synology'
    
    # But confidence should be lower due to limited data
    assert matches[0]['confidence'] < 0.5