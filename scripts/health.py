#!/usr/bin/env python3
"""
health.py — System Health Check (non-privileged)
Collects system state, service status, resource usage, and recent errors.
Does NOT require sudo/admin.

Usage:
    python scripts/health.py

Output: output/health-dump.txt
"""

import platform
import subprocess
import os
import re
import sys
from pathlib import Path
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_FILE = OUTPUT_DIR / "health-dump.txt"
OUTPUT_DIR.mkdir(exist_ok=True)

OS = platform.system()  # "Linux", "Darwin", "Windows"

# ── Helpers ───────────────────────────────────────────────────────────────────

def run(cmd, shell=False, timeout=15):
    try:
        if isinstance(cmd, str) and not shell:
            cmd = cmd.split()
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, shell=shell
        )
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return f"[error: {e}]"


def ps(command, timeout=15):
    """Run a PowerShell command."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception as e:
        return f"[error: {e}]"


def read_file(path):
    try:
        return Path(path).read_text(errors="replace").strip()
    except Exception:
        return ""


def section(title):
    sep = "─" * 60
    return f"\n{sep}\n  {title}\n{sep}\n"


# ── Collectors ────────────────────────────────────────────────────────────────

def collect_overview():
    out = [section("SYSTEM OVERVIEW")]

    out.append(f"Platform : {OS}")
    out.append(f"Hostname : {platform.node()}")
    out.append(f"Time     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if OS == "Linux":
        osrel = read_file("/etc/os-release")
        name = re.search(r'^PRETTY_NAME="?([^"\n]+)"?', osrel, re.M)
        out.append(f"OS       : {name.group(1) if name else platform.version()}")
        out.append(f"Kernel   : {run('uname -r')}")
        out.append(f"Uptime   : {run('uptime -p')}")
    elif OS == "Darwin":
        out.append(f"OS       : macOS {run('sw_vers -productVersion')}")
        out.append(f"Kernel   : {run('uname -r')}")
        out.append(f"Uptime   : {run('uptime')}")
    elif OS == "Windows":
        out.append(f"OS       : {ps('(Get-CimInstance Win32_OperatingSystem).Caption')}")
        out.append(f"Version  : {platform.version()}")
        boot = ps("(Get-CimInstance Win32_OperatingSystem).LastBootUpTime")
        out.append(f"Last Boot: {boot}")

    return "\n".join(out)


def collect_cpu_load():
    out = [section("CPU / LOAD")]

    if OS == "Linux":
        loadavg = read_file("/proc/loadavg")
        out.append(f"Load average: {loadavg}")
        out.append(run("top -bn1 | head -5"))
    elif OS == "Darwin":
        out.append(run("top -l 1 -n 0 | head -10"))
    elif OS == "Windows":
        load = ps("(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average")
        out.append(f"CPU Load: {load}%")
        out.append(ps("Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 Name,CPU,WorkingSet | Format-Table -AutoSize | Out-String"))

    return "\n".join(out)


def collect_memory():
    out = [section("MEMORY")]

    if OS == "Linux":
        out.append(run("free -h"))
        meminfo = read_file("/proc/meminfo")
        for key in ("SwapTotal", "SwapFree", "Dirty", "Writeback", "AnonHugePages"):
            m = re.search(rf"^{key}:\s+(.+)", meminfo, re.M)
            if m:
                out.append(f"{key}: {m.group(1).strip()}")
    elif OS == "Darwin":
        out.append(run("vm_stat"))
        out.append(run("sysctl -n hw.memsize"))
    elif OS == "Windows":
        out.append(ps(
            "Get-CimInstance Win32_OperatingSystem | "
            "Select-Object @{N='Total(GB)';E={[math]::Round($_.TotalVisibleMemorySize/1MB,1)}}, "
            "@{N='Free(GB)';E={[math]::Round($_.FreePhysicalMemory/1MB,1)}} | "
            "Format-List | Out-String"
        ))
        out.append(ps(
            "Get-CimInstance Win32_PageFileUsage | "
            "Select-Object Name, CurrentUsage, AllocatedBaseSize | "
            "Format-List | Out-String"
        ))

    return "\n".join(out)


def collect_disk():
    out = [section("DISK USAGE")]

    if OS == "Linux":
        out.append(run("df -h -x tmpfs -x devtmpfs"))
    elif OS == "Darwin":
        out.append(run("df -h"))
    elif OS == "Windows":
        out.append(ps(
            "Get-PSDrive -PSProvider FileSystem | "
            "Select-Object Name, @{N='Used(GB)';E={[math]::Round($_.Used/1GB,1)}}, "
            "@{N='Free(GB)';E={[math]::Round($_.Free/1GB,1)}}, "
            "@{N='Total(GB)';E={[math]::Round(($_.Used+$_.Free)/1GB,1)}} | "
            "Format-Table -AutoSize | Out-String"
        ))

    return "\n".join(out)


def collect_gpu():
    out = [section("GPU STATUS")]

    smi = run("nvidia-smi")
    if "[error" not in smi and smi:
        out.append(smi)
    else:
        out.append("[nvidia-smi not available]")

    if OS == "Linux":
        lspci_gpu = run("lspci | grep -iE 'VGA|3D|Display'", shell=True)
        if lspci_gpu:
            out.append(f"\nlspci GPU:\n{lspci_gpu}")
        # PCIe link speed (non-privileged)
        try:
            gpu_addr = re.search(r"^([0-9a-f:.]+)\s+(?:VGA|3D|Display)", lspci_gpu, re.M)
            if gpu_addr:
                addr = gpu_addr.group(1).replace(":", "/")
                speed_path = Path(f"/sys/bus/pci/devices/0000:{gpu_addr.group(1)}/current_link_speed")
                if not speed_path.exists():
                    # Try finding GPU PCI device path
                    for p in Path("/sys/bus/pci/devices").iterdir():
                        class_file = p / "class"
                        if class_file.exists() and class_file.read_text().strip() in ("0x030000", "0x030200"):
                            speed_file = p / "current_link_speed"
                            if speed_file.exists():
                                out.append(f"PCIe link speed: {speed_file.read_text().strip()}")
                                break
        except Exception:
            pass
    elif OS == "Darwin":
        out.append(run("system_profiler SPDisplaysDataType"))
    elif OS == "Windows":
        out.append(ps(
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name, DriverVersion, VideoModeDescription, AdapterRAM | "
            "Format-List | Out-String"
        ))

    return "\n".join(out)


def collect_services():
    out = [section("SERVICES — FAILED / STOPPED")]

    if OS == "Linux":
        failed = run("systemctl list-units --state=failed --no-legend --no-pager")
        out.append("Failed systemd units:")
        out.append(failed if failed and "[error" not in failed else "  (none)")

        # User services
        failed_user = run("systemctl --user list-units --state=failed --no-legend --no-pager")
        out.append("\nFailed user units:")
        out.append(failed_user if failed_user and "[error" not in failed_user else "  (none)")
    elif OS == "Darwin":
        out.append(run("launchctl list | grep -v '^-' | head -30", shell=True))
    elif OS == "Windows":
        out.append(ps(
            "Get-Service | Where-Object {$_.Status -eq 'Stopped' -and $_.StartType -eq 'Automatic'} | "
            "Select-Object DisplayName, Status, StartType | "
            "Format-Table -AutoSize | Out-String"
        ))

    return "\n".join(out)


def collect_recent_errors():
    out = [section("RECENT ERRORS (USER-SPACE / APPLICATION)")]

    if OS == "Linux":
        # User journal errors (no sudo needed)
        errors = run(
            "journalctl --no-pager -p 0..3 -n 50 --since '24 hours ago'",
            timeout=20
        )
        out.append("journalctl -p err..emerg (last 24h, user-accessible):")
        out.append(errors if errors and "[error" not in errors else "  (none)")

        out.append("\nRecent journal (last 30 lines, current boot):")
        out.append(run("journalctl -n 30 --no-pager", timeout=15))
    elif OS == "Darwin":
        out.append(run(
            "log show --last 1h --predicate 'messageType == 16 OR messageType == 17' --info 2>/dev/null | tail -50",
            shell=True, timeout=30
        ))
    elif OS == "Windows":
        out.append(ps(
            "Get-EventLog -LogName Application -Newest 30 -EntryType Error,Warning "
            "| Select-Object TimeGenerated, EntryType, Source, Message "
            "| Format-List | Out-String",
            timeout=30
        ))

    return "\n".join(out)


def collect_boot_history():
    out = [section("BOOT HISTORY")]

    if OS == "Linux":
        boots = run("journalctl --list-boots --no-pager")
        out.append(boots if boots else "[journalctl not available]")
    elif OS == "Darwin":
        out.append(run("last -5"))
    elif OS == "Windows":
        out.append(ps(
            "Get-EventLog -LogName System -Newest 20 "
            "-InstanceId 6005,6006,6008,1074 "
            "| Select-Object TimeGenerated, EventID, Message "
            "| Format-List | Out-String",
            timeout=20
        ))

    return "\n".join(out)


def collect_network():
    out = [section("NETWORK STATUS")]

    if OS == "Linux":
        out.append(run("ip -brief address show"))
        out.append("")
        out.append(run("ip route"))
    elif OS == "Darwin":
        out.append(run("ifconfig -a | grep -E 'inet |flags|ether'", shell=True))
    elif OS == "Windows":
        out.append(ps(
            "Get-NetAdapter | Select-Object Name, Status, LinkSpeed | Format-Table | Out-String"
        ))
        out.append(ps("Test-NetConnection -ComputerName 8.8.8.8 -InformationLevel Quiet"))

    return "\n".join(out)


def collect_top_processes():
    out = [section("TOP PROCESSES (by memory)")]

    if OS == "Linux":
        out.append(run(
            "ps aux --sort=-%mem | head -15",
            shell=True
        ))
    elif OS == "Darwin":
        out.append(run("ps aux -m | head -15"))
    elif OS == "Windows":
        out.append(ps(
            "Get-Process | Sort-Object WorkingSet -Descending | "
            "Select-Object -First 15 Name, Id, "
            "@{N='Mem(MB)';E={[math]::Round($_.WorkingSet/1MB,1)}}, CPU | "
            "Format-Table -AutoSize | Out-String"
        ))

    return "\n".join(out)


def collect_note():
    """Remind user that privileged data needs elevated.py."""
    lines = [
        section("NEXT STEPS"),
        "This dump contains non-privileged data only.",
        "",
        "For kernel logs, hardware sensors, SMART health, MCE errors, and crash history,",
        "run the elevated script:",
        "",
    ]
    if OS == "Windows":
        lines.append("  (Run as Administrator)  python scripts/elevated.py")
    else:
        lines.append("  sudo python scripts/elevated.py")
    lines.append("")
    lines.append("Share output/elevated-dump.txt with Claude alongside this file.")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*50}")
    print("  Health Check — Claude Diagnostics")
    print(f"  Platform: {OS}")
    print(f"{'='*50}\n")

    collectors = [
        ("Overview",        collect_overview),
        ("CPU / Load",      collect_cpu_load),
        ("Memory",          collect_memory),
        ("Disk",            collect_disk),
        ("GPU",             collect_gpu),
        ("Services",        collect_services),
        ("Recent Errors",   collect_recent_errors),
        ("Boot History",    collect_boot_history),
        ("Network",         collect_network),
        ("Top Processes",   collect_top_processes),
        ("Next Steps",      collect_note),
    ]

    chunks = []
    for name, fn in collectors:
        print(f"  Collecting {name}...", end=" ", flush=True)
        try:
            chunks.append(fn())
            print("done")
        except Exception as e:
            chunks.append(section(name.upper()) + f"[collection error: {e}]")
            print(f"error: {e}")

    output = "\n".join(chunks)
    OUTPUT_FILE.write_text(output, encoding="utf-8")

    print(f"\n✓ Health dump written to: {OUTPUT_FILE}")
    print("  Share output/health-dump.txt with Claude.\n")


if __name__ == "__main__":
    main()
