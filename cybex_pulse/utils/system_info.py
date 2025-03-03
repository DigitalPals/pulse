"""
System information utilities for Cybex Pulse.
"""
import os
import psutil
import platform
import time
from typing import Dict, Any, List, Tuple

def get_cpu_info() -> Dict[str, Any]:
    """
    Get CPU information.
    
    Returns:
        Dict[str, Any]: Dictionary with CPU information
    """
    try:
        # Get CPU usage percentage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get CPU count
        cpu_count = psutil.cpu_count(logical=True) or 1  # Default to 1 if None
        physical_cores = psutil.cpu_count(logical=False) or 1  # Default to 1 if None
        
        # Calculate normalized CPU percentage based on number of cores
        # This gives a more accurate representation in virtualized environments
        normalized_percent = min(100, cpu_percent / cpu_count * 100) if cpu_count > 0 else cpu_percent
        
        # Get CPU frequency
        cpu_freq = psutil.cpu_freq()
        current_freq = cpu_freq.current if cpu_freq else None
        
        # Get CPU load average (1, 5, 15 minutes)
        load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else None
        
        # Normalize load average by number of cores
        normalized_load_avg = None
        if load_avg:
            normalized_load_avg = [round(load / cpu_count * 100, 2) for load in load_avg]
        
        # Get CPU model name
        cpu_info = {}
        try:
            if platform.system() == "Linux":
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.strip():
                            if line.rstrip('\n').startswith('model name'):
                                model_name = line.rstrip('\n').split(':')[1].strip()
                                cpu_info['model'] = model_name
                                break
            elif platform.system() == "Darwin":  # macOS
                import subprocess
                output = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string']).decode().strip()
                cpu_info['model'] = output
            else:
                cpu_info['model'] = platform.processor()
        except Exception as e:
            cpu_info['model'] = f"Unknown (Error: {str(e)})"
        
        return {
            "percent": normalized_percent,  # Use normalized percentage
            "raw_percent": cpu_percent,     # Keep the raw percentage for reference
            "count": cpu_count,
            "physical_cores": physical_cores,
            "current_freq": current_freq,
            "load_avg": load_avg,
            "normalized_load_avg": normalized_load_avg,  # Add normalized load average
            "model": cpu_info.get('model', platform.processor())
        }
    except Exception as e:
        return {
            "error": str(e)
        }

def get_memory_info() -> Dict[str, Any]:
    """
    Get memory information.
    
    Returns:
        Dict[str, Any]: Dictionary with memory information
    """
    try:
        # Get virtual memory information
        mem = psutil.virtual_memory()
        
        # Get swap memory information
        swap = psutil.swap_memory()
        
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent
        }
    except Exception as e:
        return {
            "error": str(e)
        }

def get_disk_info() -> Dict[str, Any]:
    """
    Get disk information.
    
    Returns:
        Dict[str, Any]: Dictionary with disk information
    """
    try:
        # Get disk usage for root partition
        disk = psutil.disk_usage('/')
        
        # Get disk I/O statistics
        disk_io = psutil.disk_io_counters()
        
        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "read_count": disk_io.read_count if disk_io else None,
            "write_count": disk_io.write_count if disk_io else None,
            "read_bytes": disk_io.read_bytes if disk_io else None,
            "write_bytes": disk_io.write_bytes if disk_io else None
        }
    except Exception as e:
        return {
            "error": str(e)
        }

def get_network_info() -> Dict[str, Any]:
    """
    Get network information.
    
    Returns:
        Dict[str, Any]: Dictionary with network information
    """
    try:
        # Get network I/O statistics
        net_io = psutil.net_io_counters()
        
        # Get network connections count
        connections = len(psutil.net_connections())
        
        # Get network interfaces
        interfaces = []
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == psutil.AF_LINK:  # MAC address
                    mac = addr.address
                elif addr.family == 2:  # IPv4
                    ipv4 = addr.address
                    interfaces.append({
                        "name": interface,
                        "mac": mac if 'mac' in locals() else None,
                        "ipv4": ipv4
                    })
                    break
        
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "connections": connections,
            "interfaces": interfaces
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

def get_all_system_info() -> Dict[str, Dict[str, Any]]:
    """
    Get all system information.
    
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary with all system information
    """
    return {
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),
        "network": get_network_info(),
        "uptime": get_system_uptime(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }
    }