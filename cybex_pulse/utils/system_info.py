"""
System information utilities for Cybex Pulse.
"""
import os
import psutil
import platform
import time
from typing import Dict, Any, List, Tuple

# Cache for CPU model information to avoid repeated lookups
_cpu_model_cache = None
_cpu_count_cache = None
_physical_cores_cache = None

# Cache for CPU usage to avoid spikes in measurements
_last_cpu_percent = 0
_last_cpu_check_time = 0
_CPU_CACHE_TTL = 0.5  # Cache CPU usage for 0.5 seconds

def get_cpu_info() -> Dict[str, Any]:
    """
    Get CPU information.
    
    Returns:
        Dict[str, Any]: Dictionary with CPU information
    """
    global _cpu_model_cache, _cpu_count_cache, _physical_cores_cache
    global _last_cpu_percent, _last_cpu_check_time
    
    try:
        current_time = time.time()
        
        # Use cached CPU percentage if recent enough
        if current_time - _last_cpu_check_time <= _CPU_CACHE_TTL:
            cpu_percent = _last_cpu_percent
        else:
            # Get CPU usage percentage without blocking (interval=0)
            # This returns the usage since the last call, or 0 on first call
            cpu_percent = psutil.cpu_percent(interval=0)
            _last_cpu_percent = cpu_percent
            _last_cpu_check_time = current_time
        
        # Cache CPU count and cores to avoid repeated calls
        if _cpu_count_cache is None:
            _cpu_count_cache = psutil.cpu_count(logical=True) or 1
        cpu_count = _cpu_count_cache
        
        if _physical_cores_cache is None:
            _physical_cores_cache = psutil.cpu_count(logical=False) or 1
        physical_cores = _physical_cores_cache
        
        # Calculate normalized CPU percentage based on number of cores
        normalized_percent = min(100, cpu_percent / cpu_count * 100) if cpu_count > 0 and cpu_percent > 0 else cpu_percent
        
        # Get CPU frequency - only if needed and not too frequently
        current_freq = None
        if current_time % 5 < 1:  # Only check every ~5 seconds
            try:
                cpu_freq = psutil.cpu_freq()
                current_freq = cpu_freq.current if cpu_freq else None
            except Exception:
                # Ignore errors with CPU frequency
                pass
        
        # Get CPU load average (1, 5, 15 minutes) - only if needed
        load_avg = None
        normalized_load_avg = None
        if hasattr(os, 'getloadavg'):
            try:
                load_avg = os.getloadavg()
                # Normalize load average by number of cores
                normalized_load_avg = [round(load / cpu_count * 100, 2) for load in load_avg]
            except Exception:
                # Ignore errors with load average
                pass
        
        # Get CPU model name (use cached value if available)
        if _cpu_model_cache is None:
            try:
                if platform.system() == "Linux":
                    with open('/proc/cpuinfo', 'r') as f:
                        for line in f:
                            if line.strip():
                                if line.rstrip('\n').startswith('model name'):
                                    model_name = line.rstrip('\n').split(':')[1].strip()
                                    _cpu_model_cache = model_name
                                    break
                elif platform.system() == "Darwin":  # macOS
                    import subprocess
                    output = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string']).decode().strip()
                    _cpu_model_cache = output
                else:
                    _cpu_model_cache = platform.processor()
                
                # If we couldn't determine the model, use a default
                if not _cpu_model_cache:
                    _cpu_model_cache = platform.processor() or "Unknown CPU"
            except Exception as e:
                _cpu_model_cache = f"Unknown (Error: {str(e)})"
        
        return {
            "percent": normalized_percent,  # Use normalized percentage
            "raw_percent": cpu_percent,     # Keep the raw percentage for reference
            "count": cpu_count,
            "physical_cores": physical_cores,
            "current_freq": current_freq,
            "load_avg": load_avg,
            "normalized_load_avg": normalized_load_avg,  # Add normalized load average
            "model": _cpu_model_cache
        }
    except Exception as e:
        return {
            "error": str(e)
        }

# Cache for memory information
_memory_info_cache = None
_last_memory_check_time = 0
_MEMORY_CACHE_TTL = 2  # Cache memory info for 2 seconds

def get_memory_info() -> Dict[str, Any]:
    """
    Get memory information.
    
    Returns:
        Dict[str, Any]: Dictionary with memory information
    """
    global _memory_info_cache, _last_memory_check_time
    
    try:
        current_time = time.time()
        
        # Use cached memory info if recent enough
        if current_time - _last_memory_check_time <= _MEMORY_CACHE_TTL and _memory_info_cache:
            return _memory_info_cache
        
        # Get virtual memory information
        mem = psutil.virtual_memory()
        
        # Get swap memory information - only if needed
        swap_info = {"total": 0, "used": 0, "percent": 0}
        try:
            swap = psutil.swap_memory()
            swap_info = {
                "total": swap.total,
                "used": swap.used,
                "percent": swap.percent
            }
        except Exception:
            # Ignore errors with swap memory
            pass
        
        # Create result
        result = {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent,
            "swap_total": swap_info["total"],
            "swap_used": swap_info["used"],
            "swap_percent": swap_info["percent"]
        }
        
        # Update cache
        _memory_info_cache = result
        _last_memory_check_time = current_time
        
        return result
    except Exception as e:
        return {
            "error": str(e)
        }

# Cache for disk information
_disk_info_cache = None
_last_disk_check_time = 0
_DISK_CACHE_TTL = 5  # Cache disk info for 5 seconds (disk usage changes slowly)

def get_disk_info() -> Dict[str, Any]:
    """
    Get disk information.
    
    Returns:
        Dict[str, Any]: Dictionary with disk information
    """
    global _disk_info_cache, _last_disk_check_time
    
    try:
        current_time = time.time()
        
        # Use cached disk info if recent enough
        if current_time - _last_disk_check_time <= _DISK_CACHE_TTL and _disk_info_cache:
            return _disk_info_cache
        
        # Get disk usage for root partition
        disk = psutil.disk_usage('/')
        
        # Get disk I/O statistics - only if needed and not too frequently
        io_info = {"read_count": None, "write_count": None, "read_bytes": None, "write_bytes": None}
        if current_time % 10 < 1:  # Only check every ~10 seconds
            try:
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    io_info = {
                        "read_count": disk_io.read_count,
                        "write_count": disk_io.write_count,
                        "read_bytes": disk_io.read_bytes,
                        "write_bytes": disk_io.write_bytes
                    }
            except Exception:
                # Ignore errors with disk I/O
                pass
        
        # Create result
        result = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "read_count": io_info["read_count"],
            "write_count": io_info["write_count"],
            "read_bytes": io_info["read_bytes"],
            "write_bytes": io_info["write_bytes"]
        }
        
        # Update cache
        _disk_info_cache = result
        _last_disk_check_time = current_time
        
        return result
    except Exception as e:
        return {
            "error": str(e)
        }

# Cache for network interfaces to avoid repeated lookups
_network_interfaces_cache = None
_last_interfaces_update = 0
_INTERFACES_CACHE_TTL = 60  # Cache network interfaces for 60 seconds

# Cache for network I/O statistics
_network_io_cache = None
_last_network_io_update = 0
_NETWORK_IO_CACHE_TTL = 1  # Cache network I/O for 1 second

def get_network_info() -> Dict[str, Any]:
    """
    Get network information.
    
    Returns:
        Dict[str, Any]: Dictionary with network information
    """
    global _network_interfaces_cache, _last_interfaces_update
    global _network_io_cache, _last_network_io_update
    
    try:
        current_time = time.time()
        
        # Get network I/O statistics (use cached value if available and not expired)
        if _network_io_cache is None or (current_time - _last_network_io_update) > _NETWORK_IO_CACHE_TTL:
            try:
                net_io = psutil.net_io_counters()
                _network_io_cache = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                }
                _last_network_io_update = current_time
            except Exception:
                # Use default values if there's an error
                if _network_io_cache is None:
                    _network_io_cache = {
                        "bytes_sent": 0,
                        "bytes_recv": 0,
                        "packets_sent": 0,
                        "packets_recv": 0
                    }
        
        # Skip the expensive network connections count entirely
        connections = 0
        
        # Get network interfaces (use cached value if available and not expired)
        if _network_interfaces_cache is None or (current_time - _last_interfaces_update) > _INTERFACES_CACHE_TTL:
            try:
                interfaces = []
                for interface, addrs in psutil.net_if_addrs().items():
                    mac = None
                    ipv4 = None
                    
                    for addr in addrs:
                        if addr.family == psutil.AF_LINK:  # MAC address
                            mac = addr.address
                        elif addr.family == 2:  # IPv4
                            ipv4 = addr.address
                    
                    if ipv4:  # Only add interfaces with IPv4 addresses
                        interfaces.append({
                            "name": interface,
                            "mac": mac,
                            "ipv4": ipv4
                        })
                
                _network_interfaces_cache = interfaces
                _last_interfaces_update = current_time
            except Exception:
                # Use empty list if there's an error
                if _network_interfaces_cache is None:
                    _network_interfaces_cache = []
        
        return {
            "bytes_sent": _network_io_cache["bytes_sent"],
            "bytes_recv": _network_io_cache["bytes_recv"],
            "packets_sent": _network_io_cache["packets_sent"],
            "packets_recv": _network_io_cache["packets_recv"],
            "connections": connections,
            "interfaces": _network_interfaces_cache
        }
    except Exception as e:
        return {
            "error": str(e)
        }

def get_system_uptime() -> Dict[str, Any]:
    """
    Get system uptime.
    
    Returns:
        Dict[str, Any]: Dictionary with system uptime information
    """
    try:
        # Get boot time
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        
        # Calculate days, hours, minutes, seconds
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return {
            "boot_time": boot_time,
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
        }
    except Exception as e:
        return {
            "error": str(e)
        }

# Cache for complete system info
_all_system_info_cache = None
_last_all_info_update = 0
_ALL_INFO_CACHE_TTL = 1  # Cache all system info for 1 second

def get_all_system_info() -> Dict[str, Dict[str, Any]]:
    """
    Get all system information.
    
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary with all system information
    """
    global _all_system_info_cache, _last_all_info_update
    
    current_time = time.time()
    
    # Use cached info if recent enough
    if _all_system_info_cache is not None and (current_time - _last_all_info_update) <= _ALL_INFO_CACHE_TTL:
        return _all_system_info_cache
    
    # Get platform info only once per application run
    platform_info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor()
    }
    
    # Collect all system information
    result = {
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),
        "network": get_network_info(),
        "uptime": get_system_uptime(),
        "platform": platform_info
    }
    
    # Update cache
    _all_system_info_cache = result
    _last_all_info_update = current_time
    
    return result