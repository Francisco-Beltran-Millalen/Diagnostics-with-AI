# Issue Tracker

This file tracks all known system issues. Updated at the end of every diagnostic session.
Do not delete entries — move them between sections as status changes.

---

## Active / TODO

*(none)*

---

## Known (Recurring / Accepted — No Action Planned)

- **AppArmor audit log spam (Xorg/NVIDIA)** — Xorg repeatedly logs allowed access to `/proc/driver/nvidia/params`, `/dev/nvidiactl`, `/dev/nvidia-modeset`. Cosmetic, no impact.
- **wireplumber: BlueZ/UPower warnings on desktop** — "BlueZ not available / Failed to get percentage from UPower" on every boot. Expected on a desktop PC with no Bluetooth daemon and no battery. No action needed.
- **xhci USBSTS 0x401 Reinit on resume** — USB controller halts on S3 resume, kernel performs full reinit. Known AMD/Ryzen quirk. Harmless — scope limited to USB devices, does not cause display freezes.
- **cupsd AppArmor DENIED (net_admin + /etc/paperspecs)** — CUPS printer daemon denied two capabilities it doesn't need. Cosmetic, printing unaffected.

---

## Resolved

| Issue | Fix | Session |
|---|---|---|
| NVIDIA 580.x driver on Fedora crashing every 1–3h (Wayland) | Migrated to Debian 13 + NVIDIA 550.163.01 + XFCE/X11 | #1–#9 |
| Desktop not loading after kernel upgrade (DKMS module missing) | `apt install linux-headers-$(uname -r) && dkms autoinstall` | #17 |
| PCIe Gen3→Gen1 MCE crash (Bank 5, SYND 4d000000) | BIOS: Advanced → AMD PBS → PCIe x16 Link Speed → Gen2 | #18 |
| DPMS idle freeze (NVIDIA driver hang on display power transition) | `xset dpms 0 0 0 && xset s off` + xfconf dpms-enabled=false + autostart entry | #16 |
| Suspend/resume freeze (NVIDIA 550 + Pascal + X11 + S3) | Avoid suspend — use shutdown instead | #20 |
| Volume keys not working (pactl missing) | `apt install pulseaudio-utils` | #12 |
| Black-on-black error dialogs (Rose Pine theme dark→light port) | Fixed `messagedialog.background` colors in GTK CSS | #12 |
| Thunar sidebar white-on-black (wrong treeview CSS) | Fixed `treeview.view:selected background-color` | #13 |
| Network stuck at 100 Mbps | Replaced damaged Cat5e cable | #16 |
| WoW 3.3.5a (Flatpak Steam) not loading game files | `flatpak override --user --filesystem=/media/main com.valvesoftware.Steam` | #15 |
| Second SSD not auto-mounting | Added UUID entry to `/etc/fstab` with `nofail` | #12 |
| Autologin not working (LightDM) | Added user to `autologin` group + config entry | #11 |

---

## No Solution Found

| Issue | Investigation Summary | Session |
|---|---|---|
| **NVIDIA 550.x + Pascal (GTX 1060) + X11 silent deadlock** | Display freezes silently after multi-client GPU use (Firefox + Alacritty + compositor). Kernel logs RCU stall warning (rcu_watching_snap_recheck, Tainted: POE) ~53 min after display freeze. No MCE. No confirmed fix exists: 550.107.02 fix is notebook-only; nvidia-open-dkms requires Turing+; Pascal is EOL on Linux. **User migrated to Windows.** | #19, #21 |
