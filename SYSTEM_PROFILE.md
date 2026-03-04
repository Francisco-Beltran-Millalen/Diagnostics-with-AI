# System Profile

> **Note:** This file is generated and updated by `python scripts/discover.py`.
> The profile below is the last known state of this machine.
> Run `discover.py` on a new machine to overwrite with current hardware.

Last updated: 2026-03-04 (manually — pre-Windows migration)

---

## Machine

| Field | Value |
|---|---|
| **Model** | ASRock B450M/ac R2.0 (Desktop) |
| **Motherboard** | ASRock B450M/ac R2.0 — BIOS P10.43 (2025-06-25) |
| **CPU** | AMD Ryzen 7 1700 — 8 cores / 16 threads — 3.0 GHz base |
| **RAM** | 16 GB DDR4 2133 MHz |
| **GPU** | NVIDIA GeForce GTX 1060 3GB (Pascal / GP106-A) |
| **Storage (primary)** | 250 GB Crucial MX500 SSD — ext4 — `/` |
| **Storage (secondary)** | ~500 GB HDD — ext4 — `/media/main` |
| **Network** | Realtek RTL8168 (r8169 driver) — Gigabit Ethernet |
| **Display** | Samsung S22B300 — 1920×1080 — HDMI |

---

## Software (Last Known — Linux)

| Field | Value |
|---|---|
| **OS** | Debian 13 Trixie |
| **Kernel** | 6.12.73+deb13-amd64 |
| **Desktop** | XFCE 4.x on X11 |
| **Display Manager** | LightDM |
| **GPU Driver** | NVIDIA 550.163.01 (proprietary) |
| **PCIe Link** | Capped at Gen2 (5 GT/s) via BIOS — ASPM disabled |

---

## Key Configuration Notes

- BIOS PCIe x16 link speed forced to **Gen2** — prevents AMD B450 data fabric MCE on Gen3→Gen1 transitions
- DPMS disabled system-wide (`xset s off` autostart + xfconf)
- Suspend (S3) avoided — NVIDIA 550 + Pascal + X11 has unfixed suspend/resume freeze bug
- `linux-headers-$(uname -r)` must be installed before any kernel upgrade for DKMS/NVIDIA to rebuild

---

*Run `python scripts/discover.py` to regenerate this file with live data.*
