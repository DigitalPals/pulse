#!/usr/bin/env python3
"""
Test script for device fingerprinting functionality.
Lists all available modules and signatures.
"""
import os
import sys
import json

# Ensure the Pulse package is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from cybex_pulse.fingerprinting.engine import FingerprintEngine
    
    # Initialize the fingerprinting engine
    engine = FingerprintEngine()
    
    # Get loaded modules and count signatures
    modules = engine.get_available_modules()
    total_signatures = engine.get_signature_count()
    
    print(f"Loaded {len(modules)} device modules with {total_signatures} total signatures:")
    print("-" * 60)
    
    # Print details for each module
    for module_name in sorted(modules):
        module_obj = engine.device_modules[module_name]
        if hasattr(module_obj, 'SIGNATURES'):
            signatures = module_obj.SIGNATURES
            device_types = set(sig['device_type'] for sig in signatures.values())
            manufacturers = set(sig['manufacturer'] for sig in signatures.values())
            
            print(f"{module_name.capitalize()} Module:")
            print(f"  Signatures: {len(signatures)}")
            print(f"  Device Types: {', '.join(sorted(device_types))}")
            print(f"  Manufacturers: {', '.join(sorted(manufacturers))}")
            print()
    
    # Test with mock device data
    test_device = {
        'ip_address': '192.168.1.1',
        'mac_address': 'B4:FB:E4:5A:11:22',  # UniFi MAC
        'open_ports': [22, 80, 443, 8080, 8443],
        'http_headers': {
            'Server': 'UniFi',
            'X-Frame-Options': 'SAMEORIGIN',
            'Content-Type': 'text/html'
        },
        'snmp_data': {
            'SNMPv2-MIB::sysDescr.0': 'UniFi Dream Machine',
            'SNMPv2-MIB::sysObjectID.0': '1.3.6.1.4.1.41112'
        },
        'mdns_data': {
            'service_type': '_http._tcp',
            'service_name': 'UniFi'
        }
    }
    
    print("Testing fingerprinting with mock UniFi device data:")
    print("-" * 60)
    matches = engine.identify_device(test_device)
    
    if matches:
        print(f"Found {len(matches)} potential matches:")
        for i, match in enumerate(matches[:5], 1):  # Show top 5 matches
            print(f"{i}. {match['manufacturer']} {match['model']} ({match['device_type']})")
            print(f"   Signature: {match['signature_id']}")
            print(f"   Confidence: {match['confidence']:.2f}")
    else:
        print("No matches found!")

except ImportError as e:
    print(f"Error importing fingerprinting modules: {e}")
    sys.exit(1)