#!/usr/bin/env python3
"""
discover.py — System Discovery Script
Collects hardware and OS information and writes SYSTEM_PROFILE.md.
Run once after major hardware/OS changes.

Usage:
    python scripts/discover.py
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
OUTPUT_FILE = PROJECT_ROOT / "SYSTEM_PROFILE.md"

OS = platform.system()  # "Linux", "Darwin", "Windows"


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(cmd, shell=False, timeout=10):
    """Run a command, return stdout. Returns '' on any failure."""
    try:
        if isinstance(cmd, str) and not shell:
            cmd = cmd.split()
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, shell=shell
        )
        return r.stdout.strip()
    except Exception:
        return ""


def ps(command, timeout=10):
    """Run a PowerShell command (Windows only)."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception:
        return ""


def read_file(path):
    """Read a file, return contents or ''."""
    try:
        return Path(path).read_text(errors="replace")
    except Exception:
        return ""


def first_match(pattern, text, default="Unknown"):
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(1).strip() if m else default


# ── Collectors ────────────────────────────────────────────────────────────────

def get_os_info():
    if OS == "Linux":
        osrel = read_file("/etc/os-release")
        name = first_match(r'^PRETTY_NAME="?([^"\n]+)"?', osrel)
        return name
    elif OS == "Darwin":
        product = run("sw_vers -productName")
        version = run("sw_vers -productVersion")
        build = run("sw_vers -buildVersion")
        return f"{product} {version} ({build})"
    elif OS == "Windows":
        out = ps("(Get-CimInstance Win32_OperatingSystem).Caption")
        return out or platform.version()
    return platform.version()


def get_kernel():
    if OS in ("Linux", "Darwin"):
        return run("uname -r")
    elif OS == "Windows":
        return platform.version()
    return "Unknown"


def get_hostname():
    return platform.node() or "Unknown"


def get_cpu():
    if OS == "Linux":
        info = read_file("/proc/cpuinfo")
        model = first_match(r"model name\s*:\s*(.+)", info)
        cores_logical = run("nproc") or "?"
        cores_physical = run("nproc --all") or "?"
        freq = first_match(r"cpu MHz\s*:\s*([\d.]+)", info)
        freq_str = f" @ {float(freq)/1000:.2f} GHz" if freq != "Unknown" else ""
        return f"{model} — {cores_physical} cores / {cores_logical} threads{freq_str}"
    elif OS == "Darwin":
        brand = run("sysctl -n machdep.cpu.brand_string")
        logical = run("sysctl -n hw.logicalcpu")
        physical = run("sysctl -n hw.physicalcpu")
        return f"{brand} — {physical} cores / {logical} threads"
    elif OS == "Windows":
        name = ps("(Get-CimInstance Win32_Processor).Name")
        cores = ps("(Get-CimInstance Win32_Processor).NumberOfCores")
        threads = ps("(Get-CimInstance Win32_Processor).NumberOfLogicalProcessors")
        return f"{name} — {cores} cores / {threads} threads"
    return "Unknown"


def get_ram():
    if OS == "Linux":
        info = read_file("/proc/meminfo")
        total = first_match(r"MemTotal:\s+(\d+)", info)
        if total != "Unknown":
            gb = int(total) / 1024 / 1024
            return f"{gb:.1f} GB"
    elif OS == "Darwin":
        mem = run("sysctl -n hw.memsize")
        if mem:
            gb = int(mem) / 1024 ** 3
            return f"{gb:.1f} GB"
    elif OS == "Windows":
        mem = ps("(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory")
        if mem:
            gb = int(mem) / 1024 ** 3
            return f"{gb:.1f} GB"
    return "Unknown"


def get_gpu():
    # Try nvidia-smi first (cross-platform)
    smi = run("nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader,nounits")
    if smi:
        lines = [f"NVIDIA {l.strip()}" for l in smi.splitlines() if l.strip()]
        return "\n| | " + "\n| | ".join(lines)

    if OS == "Linux":
        lspci = run("lspci")
        gpus = re.findall(r"(?:VGA compatible controller|3D controller|Display controller): (.+)", lspci)
        return "; ".join(gpus) if gpus else "Unknown (lspci not available)"
    elif OS == "Darwin":
        out = run("system_profiler SPDisplaysDataType")
        chipset = re.findall(r"Chipset Model:\s+(.+)", out)
        return "; ".join(chipset) if chipset else "Unknown"
    elif OS == "Windows":
        out = ps("(Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, AdapterRAM | Format-List | Out-String)")
        return out or "Unknown"
    return "Unknown"


def get_motherboard():
    if OS == "Linux":
        vendor = read_file("/sys/class/dmi/id/board_vendor").strip()
        name = read_file("/sys/class/dmi/id/board_name").strip()
        bios_ver = read_file("/sys/class/dmi/id/bios_version").strip()
        bios_date = read_file("/sys/class/dmi/id/bios_date").strip()
        board = f"{vendor} {name}".strip()
        if bios_ver:
            board += f" — BIOS {bios_ver} ({bios_date})"
        return board or "Unknown"
    elif OS == "Darwin":
        out = run("system_profiler SPHardwareDataType")
        model = first_match(r"Model (?:Name|Identifier):\s+(.+)", out)
        serial = first_match(r"Serial Number.*?:\s+(.+)", out)
        return f"{model} (Serial: {serial})"
    elif OS == "Windows":
        mfr = ps("(Get-CimInstance Win32_BaseBoard).Manufacturer")
        prod = ps("(Get-CimInstance Win32_BaseBoard).Product")
        bios = ps("(Get-CimInstance Win32_BIOS).SMBIOSBIOSVersion")
        bios_date = ps("(Get-CimInstance Win32_BIOS).ReleaseDate")
        result = f"{mfr} {prod}".strip()
        if bios:
            result += f" — BIOS {bios}"
        return result
    return "Unknown"


def get_storage():
    lines = []
    if OS == "Linux":
        lsblk = run("lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT")
        if lsblk:
            lines.append("```")
            lines.append(lsblk)
            lines.append("```")
        df = run("df -h --output=source,size,used,avail,pcent,target -x tmpfs -x devtmpfs")
        if df:
            lines.append("```")
            lines.append(df)
            lines.append("```")
    elif OS == "Darwin":
        diskutil = run("diskutil list")
        if diskutil:
            lines.append("```")
            lines.append(diskutil[:2000])  # truncate if huge
            lines.append("```")
        df = run("df -h")
        if df:
            lines.append("```")
            lines.append(df)
            lines.append("```")
    elif OS == "Windows":
        drives = ps("Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='Used(GB)';E={[math]::Round($_.Used/1GB,1)}}, @{N='Free(GB)';E={[math]::Round($_.Free/1GB,1)}} | Format-Table -AutoSize | Out-String")
        disks = ps("Get-CimInstance Win32_DiskDrive | Select-Object Model, @{N='Size(GB)';E={[math]::Round($_.Size/1GB,1)}} | Format-Table -AutoSize | Out-String")
        if drives or disks:
            lines.append("```")
            if disks:
                lines.append(disks.strip())
            if drives:
                lines.append(drives.strip())
            lines.append("```")
    return "\n".join(lines) or "Unknown"


def get_network():
    lines = []
    if OS == "Linux":
        ip = run("ip -brief address show")
        if ip:
            lines.append("```")
            lines.append(ip)
            lines.append("```")
        # Driver info
        for iface in re.findall(r"^(\S+)", ip, re.MULTILINE):
            if iface in ("lo",):
                continue
            drv = run(f"ethtool -i {iface}")
            drv_match = re.search(r"driver:\s+(.+)", drv)
            speed = run(f"ethtool {iface}")
            speed_match = re.search(r"Speed:\s+(.+)", speed)
            if drv_match:
                drv_info = drv_match.group(1).strip()
                spd_info = speed_match.group(1).strip() if speed_match else "?"
                lines.append(f"- `{iface}`: driver={drv_info}, speed={spd_info}")
    elif OS == "Darwin":
        out = run("networksetup -listallhardwareports")
        lines.append("```")
        lines.append(out[:1500])
        lines.append("```")
    elif OS == "Windows":
        out = ps("Get-NetAdapter | Select-Object Name, Status, LinkSpeed, MacAddress | Format-Table -AutoSize | Out-String")
        lines.append("```")
        lines.append(out.strip())
        lines.append("```")
    return "\n".join(lines) or "Unknown"


def get_desktop_env():
    """Best-effort desktop/display info."""
    if OS == "Linux":
        de = (os.environ.get("XDG_CURRENT_DESKTOP")
              or os.environ.get("DESKTOP_SESSION")
              or run("loginctl show-session $(loginctl | awk 'NR==2{print $1}') -p Type --value", shell=True)
              or "Unknown")
        if os.environ.get("WAYLAND_DISPLAY"):
            display = "Wayland"
        elif os.environ.get("DISPLAY"):
            display = f"X11 ({os.environ.get('DISPLAY')})"
        else:
            display = "Unknown"
        return f"{de} on {display}"
    elif OS == "Darwin":
        return "macOS Aqua"
    elif OS == "Windows":
        build = ps("(Get-CimInstance Win32_OperatingSystem).BuildNumber")
        return f"Windows Desktop (Build {build})"
    return "Unknown"


def get_uptime():
    if OS == "Linux":
        uptime_raw = read_file("/proc/uptime")
        if uptime_raw:
            secs = float(uptime_raw.split()[0])
            h, m = divmod(int(secs) // 60, 60)
            d, h = divmod(h, 24)
            return f"{d}d {h}h {m}m"
    elif OS == "Darwin":
        return run("uptime")
    elif OS == "Windows":
        out = ps("(Get-Date) - (gcim Win32_OperatingSystem).LastBootUpTime | Select-Object -ExpandProperty TotalHours")
        if out:
            try:
                h = float(out)
                d, hh = divmod(int(h), 24)
                return f"{d}d {hh}h"
            except Exception:
                pass
    return run("uptime") or "Unknown"


# ── Writer ────────────────────────────────────────────────────────────────────

def build_profile():
    print("Collecting system information...")

    sections = {}
    fields = [
        ("OS Version",      get_os_info),
        ("Kernel",          get_kernel),
        ("Hostname",        get_hostname),
        ("Motherboard",     get_motherboard),
        ("CPU",             get_cpu),
        ("RAM",             get_ram),
        ("GPU",             get_gpu),
        ("Desktop / UI",    get_desktop_env),
        ("Current Uptime",  get_uptime),
    ]

    results = {}
    for label, fn in fields:
        print(f"  {label}...", end=" ", flush=True)
        try:
            results[label] = fn()
            print("done")
        except Exception as e:
            results[label] = f"Error: {e}"
            print("error")

    print("  Storage...", end=" ", flush=True)
    storage = get_storage()
    print("done")

    print("  Network...", end=" ", flush=True)
    network = get_network()
    print("done")

    # Build markdown
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# System Profile",
        "",
        f"> Generated by `scripts/discover.py` on {now}",
        "",
        "---",
        "",
        "## Machine",
        "",
        "| Field | Value |",
        "|---|---|",
    ]

    for label, _ in fields:
        val = results.get(label, "Unknown")
        # Collapse multiline values for the table
        val_single = val.replace("\n", " ").strip()
        lines.append(f"| **{label}** | {val_single} |")

    lines += [
        "",
        "---",
        "",
        "## Storage",
        "",
        storage,
        "",
        "---",
        "",
        "## Network",
        "",
        network,
        "",
        "---",
        "",
        "## Configuration Notes",
        "",
        "> Add hardware-specific quirks, BIOS settings, driver choices, and known workarounds here.",
        "> This section is manually maintained — discover.py does not overwrite it.",
        "",
    ]

    # Preserve existing config notes if file exists
    existing = OUTPUT_FILE.read_text(errors="replace") if OUTPUT_FILE.exists() else ""
    config_match = re.search(
        r"## Configuration Notes\n(.*?)(?=\n---|\Z)", existing, re.DOTALL
    )
    if config_match:
        existing_notes = config_match.group(1).strip()
        if existing_notes and existing_notes != "> Add hardware-specific quirks...":
            lines[-2] = existing_notes

    return "\n".join(lines)


def main():
    print(f"\n{'='*50}")
    print("  System Discovery — Claude Diagnostics")
    print(f"  Platform: {OS}")
    print(f"{'='*50}\n")

    profile = build_profile()

    OUTPUT_FILE.write_text(profile, encoding="utf-8")
    print(f"\n✓ Profile written to: {OUTPUT_FILE}")
    print("  Share SYSTEM_PROFILE.md with Claude at the start of a diagnostic session.\n")


if __name__ == "__main__":
    main()
