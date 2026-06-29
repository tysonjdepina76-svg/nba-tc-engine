"""
System health checks — disk, memory, dashboard.
"""

import shutil
import requests
from typing import Dict


def check_disk_space() -> Dict:
    try:
        usage = shutil.disk_usage("/")
        pct = (usage.used / usage.total) * 100
        pct_s = "%.1f%%" % pct
        if pct > 90:
            return {"status": "critical", "percent": pct_s, "message": "%s full" % pct_s}
        if pct > 75:
            return {"status": "warning", "percent": pct_s, "message": "%s full" % pct_s}
        return {"status": "healthy", "percent": pct_s}
    except Exception as e:
        return {"status": "warning", "message": "Cannot check disk: %s" % e}


def check_memory() -> Dict:
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        mem = {}
        for line in lines:
            if ":" in line:
                k, v = line.split(":", 1)
                mem[k.strip()] = v.strip()
        total = int(mem["MemTotal"].split()[0]) / 1024 / 1024
        avail = int(mem["MemAvailable"].split()[0]) / 1024 / 1024
        pct = ((total - avail) / total) * 100
        pct_s = "%.1f%%" % pct
        if pct > 90:
            return {"status": "critical", "percent": pct_s, "total_gb": round(total, 1)}
        if pct > 75:
            return {"status": "warning", "percent": pct_s, "total_gb": round(total, 1)}
        return {"status": "healthy", "percent": pct_s, "total_gb": round(total, 1)}
    except Exception as e:
        return {"status": "warning", "message": "Cannot check memory: %s" % e}


def check_dashboard() -> Dict:
    try:
        r = requests.get("http://localhost:8510", timeout=3)
        if r.status_code == 200:
            return {"status": "healthy", "code": 200}
        return {"status": "warning", "code": r.status_code}
    except Exception as e:
        return {"status": "critical", "message": "Dashboard not responding: %s" % e}
