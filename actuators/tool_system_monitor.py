import psutil
import platform
import time
import json

def system_monitor(interval: float = 1.0, iterations: int = 1) -> str:
    """
    Monitor system resources over time.
    
    Args:
        interval: Seconds between measurements
        iterations: Number of measurements to take
    
    Returns:
        Formatted report of system resource usage
    """
    result = "=== SYSTEM MONITOR REPORT ===\n"
    result += f"Host: {platform.node()}\n"
    result += f"OS: {platform.system()} {platform.release()}\n"
    result += f"Python: {platform.python_version()}\n"
    result += f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    samples = []
    for i in range(iterations):
        cpu = psutil.cpu_percent(interval=interval)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        
        sample = {
            'cpu_percent': cpu,
            'memory_percent': mem.percent,
            'memory_used_gb': mem.used / (1024**3),
            'memory_total_gb': mem.total / (1024**3),
            'disk_percent': disk.percent,
            'disk_used_gb': disk.used / (1024**3),
            'disk_total_gb': disk.total / (1024**3),
            'net_sent_mb': net.bytes_sent / (1024**2),
            'net_recv_mb': net.bytes_recv / (1024**2)
        }
        samples.append(sample)
    
    # Average if multiple iterations
    if iterations > 1:
        avg_cpu = sum(s['cpu_percent'] for s in samples) / len(samples)
        avg_mem = sum(s['memory_percent'] for s in samples) / len(samples)
        avg_disk = sum(s['disk_percent'] for s in samples) / len(samples)
        result += f"Average CPU:    {avg_cpu:.1f}%\n"
        result += f"Average Memory: {avg_mem:.1f}% ({samples[0]['memory_used_gb']:.2f}/{samples[0]['memory_total_gb']:.2f} GB)\n"
        result += f"Average Disk:   {avg_disk:.1f}% ({samples[0]['disk_used_gb']:.1f}/{samples[0]['disk_total_gb']:.1f} GB)\n"
    else:
        s = samples[0]
        result += f"CPU:    {s['cpu_percent']}%\n"
        result += f"Memory: {s['memory_percent']}% ({s['memory_used_gb']:.2f}/{s['memory_total_gb']:.2f} GB)\n"
        result += f"Disk:   {s['disk_percent']}% ({s['disk_used_gb']:.1f}/{s['disk_total_gb']:.1f} GB)\n"
        result += f"Network Sent: {s['net_sent_mb']:.2f} MB | Recv: {s['net_recv_mb']:.2f} MB\n"
    
    # Process info
    result += f"\n--- Top Processes by CPU ---\n"
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            processes.append(proc.info)
        except:
            pass
    processes.sort(key=lambda p: p.get('cpu_percent', 0), reverse=True)
    for proc in processes[:5]:
        if proc['cpu_percent'] > 0:
            result += f"  PID {proc['pid']:6d} {proc['name'][:20]:20s} CPU {proc['cpu_percent']:5.1f}% MEM {proc['memory_percent']:5.1f}%\n"
    
    return result