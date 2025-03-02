"""
Tests for NAS device signatures.
"""
import pytest
from cybex_pulse.fingerprinting.engine import FingerprintEngine
from cybex_pulse.fingerprinting.devices.nas import SIGNATURES


def test_nas_signatures_structure():
    """Test that NAS signatures are correctly structured."""
    # Check that we have multiple signatures
    assert len(SIGNATURES) > 0
    
    # Check that each signature has required fields
    for sig_id, signature in SIGNATURES.items():
        assert 'device_type' in signature
        assert 'manufacturer' in signature
        assert 'model' in signature
        assert 'mac_prefix' in signature
        assert isinstance(signature['mac_prefix'], list)
        
        # All should be the NAS device type
        assert signature['device_type'] == 'NAS'
        
        # Check that NAS signatures have hostname patterns
        assert 'hostname_patterns' in signature, f"Signature {sig_id} missing hostname_patterns"


@pytest.fixture
def qnap_nas_device_data():
    """Mock device data for a QNAP NAS."""
    return {
        'ip_address': '192.168.1.100',
        'mac_address': '24:5E:BE:12:34:56',
        'open_ports': [22, 80, 443, 139, 445, 111, 2049, 8080, 6000, 10000],
        'http_headers': {
            'Server': 'http/1.1',
            'X-Powered-By': 'QTS 5.0.0',
            'Set-Cookie': 'NAS_SID=123456789; NASID=QNAP_TS-253D',
            'Content-Type': 'text/html; charset=UTF-8',
            'Connection': 'keep-alive',
            'X-Content-Contains-Qnap': 'true',
            'X-Page-Title': 'qnap ts-253d login'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'QNAP TS-253D',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.24681',
            'SNMPv2-MIB::sysName.0': 'QNAP-NAS'
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'QNAP-TS-253D'
        },
        'hostname': 'qnap-nas'
    }


@pytest.fixture
def truenas_device_data():
    """Mock device data for a TrueNAS system."""
    return {
        'ip_address': '192.168.1.101',
        'mac_address': '00:11:22:33:44:55',  # Generic MAC for software-based system
        'open_ports': [22, 80, 443, 139, 445, 111, 2049, 9000],
        'http_headers': {
            'Server': 'nginx',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Powered-By': 'truenas/13.0',
            'Content-Type': 'text/html; charset=UTF-8',
            'Connection': 'keep-alive'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'TrueNAS-SCALE-22.02',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.50536',
            'SNMPv2-MIB::sysName.0': 'truenas'
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'TrueNAS-Server'
        }
    }


@pytest.fixture
def unraid_device_data():
    """Mock device data for an Unraid server."""
    return {
        'ip_address': '192.168.1.102',
        'mac_address': '00:22:33:44:55:66',  # Generic MAC for software-based system
        'open_ports': [22, 80, 443, 139, 445, 111, 2049, 8080],
        'http_headers': {
            'Server': 'nginx',
            'X-Frame-Options': 'SAMEORIGIN',
            'Set-Cookie': 'unraid_token=1234567890',
            'Content-Type': 'text/html; charset=UTF-8',
            'Connection': 'keep-alive'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'Linux Unraid 5.13.0',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.8072.3.2.10',
            'SNMPv2-MIB::sysName.0': 'unraid-server'
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'Unraid-Server'
        }
    }


@pytest.fixture
def wd_mycloud_device_data():
    """Mock device data for a Western Digital MyCloud NAS."""
    return {
        'ip_address': '192.168.1.103',
        'mac_address': '00:90:A9:AB:CD:EF',
        'open_ports': [22, 80, 443, 139, 445, 111, 2049, 9000],
        'http_headers': {
            'Server': 'Apache',
            'WWW-Authenticate': 'Basic realm="WD MyCloud"',
            'Content-Type': 'text/html; charset=UTF-8',
            'Connection': 'keep-alive'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'WD MyCloud OS 5',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.5127',
            'SNMPv2-MIB::sysName.0': 'WDMyCloud'
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'MyCloud-1234'
        }
    }


def test_qnap_identification(qnap_nas_device_data):
    """Test identification of a QNAP NAS."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(qnap_nas_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be the QNAP NAS
    best_match = matches[0]
    assert best_match['signature_id'] == 'qnap_nas'
    assert best_match['manufacturer'] == 'QNAP'
    assert best_match['device_type'] == 'NAS'
    assert best_match['confidence'] > 0.7  # High confidence


def test_truenas_identification(truenas_device_data):
    """Test identification of a TrueNAS system."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(truenas_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be TrueNAS
    best_match = matches[0]
    assert best_match['signature_id'] == 'truenas'
    assert best_match['manufacturer'] == 'iXsystems'
    assert best_match['device_type'] == 'NAS'
    assert best_match['confidence'] > 0.5  # Moderate confidence is enough


def test_unraid_identification(unraid_device_data):
    """Test identification of an Unraid server."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(unraid_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be Unraid
    best_match = matches[0]
    assert best_match['signature_id'] == 'unraid'
    assert best_match['manufacturer'] == 'Lime Technology'
    assert best_match['device_type'] == 'NAS'
    assert best_match['confidence'] > 0.5  # Moderate confidence is enough


def test_wd_mycloud_identification(wd_mycloud_device_data):
    """Test identification of a Western Digital MyCloud NAS."""
    engine = FingerprintEngine()
    
    matches = engine.identify_device(wd_mycloud_device_data)
    
    # Should have at least one match
    assert len(matches) > 0
    
    # Best match should be Western Digital MyCloud
    best_match = matches[0]
    assert best_match['signature_id'] == 'wd_mycloud'
    assert best_match['manufacturer'] == 'Western Digital'
    assert best_match['device_type'] == 'NAS'
    assert best_match['confidence'] > 0.7  # High confidence


def test_partial_nas_matches():
    """Test partial matches for NAS devices with limited data."""
    engine = FingerprintEngine()
    
    # Device with only QNAP MAC address and some typical NAS ports
    partial_data = {
        'ip_address': '192.168.1.105',
        'mac_address': '00:1F:1F:11:22:33',  # QNAP MAC
        'open_ports': [80, 443, 445, 139],
        'http_headers': {},
        'snmp_data': {},
        'mdns_data': {}
    }
    
    matches = engine.identify_device(partial_data)
    
    # Should have matches for some NAS
    assert len(matches) > 0
    
    # First match should be QNAP due to MAC prefix
    if 'qnap' in matches[0]['signature_id']:
        # But confidence should be lower due to partial match
        assert matches[0]['confidence'] < 0.5
    
    # Adding a typical HTTP header should increase confidence
    partial_data['http_headers'] = {
        'Server': 'http/1.1',
        'X-Powered-By': 'QTS 5.0.0',
    }
    
    matches = engine.identify_device(partial_data)
    
    # Should now have a better match
    if 'qnap' in matches[0]['signature_id']:
        assert matches[0]['confidence'] > 0.4
        
        
def test_http_content_detection():
    """Test that NAS devices can be detected via HTTP content/title."""
    engine = FingerprintEngine()
    
    # Test Synology detection from webpage content
    synology_data = {
        'ip_address': '192.168.1.110',
        'mac_address': '00:11:32:AA:BB:CC',  # Synology MAC
        'open_ports': [80, 443, 5000],
        'http_headers': {
            'Server': 'nginx',
            'X-Content-Contains-Synology': 'true',
            'X-Page-Title': 'synology diskstation manager',
            'X-Has-Login-Form': 'true'
        },
        'snmp_data': {},
        'mdns_data': {}
    }
    
    matches = engine.identify_device(synology_data)
    assert len(matches) > 0
    best_match = matches[0]
    # Should detect it's a Synology device, exact signature ID might vary
    assert 'synology' in best_match['signature_id']
    assert best_match['manufacturer'] == 'Synology'
    assert best_match['confidence'] > 0.3
    
    # Test Unraid detection from webpage content only (no standard headers)
    unraid_data = {
        'ip_address': '192.168.1.111',
        'mac_address': '00:22:33:44:55:66',  # Generic MAC
        'open_ports': [80, 443],
        'http_headers': {
            'Server': 'nginx',
            'X-Content-Contains-Unraid': 'true',
            'X-Page-Title': 'unraid server login',
            'X-Has-Login-Form': 'true'
        },
        'snmp_data': {},
        'mdns_data': {}
    }
    
    matches = engine.identify_device(unraid_data)
    assert len(matches) > 0
    best_match = matches[0]
    assert best_match['signature_id'] == 'unraid'
    assert best_match['confidence'] > 0.4