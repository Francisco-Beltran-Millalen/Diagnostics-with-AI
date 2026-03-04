#!/usr/bin/env python3
"""
elevated.py — Privileged System Diagnostic Dump
Collects kernel logs, hardware sensors, SMART data, crash history, and MCE errors.
REQUIRES elevated privileges.

Usage:
    Linux/macOS : sudo python scripts/elevated.py
    Windows     : Run as Administrator — python scripts/elevated.py

Output: output/elevated-dump.txt
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
OUTPUT_FILE = OUTPUT_DIR / "elevated-dump.txt"
OUTPUT_DIR.mkdir(exist_ok=True)

OS = platform.system()  # "Linux", "Darwin", "Windows"


# ── Privilege check ───────────────────────────────────────────────────────────

def check_privileges():
    """Warn if not running elevated. Don't block — partial data is still useful."""
    if OS in ("Linux", "Darwin"):
        if os.geteuid() != 0:
            print("⚠  WARNING: Not running as root. Some data will be missing.")
            print("   For full output: sudo python scripts/elevated.py\n")
            return False
    elif OS == "Windows":
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("⚠  WARNING: Not running as Administrator. Some data will be missing.")
                print("   Right-click terminal → Run as Administrator\n")
                return False
        except Exception:
            pass
    return True


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(cmd, shell=False, timeout=30):
    try:
        if isinstance(cmd, str) and not shell:
            cmd = cmd.split()
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, shell=shell
        )
        return (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return "[timeout]"
    except Exception as e:
        return f"[error: {e}]"


def ps(command, timeout=30):
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception as e:
        return f"[error: {e}]"


def section(title):
    sep = "─" * 60
    return f"\n{sep}\n  {title}\n{sep}\n"


# ── Linux collectors ──────────────────────────────────────────────────────────

def linux_dmesg():
    out = [section("DMESG — KERNEL RING BUFFER (current boot)")]
    # Full dmesg
    full = run("dmesg --level=emerg,alert,crit,err,warn")
    out.append("Errors and warnings:")
    out.append(full if full else "  (none)")

    # Hardware errors specifically
    out.append("\nHardware / MCE / GPU filter:")
    hw = run(
        "dmesg | grep -iE '(machine check|mce|hardware error|nvidia|nvrm|xid|"
        "hung_task|soft.?lockup|hard.?lockup|rcu|out.of.memory|oom.kill|"
        "pcieport|aer|usb.error|ata.*error|ext4.*error)'",
        shell=True
    )
    out.append(hw if hw else "  (none)")
    return "\n".join(out)


def linux_journal_kernel():
    out = [section("JOURNAL — KERNEL LOG (current boot)")]
    out.append(run("journalctl -b 0 -k --no-pager -n 100"))
    return "\n".join(out)


def linux_journal_prev():
    out = [section("JOURNAL — PREVIOUS BOOT (kernel + errors)")]
    # Check if previous boot exists
    boots = run("journalctl --list-boots --no-pager")
    if "-1" in boots or "b 1" in boots:
        out.append("Kernel log (boot -1):")
        out.append(run("journalctl -b -1 -k --no-pager -n 80"))
        out.append("\nErrors (boot -1):")
        out.append(run("journalctl -b -1 -p 0..3 --no-pager -n 50"))
    else:
        out.append("(no previous boot in journal)")
    return "\n".join(out)


def linux_crash_history():
    out = [section("CRASH / BOOT HISTORY")]
    out.append(run("last -x | head -30"))
    return "\n".join(out)


def linux_mce():
    out = [section("MCE — MACHINE CHECK EXCEPTIONS")]
    # rasdaemon
    ras = run("ras-mc-ctl --summary")
    out.append("rasdaemon summary:")
    out.append(ras if ras and "[error" not in ras else "  [rasdaemon not available or no data]")

    # dmesg MCE
    mce_dmesg = run("dmesg | grep -iE '(machine check|hardware error|mce)'", shell=True)
    out.append("\ndmesg MCE entries:")
    out.append(mce_dmesg if mce_dmesg else "  (none)")
    return "\n".join(out)


def linux_sensors():
    out = [section("HARDWARE SENSORS / TEMPERATURES")]
    temps = run("sensors")
    out.append(temps if temps and "[error" not in temps else "  [sensors not available — install lm-sensors]")

    # GPU temperature via nvidia-smi
    gpu_temp = run(
        "nvidia-smi --query-gpu=temperature.gpu,fan.speed,power.draw,clocks.current.graphics "
        "--format=csv,noheader"
    )
    if gpu_temp and "[error" not in gpu_temp:
        out.append(f"\nNVIDIA GPU: temp={gpu_temp}")
    return "\n".join(out)


def linux_smart():
    out = [section("DISK SMART HEALTH")]
    # Find block devices
    lsblk = run("lsblk -dn -o NAME,TYPE")
    disks = re.findall(r"(sd[a-z]|nvme\d+n\d+|hd[a-z])\s+disk", lsblk)
    if not disks:
        out.append("[no disks found via lsblk, trying common names]")
        disks = ["sda", "sdb", "nvme0n1"]

    for disk in disks:
        out.append(f"\n/dev/{disk}:")
        smart = run(f"smartctl -H -A /dev/{disk}")
        if "[error" in smart or "Permission denied" in smart:
            out.append(f"  [smartctl not available — install smartmontools]")
        else:
            # Show only health + key attributes
            lines = smart.splitlines()
            for line in lines:
                if any(k in line for k in (
                    "SMART overall", "Reallocated", "Pending", "Uncorrectable",
                    "Temperature", "Power_On_Hours", "Start_Stop", "Raw_Read_Error",
                    "PASSED", "FAILED"
                )):
                    out.append(f"  {line}")
    return "\n".join(out)


def linux_pcie():
    out = [section("PCIe LINK STATUS")]
    lspci = run("lspci | grep -iE 'VGA|3D|Display'", shell=True)
    gpus = re.findall(r"^([0-9a-f:.]+)\s+", lspci, re.M)
    for addr in gpus:
        out.append(f"\nGPU @ {addr}:")
        detail = run(f"lspci -vv -s {addr}")
        for line in detail.splitlines():
            if re.search(r"LnkSta|LnkCap|LnkCtl|Speed|ASPM", line):
                out.append(f"  {line.strip()}")
    return "\n".join(out)


def linux_pstore():
    out = [section("PSTORE — KERNEL CRASH DUMPS")]
    pstore = Path("/sys/fs/pstore")
    if pstore.exists():
        files = list(pstore.iterdir())
        if files:
            for f in files:
                out.append(f"Found: {f}")
                try:
                    out.append(f.read_text(errors="replace")[:500])
                except Exception:
                    out.append("[unreadable]")
        else:
            out.append("pstore directory is empty (no crash dumps saved)")
    else:
        out.append("[pstore not mounted]")
    return "\n".join(out)


# ── macOS collectors ──────────────────────────────────────────────────────────

def macos_kernel_log():
    out = [section("KERNEL / SYSTEM LOG (last 2h)")]
    out.append(run(
        "log show --last 2h --predicate "
        "'messageType == 16 OR messageType == 17 OR subsystem == \"com.apple.kernel\"' "
        "--info 2>/dev/null | tail -100",
        shell=True, timeout=60
    ))
    return "\n".join(out)


def macos_crash_history():
    out = [section("CRASH HISTORY")]
    out.append(run("last -20"))
    crash_dir = Path(os.path.expanduser("~/Library/Logs/DiagnosticReports"))
    if crash_dir.exists():
        crashes = sorted(crash_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        for c in crashes:
            out.append(f"\nCrash report: {c.name}")
    return "\n".join(out)


def macos_sensors():
    out = [section("HARDWARE SENSORS")]
    out.append("(powermetrics requires root — running 1 sample)")
    out.append(run(
        "powermetrics -n 1 --samplers smc 2>/dev/null | grep -iE 'temp|fan|power'",
        shell=True, timeout=30
    ))
    return "\n".join(out)


def macos_smart():
    out = [section("DISK SMART HEALTH")]
    disks = re.findall(r"(/dev/disk\d+)\b", run("diskutil list"))
    seen = set()
    for disk in disks:
        if disk in seen:
            continue
        seen.add(disk)
        smart = run(f"smartctl -H {disk}")
        if "PASSED" in smart or "FAILED" in smart:
            out.append(f"{disk}: {re.search(r'SMART overall.*', smart).group(0) if re.search(r'SMART overall.*', smart) else smart[:100]}")
    return "\n".join(out)


# ── Windows collectors ────────────────────────────────────────────────────────

def windows_event_log():
    out = [section("WINDOWS EVENT LOG — SYSTEM (errors/warnings)")]
    out.append(ps(
        "Get-EventLog -LogName System -Newest 50 -EntryType Error,Warning "
        "| Select-Object TimeGenerated, EventID, EntryType, Source, "
        "@{N='Message';E={$_.Message.Substring(0, [Math]::Min(200,$_.Message.Length))}} "
        "| Format-List | Out-String",
        timeout=30
    ))
    return "\n".join(out)


def windows_app_event_log():
    out = [section("WINDOWS EVENT LOG — APPLICATION (errors)")]
    out.append(ps(
        "Get-EventLog -LogName Application -Newest 30 -EntryType Error "
        "| Select-Object TimeGenerated, EventID, Source, "
        "@{N='Message';E={$_.Message.Substring(0, [Math]::Min(200,$_.Message.Length))}} "
        "| Format-List | Out-String",
        timeout=30
    ))
    return "\n".join(out)


def windows_crash_history():
    out = [section("CRASH / SHUTDOWN HISTORY")]
    # EventID 6005=start, 6006=stop, 6008=unexpected shutdown, 41=kernel power (crash)
    out.append(ps(
        "Get-WinEvent -LogName System -MaxEvents 30 "
        "| Where-Object {$_.Id -in @(41, 1074, 6005, 6006, 6008)} "
        "| Select-Object TimeCreated, Id, "
        "@{N='Type';E={switch($_.Id){41{'CRASH/REBOOT'} 1074{'SHUTDOWN'} 6005{'STARTUP'} 6006{'SHUTDOWN'} 6008{'UNEXPECTED SHUTDOWN'}}}} "
        ", Message "
        "| Format-List | Out-String",
        timeout=30
    ))
    return "\n".join(out)


def windows_sensors():
    out = [section("HARDWARE SENSORS (WMI — limited)")]
    out.append("Note: For detailed temps/fan speeds, use HWiNFO64.")
    out.append(ps(
        "Get-CimInstance -Namespace root/WMI -ClassName MSAcpi_ThermalZoneTemperature "
        "| Select-Object InstanceName, "
        "@{N='Temp(C)';E={[math]::Round($_.CurrentTemperature/10 - 273.15, 1)}} "
        "| Format-Table | Out-String"
    ))
    return "\n".join(out)


def windows_smart():
    out = [section("DISK SMART HEALTH")]
    out.append(ps(
        "Get-CimInstance -Namespace root/WMI -ClassName MSStorageDriver_FailurePredictStatus "
        "| Select-Object InstanceName, PredictFailure, Reason "
        "| Format-Table | Out-String"
    ))
    # Also try smartctl if available
    smartctl = run("smartctl --scan", shell=True)
    if smartctl and "[error" not in smartctl:
        out.append("\nsmartctl scan:")
        out.append(smartctl)
        for line in smartctl.splitlines():
            dev = re.match(r"(/dev/\S+)", line)
            if dev:
                out.append(f"\n{dev.group(1)} health:")
                out.append(run(f"smartctl -H {dev.group(1)}"))
    return "\n".join(out)


def windows_drivers():
    out = [section("DRIVER STATUS")]
    out.append(ps(
        "Get-WmiObject Win32_PnPSignedDriver "
        "| Where-Object {$_.DeviceClass -in @('DISPLAY','NET','SYSTEM')} "
        "| Select-Object DeviceClass, DeviceName, DriverVersion, DriverDate "
        "| Format-Table -AutoSize | Out-String"
    ))
    return "\n".join(out)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*50}")
    print("  Elevated Diagnostics — Claude Diagnostics")
    print(f"  Platform: {OS}")
    print(f"{'='*50}\n")

    is_elevated = check_privileges()

    if OS == "Linux":
        collectors = [
            ("dmesg",           linux_dmesg),
            ("Journal (kernel)",linux_journal_kernel),
            ("Journal (prev)",  linux_journal_prev),
            ("Crash history",   linux_crash_history),
            ("MCE",             linux_mce),
            ("Sensors",         linux_sensors),
            ("SMART",           linux_smart),
            ("PCIe",            linux_pcie),
            ("pstore",          linux_pstore),
        ]
    elif OS == "Darwin":
        collectors = [
            ("Kernel log",      macos_kernel_log),
            ("Crash history",   macos_crash_history),
            ("Sensors",         macos_sensors),
            ("SMART",           macos_smart),
        ]
    elif OS == "Windows":
        collectors = [
            ("System events",   windows_event_log),
            ("App events",      windows_app_event_log),
            ("Crash history",   windows_crash_history),
            ("Sensors",         windows_sensors),
            ("SMART",           windows_smart),
            ("Drivers",         windows_drivers),
        ]
    else:
        print(f"Unsupported platform: {OS}")
        sys.exit(1)

    chunks = [
        f"Elevated Diagnostic Dump\nGenerated: {datetime.now()}\nOS: {OS}\nElevated: {is_elevated}\n"
    ]

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

    print(f"\n✓ Elevated dump written to: {OUTPUT_FILE}")
    print("  Share output/elevated-dump.txt with Claude.\n")


if __name__ == "__main__":
    main()
