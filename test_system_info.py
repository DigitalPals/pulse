#!/usr/bin/env python3
"""
Test script to verify that the system_info module is working correctly.
"""
import sys
import traceback

try:
    print("Importing system_info functions...")
    from cybex_pulse.utils.system_info import get_cpu_info, get_memory_info, get_all_system_info
    
    print("\nTesting get_cpu_info()...")
    cpu_info = get_cpu_info()
    print(f"CPU Info: {cpu_info}")
    
    print("\nTesting get_memory_info()...")
    memory_info = get_memory_info()
    print(f"Memory Info: {memory_info}")
    
    print("\nTesting get_all_system_info()...")
    all_info = get_all_system_info()
    print(f"All System Info Keys: {list(all_info.keys())}")
    
    print("\nAll tests passed successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    print("\nTraceback:")
    traceback.print_exc()
    sys.exit(1)