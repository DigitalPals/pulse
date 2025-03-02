"""
Tests for the fingerprinting scanner.
"""
import pytest
import socket
from unittest.mock import patch, MagicMock
from cybex_pulse.fingerprinting.scanner import DeviceFingerprinter


@pytest.fixture
def mock_socket():
    """Mock socket for port scanning."""
    with patch('socket.socket') as mock:
        sock_instance = MagicMock()
        mock.return_value = sock_instance
        sock_instance.connect_ex.return_value = 0  # Port is open
        yield mock


@pytest.fixture
def mock_requests():
    """Mock requests for HTTP headers."""
    with patch('requests.head') as mock:
        response = MagicMock()
        response.status_code = 200
        response.headers = {
            'Server': 'Test Server',
            'Content-Type': 'text/html'
        }
        mock.return_value = response
        yield mock


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for SNMP and mDNS data."""
    with patch('subprocess.run') as mock:
        result = MagicMock()
        result.returncode = 0
        result.stdout = "SNMPv2-MIB::sysDescr.0 :: Test System Description"
        mock.return_value = result
        yield mock


def test_fingerprinter_initialization():
    """Test that fingerprinter initializes properly."""
    fingerprinter = DeviceFingerprinter()
    assert fingerprinter.engine is not None
    assert fingerprinter.timeout == 2  # Default timeout
    assert fingerprinter.max_threads == 10  # Default max threads


def test_check_port(mock_socket):
    """Test port checking."""
    fingerprinter = DeviceFingerprinter()
    is_open = fingerprinter._check_port('192.168.1.1', 80)
    
    assert is_open is True
    mock_socket.assert_called_once()
    mock_socket.return_value.settimeout.assert_called_once()
    mock_socket.return_value.connect_ex.assert_called_once_with(('192.168.1.1', 80))
    mock_socket.return_value.close.assert_called_once()


def test_scan_ports(mock_socket):
    """Test port scanning."""
    fingerprinter = DeviceFingerprinter()
    open_ports = fingerprinter._scan_ports('192.168.1.1', [80, 443, 22])
    
    assert 80 in open_ports
    assert 443 in open_ports
    assert 22 in open_ports
    assert len(open_ports) == 3
    assert mock_socket.call_count == 3


def test_get_http_headers(mock_requests):
    """Test HTTP header retrieval."""
    fingerprinter = DeviceFingerprinter()
    headers = fingerprinter._get_http_headers('192.168.1.1')
    
    assert 'Server' in headers
    assert headers['Server'] == 'Test Server'
    assert 'Content-Type' in headers
    assert headers['Content-Type'] == 'text/html'
    
    # Should try both HTTP and HTTPS
    assert mock_requests.call_count == 2


@patch('requests.head', side_effect=Exception("Connection error"))
def test_get_http_headers_error(mock_requests):
    """Test error handling in HTTP header retrieval."""
    fingerprinter = DeviceFingerprinter()
    headers = fingerprinter._get_http_headers('192.168.1.1')
    
    assert headers == {}
    assert mock_requests.call_count == 2


def test_get_snmp_data(mock_subprocess):
    """Test SNMP data retrieval."""
    fingerprinter = DeviceFingerprinter()
    snmp_data = fingerprinter._get_snmp_data('192.168.1.1')
    
    assert 'SNMPv2-MIB::sysDescr.0' in snmp_data
    assert snmp_data['SNMPv2-MIB::sysDescr.0'] == 'Test System Description'
    mock_subprocess.assert_called_once()


@patch('subprocess.run', side_effect=Exception("Command error"))
def test_get_snmp_data_error(mock_subprocess):
    """Test error handling in SNMP data retrieval."""
    fingerprinter = DeviceFingerprinter()
    snmp_data = fingerprinter._get_snmp_data('192.168.1.1')
    
    assert snmp_data == {}
    mock_subprocess.assert_called_once()


def test_get_mdns_data(mock_subprocess):
    """Test mDNS data retrieval."""
    mock_subprocess.return_value.stdout = "device.local"
    fingerprinter = DeviceFingerprinter()
    mdns_data = fingerprinter._get_mdns_data('192.168.1.1')
    
    assert 'hostname' in mdns_data
    assert mdns_data['hostname'] == 'device.local'
    mock_subprocess.assert_called()


@patch('subprocess.run', side_effect=Exception("Command error"))
def test_get_mdns_data_error(mock_subprocess):
    """Test error handling in mDNS data retrieval."""
    fingerprinter = DeviceFingerprinter()
    mdns_data = fingerprinter._get_mdns_data('192.168.1.1')
    
    assert mdns_data == {}
    mock_subprocess.assert_called_once()


@patch('cybex_pulse.fingerprinting.scanner.DeviceFingerprinter._scan_ports')
@patch('cybex_pulse.fingerprinting.scanner.DeviceFingerprinter._get_http_headers')
@patch('cybex_pulse.fingerprinting.scanner.DeviceFingerprinter._get_snmp_data')
@patch('cybex_pulse.fingerprinting.scanner.DeviceFingerprinter._get_mdns_data')
@patch('cybex_pulse.fingerprinting.engine.FingerprintEngine.identify_device')
def test_fingerprint_device(mock_identify, mock_mdns, mock_snmp, mock_http, mock_ports):
    """Test full device fingerprinting."""
    # Mock return values
    mock_ports.return_value = [80, 443]
    mock_http.return_value = {'Server': 'Test'}
    mock_snmp.return_value = {'SNMPv2-MIB::sysDescr.0': 'Test'}
    mock_mdns.return_value = {'hostname': 'test'}
    mock_identify.return_value = [{'signature_id': 'test', 'confidence': 0.8}]
    
    fingerprinter = DeviceFingerprinter()
    result = fingerprinter.fingerprint_device('192.168.1.1', '00:11:22:33:44:55')
    
    # Check that all needed functions were called
    mock_ports.assert_called_once()
    mock_http.assert_called_once()
    mock_snmp.assert_called_once()
    mock_mdns.assert_called_once()
    mock_identify.assert_called_once()
    
    # Check that result contains expected data
    assert result['ip_address'] == '192.168.1.1'
    assert result['mac_address'] == '00:11:22:33:44:55'
    assert result['open_ports'] == [80, 443]
    assert result['http_headers'] == {'Server': 'Test'}
    assert result['snmp_data'] == {'SNMPv2-MIB::sysDescr.0': 'Test'}
    assert result['mdns_data'] == {'hostname': 'test'}
    assert result['identification'] == [{'signature_id': 'test', 'confidence': 0.8}]


@patch('cybex_pulse.fingerprinting.scanner.DeviceFingerprinter.fingerprint_device')
def test_fingerprint_network(mock_fingerprint_device):
    """Test fingerprinting multiple network devices."""
    mock_fingerprint_device.side_effect = [
        {'ip_address': '192.168.1.1', 'identification': [{'confidence': 0.9}]},
        {'ip_address': '192.168.1.2', 'identification': [{'confidence': 0.8}]},
        Exception("Test error")  # Simulate an error for one device
    ]
    
    devices = [
        {'ip_address': '192.168.1.1', 'mac_address': '00:11:22:33:44:55'},
        {'ip_address': '192.168.1.2', 'mac_address': '00:11:22:33:44:66'},
        {'ip_address': '192.168.1.3', 'mac_address': '00:11:22:33:44:77'}
    ]
    
    fingerprinter = DeviceFingerprinter()
    results = fingerprinter.fingerprint_network(devices)
    
    # Should have 2 successful results (third device raised exception)
    assert len(results) == 2
    assert results[0]['ip_address'] == '192.168.1.1'
    assert results[1]['ip_address'] == '192.168.1.2'
    
    # Should have called fingerprint_device for each device
    assert mock_fingerprint_device.call_count == 3