"""
Tests for the fingerprinting engine.
"""
import pytest
from cybex_pulse.fingerprinting.engine import FingerprintEngine


def test_engine_initialization():
    """Test that the engine initializes properly and loads device modules."""
    engine = FingerprintEngine()
    assert len(engine.signatures) > 0
    assert len(engine.device_modules) > 0


def test_identify_unifi_device(unifi_udm_device_data):
    """Test identification of UniFi device."""
    engine = FingerprintEngine()
    matches = engine.identify_device(unifi_udm_device_data)
    
    assert len(matches) > 0
    
    # Best match should be a UniFi device
    best_match = matches[0]
    assert 'unifi' in best_match['signature_id']
    assert best_match['manufacturer'] == 'Ubiquiti'
    assert best_match['device_type'] == 'Router'
    assert best_match['confidence'] > 0.7  # High confidence


def test_identify_synology_device(synology_nas_device_data):
    """Test identification of Synology NAS device."""
    engine = FingerprintEngine()
    matches = engine.identify_device(synology_nas_device_data)
    
    assert len(matches) > 0
    
    # Best match should be a Synology device
    best_match = matches[0]
    assert 'synology' in best_match['signature_id']
    assert best_match['manufacturer'] == 'Synology'
    assert best_match['device_type'] == 'NAS'
    assert best_match['confidence'] > 0.7  # High confidence
    
    # Check that the correct model is identified
    assert 'ds920plus' in best_match['signature_id'].lower()


def test_identify_shelly_device(shelly_plug_device_data):
    """Test identification of Shelly smart home device."""
    engine = FingerprintEngine()
    matches = engine.identify_device(shelly_plug_device_data)
    
    assert len(matches) > 0
    
    # Best match should be a Shelly device
    best_match = matches[0]
    assert 'shelly' in best_match['signature_id']
    assert best_match['manufacturer'] == 'Shelly'
    assert best_match['confidence'] > 0.5  # Moderate confidence


def test_identify_roku_device(roku_device_data):
    """Test identification of Roku media device."""
    engine = FingerprintEngine()
    matches = engine.identify_device(roku_device_data)
    
    assert len(matches) > 0
    
    # Best match should be a Roku device
    best_match = matches[0]
    assert 'roku' in best_match['signature_id']
    assert best_match['manufacturer'] == 'Roku'
    assert best_match['device_type'] == 'Media Player'
    assert best_match['confidence'] > 0.5  # Moderate confidence


def test_identify_printer_device(printer_device_data):
    """Test identification of HP printer device."""
    engine = FingerprintEngine()
    matches = engine.identify_device(printer_device_data)
    
    assert len(matches) > 0
    
    # Best match should be an HP printer
    best_match = matches[0]
    assert 'hp' in best_match['signature_id']
    assert best_match['manufacturer'] == 'HP'
    assert best_match['device_type'] == 'Printer'
    assert best_match['confidence'] > 0.7  # High confidence


def test_unknown_device(unknown_device_data):
    """Test handling of unknown device."""
    engine = FingerprintEngine()
    matches = engine.identify_device(unknown_device_data)
    
    # There might be some low-confidence matches
    if matches:
        assert matches[0]['confidence'] < 0.4  # Low confidence for unknown device


def test_similar_device(similar_device_data):
    """Test handling of device with characteristics similar to multiple devices."""
    engine = FingerprintEngine()
    matches = engine.identify_device(similar_device_data)
    
    # Should match an Epson printer with medium confidence due to MAC and SNMP
    assert len(matches) > 0
    assert matches[0]['manufacturer'] == 'Epson'
    
    # Check if there are multiple possible matches with similar confidence
    if len(matches) > 1:
        # Confidence difference between top matches should be small
        confidence_diff = matches[0]['confidence'] - matches[1]['confidence']
        assert confidence_diff < 0.3  # Small difference in confidence
    
    
def test_partial_data():
    """Test identification with partial device data."""
    # Only MAC address
    mac_only = {
        'ip_address': '192.168.1.10',
        'mac_address': 'B4:FB:E4:11:22:33',  # UniFi MAC
        'open_ports': [],
        'http_headers': {},
        'snmp_data': {},
        'mdns_data': {}
    }
    
    engine = FingerprintEngine()
    matches = engine.identify_device(mac_only)
    
    # Should have at least one match based on MAC OUI
    assert len(matches) > 0
    assert 'ubiquiti' in matches[0]['manufacturer'].lower()
    assert matches[0]['confidence'] < 0.5  # Low confidence with MAC only
    
    
def test_confidence_scoring():
    """Test confidence scoring with varying levels of match data."""
    engine = FingerprintEngine()
    
    # Create device data with varying levels of matching characteristics
    full_match = {
        'ip_address': '192.168.1.5',
        'mac_address': '00:18:71:FD:EC:BA',  # HP MAC
        'open_ports': [80, 443, 515, 631, 9100],  # HP printer ports
        'http_headers': {
            'Server': 'HP-ChaiSOE/1.0',  # HP server
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'HP LaserJet Pro MFP M428fdw',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.11'
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'HP LaserJet Pro MFP M428fdw'
        }
    }
    
    partial_match = {
        'ip_address': '192.168.1.5',
        'mac_address': '00:18:71:FD:EC:BA',  # HP MAC
        'open_ports': [80, 443],  # Some common ports, missing specific printer ports
        'http_headers': {
            'Server': 'HP-ChaiSOE/1.0',  # HP server
        },
        'snmp_data': {},  # Missing SNMP data
        'mdns_data': {}  # Missing mDNS data
    }
    
    minimal_match = {
        'ip_address': '192.168.1.5',
        'mac_address': '00:18:71:FD:EC:BA',  # HP MAC
        'open_ports': [80],  # Just a common port
        'http_headers': {},  # No HTTP data
        'snmp_data': {},  # No SNMP data
        'mdns_data': {}  # No mDNS data
    }
    
    full_results = engine.identify_device(full_match)
    partial_results = engine.identify_device(partial_match)
    minimal_results = engine.identify_device(minimal_match)
    
    # Confirm we're getting HP printer as the top match in all cases
    assert 'hp' in full_results[0]['signature_id']
    assert 'hp' in partial_results[0]['signature_id']
    assert 'hp' in minimal_results[0]['signature_id']
    
    # Compare confidence scores - should decrease with less matching data
    assert full_results[0]['confidence'] > partial_results[0]['confidence']
    assert partial_results[0]['confidence'] > minimal_results[0]['confidence']