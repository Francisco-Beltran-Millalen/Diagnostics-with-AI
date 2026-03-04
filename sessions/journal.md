# Diagnostic Session Journal

This file logs all diagnostic sessions: what was investigated, what was found, what actions were taken, and what decisions were made. It serves as persistent memory across sessions.

---

## [ARCHIVED] Sessions #1–#9 — February 10–17, 2026 — Fedora Era (Superseded)

> Full session logs collapsed for context efficiency. System has been migrated to Debian 13. This summary is the only relevant context from the Fedora period.

### System Profile (Fedora — no longer in use)
- **Machine**: ASRock B450M/ac R2.0 (Desktop)
- **CPU**: AMD Ryzen 7 1700 (8 cores / 16 threads) — same hardware, still in use
- **RAM**: 16GB
- **GPU**: NVIDIA GeForce GTX 1060 3GB — Driver 580.119.02 (Fedora)
- **OS**: Fedora 43 KDE Plasma — started on Wayland, migrated to X11 partway through
- **Kernel**: 6.18.8 → 6.18.10 (the 6.18.10 update triggered the final crash)
- **Storage**: 250GB Crucial MX500 SSD (btrfs) + 8GB zram swap

### What Happened — Short Version
Nine sessions were spent chasing **NVIDIA 580.x driver instability on Wayland**. The driver caused silent GPU hangs (no Xid logged, no kernel panic — PCIe bus locked up completely), crashing the system every 1–3 hours during normal browser/YouTube use.

**Fixes applied during Fedora era (most now irrelevant):**
- Created `/etc/modprobe.d/nvidia-power.conf` (modeset, fbdev, PreserveVideoMemoryAllocations)
- Set `QT_WAYLAND_DISABLE_WINDOWDECORATION=1` to fix lock screen EGL errors (Xid 13)
- Installed `xorg-x11-drv-nvidia-cuda` (nvidia-smi)
- Fixed bluetooth udev rule log spam (bad rule + initramfs rebuild)
- Disabled `nvidia-powerd` (not applicable to GTX 1060)
- Switched from Wayland to X11 (Sessions #6–#7) — reduced crashes but didn't eliminate them

**Root cause identified (Session #6):** NVIDIA 580.x introduced a documented Wayland regression affecting GPUs from GTX 1060 to RTX 5070 Ti across all distros. Confirmed by community reports on Fedora, Arch, Ubuntu, Debian, openSUSE.

**Final crash (Session #9, Feb 17):** Kernel update to 6.18.10 triggered a **MCE data fabric sync flood** (AMD hardware kill switch for uncorrectable PCIe errors) within 19 minutes on first boot. Reset reason: `0x08000800`. This was the breaking point.

### Decision: Migrate to Debian 13 + XFCE + X11
- **Why Debian**: Ships NVIDIA 550.163.01 (stable branch, pre-580.x regression). Conservative kernel policy — no surprise breaking updates.
- **Why XFCE**: X11-native, GPU-light, minimal surface area for driver bugs.
- **Community evidence**: Fedora 43 + 580.119.02 user confirmed freezes eliminated by switching to Debian + 550.x.
- **Plan B** (driver+kernel downgrade on Fedora): abandoned — NVIDIA 550 won't compile against kernel 6.18.

### Key Lessons from Fedora Era
- When the NVIDIA driver hangs, it can lock the PCIe bus so completely the kernel cannot log anything. No Xid, no panic = the silence IS the error.
- `BP_SYS_RST_L was tripped` (reset reason `0x00010800`) = hard reset. `0x08000800` = AMD MCE sync flood (hardware-level uncorrectable error, more severe).
- Kernel updates can change how GPU errors are *handled* without changing the underlying GPU bug. 6.18.8: silent hang. 6.18.10: full MCE. Same broken driver, different kernel tolerance.
- Fedora's rolling update model is a poor fit for systems with known driver instability — every update is a gamble.
- Cross-boot statistical analysis is powerful for ruling out red herrings (USB resets, framebuffer errors were not the cause of crashes).

---

## Session #11 — February 17, 2026 — Ricing, Panel, Keybindings, Applications

### Purpose
Continue Debian 13 setup. Complete desktop ricing (tasks 7–13), configure XFCE panel, add keybindings, set up Flatpak.

### Ricing Completed (Tasks 7–12, user-executed)
- **JetBrains Mono Nerd Font** — installed to `~/.local/share/fonts/`, fc-cache updated
- **Rose Pine GTK theme (Dawn)** — installed to `~/.themes/`
- **Icon theme** — installed to `~/.icons/`
- **XFCE theme applied** — GTK theme, icons, WM theme, fonts via XFCE Appearance
- **Alacritty** — configured with Rose Pine Dawn theme + JetBrains Mono, font size 13
- **Starship** — installed and configured, added to `~/.bashrc`

### Panel Configuration (Task 13)

#### Final Panel Layout
```
[App Menu][Docklike Taskbar][···spacer···][Systray][Volume][Clock][Session]
```
- **Position**: Bottom, full width (`p=10;x=0;y=0`)
- **Height**: 40px, icon size 24px
- **Background**: Rose Pine Dawn surface (#faf4ed, 95% opacity) — `background-style=1`
- **Tasklist**: Replaced with `xfce4-docklike-plugin` (icon-only taskbar)
- **Pager removed** (workspace switcher)
- **Dark mode disabled** — was forcing white text on light background
- **Clock format**: `%a %d  %H:%M` (e.g. "Tue 17  21:30"), font: JetBrains Mono Bold 14
- **Volume**: `xfce4-pulseaudio-plugin` added (was already installed)

#### Replication Commands
```bash
# Panel geometry
xfconf-query -c xfce4-panel -p /panels/panel-1/size -t uint -s 40
xfconf-query -c xfce4-panel -p /panels/panel-1/icon-size -t uint -s 24
xfconf-query -c xfce4-panel -p /panels/panel-1/length -t uint -s 100
xfconf-query -c xfce4-panel -p /panels/panel-1/position -t string -s "p=10;x=0;y=0"
xfconf-query -c xfce4-panel -p /panels/panel-1/position-locked -t bool -s true

# Panel appearance
xfconf-query -c xfce4-panel -p /panels/dark-mode -t bool -s false
xfconf-query -c xfce4-panel -p /panels/panel-1/background-style -t uint -s 1 --create
xfconf-query -c xfce4-panel -p /panels/panel-1/background-rgba \
  --force-array -t double -s 0.9804 -t double -s 0.9569 -t double -s 0.9294 -t double -s 0.95 --create

# Remove pager (plugin-4, plugin-5)
xfconf-query -c xfce4-panel -p /plugins/plugin-4 -r -R
xfconf-query -c xfce4-panel -p /plugins/plugin-5 -r -R

# Swap tasklist → docklike (install first: sudo apt install xfce4-docklike-plugin)
xfconf-query -c xfce4-panel -p /plugins/plugin-2 -t string -s "docklike"
xfconf-query -c xfce4-panel -p /plugins/plugin-2/grouping -r 2>/dev/null

# Add volume plugin (ID 19)
xfconf-query -c xfce4-panel -p /plugins/plugin-19 -t string -s "pulseaudio" --create

# Set plugin order
xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids \
  --force-array -t int -s 1 -t int -s 2 -t int -s 3 -t int -s 6 -t int -s 19 -t int -s 7 -t int -s 8 -t int -s 9 -t int -s 10

# Clock
xfconf-query -c xfce4-panel -p /plugins/plugin-8/digital-format -t string -s "%a %d  %H:%M" --create
xfconf-query -c xfce4-panel -p /plugins/plugin-8/digital-font -t string -s "JetBrains Mono Bold 14" --create

# Restart panel (SAFE method — avoid xfce4-panel -r, it sometimes kills the panel)
pkill xfce4-panel && xfce4-panel &
```

### Keybindings Added

#### Application Shortcuts (`xfce4-keyboard-shortcuts`, commands channel)
```bash
xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>t" -t string -s "alacritty" --create
xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>l" -t string -s "xflock4" --create
xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/XF86AudioLowerVolume" -t string -s "pactl set-sink-volume @DEFAULT_SINK@ -5%" --create
xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/XF86AudioRaiseVolume" -t string -s "pactl set-sink-volume @DEFAULT_SINK@ +5%" --create
xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/XF86AudioMute" -t string -s "pactl set-sink-mute @DEFAULT_SINK@ toggle" --create
```

#### Window Manager Shortcuts (`xfce4-keyboard-shortcuts`, xfwm4 channel)
```bash
xfconf-query -c xfce4-keyboard-shortcuts -p "/xfwm4/custom/<Super>Left" -t string -s "tile_left_key" --create
xfconf-query -c xfce4-keyboard-shortcuts -p "/xfwm4/custom/<Super>Right" -t string -s "tile_right_key" --create
```

#### Already present (no action needed)
- `<Super>e` → thunar
- `Print` → xfce4-screenshooter
- `<Primary><Alt>l` → xflock4

### Known Issues / Lessons

- **`xfce4-panel -r` is unreliable** — sometimes kills the panel without restarting it. Always use `pkill xfce4-panel && xfce4-panel &` instead.
- **Panel `dark-mode=true`** forces white text on all plugins regardless of background color. Must be disabled when using a light panel background.
- **XFCE position codes**: `p=6` = TOP, `p=10` = BOTTOM. (Not intuitive — document this.)
- **xfconf changes are live** — most panel settings apply immediately without restarting the panel. Only structural changes (adding/removing plugins) need a restart.
- **Clock format affects perceived size** — a long format string like `%a %d  %H:%M` can make the font appear smaller. Shorten the format tomorrow to let Bold 14 breathe.

### Flatpak Setup (user doing independently)
```bash
sudo apt install flatpak
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
# Then reboot
```
Usage: `flatpak search <name>`, `flatpak install flathub <id>`, `flatpak update`

### Pending for Next Session
1. Fix clock — shorten format (e.g. `%H:%M`) so Bold 14 is actually readable
2. Verify Fn+F2/F3/F4 volume keys work (use `xev` if not)
3. GPU stability check — first full day on NVIDIA 550.163.01 + Debian kernel
4. Continue ricing (compositor effects, wallpaper, anything else)
5. Application installs

### Status
**Ricing: mostly complete.** Panel functional. Clock size fix pending tomorrow.

---

## Session #10 — February 17, 2026 — Debian 13 Baseline, NVIDIA Driver, Mirror, Autologin

### Purpose
First session on the new Debian 13 + XFCE system. Establish baseline, install NVIDIA driver, optimize apt mirrors, configure autologin, and plan desktop ricing.

### System Profile (New — Debian 13)
- **OS**: Debian 13 (Trixie), XFCE, X11
- **Kernel**: 6.12.69+deb13-amd64
- **GPU**: NVIDIA GeForce GTX 1060 3GB — Driver 550.163.01 (post-session)
- **Storage**: 232.9G SSD (system, 3% used) + 465.8G external HDD (84% used)
- **RAM**: 15GB, swap 12GB (partition)
- **Display Manager**: LightDM
- **Shell**: bash

### Findings

#### 1. System Running on Nouveau (Open-Source Driver)
- Debian installed `xserver-xorg-video-nouveau` by default — no proprietary driver
- `nvidia-smi` not found, no kernel module
- `nouveau: pmu: firmware unavailable` in dmesg — GPU running without power management firmware (fixed clock, no dynamic scaling)
- `nouveau: BIT table 'A' and 'L' not found` — related power table warnings

#### 2. Log Check — Clean
- Zero failed systemd services ✓
- Zero priority-3 (error) journal entries ✓
- Minor warnings only:
  - ALSA udev GOTO label bug (cosmetic, upstream packaging issue)
  - LightDM gkr-pam unable to locate daemon control file (harmless)
  - LightDM pam_systemd failed to release greeter session (cosmetic)
  - ACPI MWAIT C-state 0x0 not supported (16x) — same known ASRock B450M BIOS bug as Fedora sessions

#### 3. Ethernet Negotiated at 100 Mbps Instead of 1000 Mbps
- `cat /sys/class/net/enp4s0/speed` → 100
- Speed test confirmed ~86 Mbps (matches 100 Mbps link ceiling after overhead)
- Cause: cheap cable extender between PC and router degrading signal quality
- Fix: replace the extender or run a direct cable — **NOT a software issue**

#### 4. Apt Mirror Suboptimal
- Default `deb.debian.org` CDN benchmarked at ~70 Mbps
- Chilean mirrors benchmarked: `ftp.cl.debian.org` fastest at ~83 Mbps
- Switched to Chilean mirror

#### 5. non-free Already Enabled
- `sources.list` had `main contrib non-free non-free-firmware` — NVIDIA install ready without changes

### Actions Taken

#### NVIDIA Driver Installation
```bash
sudo apt install linux-headers-$(uname -r)
sudo apt install nvidia-driver
sudo dkms autoinstall
sudo reboot
```
- Note: `linux-headers` was missing — DKMS skipped module build with warning. Always install headers first.
- DKMS generated self-signed MOK certificate and signed all 5 modules (Secure Boot is disabled — no enrollment needed)
- Post-reboot: `nvidia-smi` confirmed 550.163.01, 32°C, 167 MiB VRAM, GPU working correctly

#### Apt Mirror Switch
```bash
sudo sed -i 's|http://deb.debian.org/debian|http://ftp.cl.debian.org/debian|g' /etc/apt/sources.list
sudo apt update && sudo apt upgrade
```
- Upgraded: `libpng16-16t64` (security update)
- Security mirror (`security.debian.org`) left unchanged

#### Autologin Configuration
```bash
sudo groupadd -f autologin && sudo gpasswd -a francisco autologin
sudo sed -i '/^\[Seat:\*\]/a autologin-user=francisco\nautologin-user-timeout=0' /etc/lightdm/lightdm.conf
```
- Adds two lines directly after `[Seat:*]` in `/etc/lightdm/lightdm.conf`
- Requires user in `autologin` group for LightDM PAM service — **both steps are mandatory**
- **Pending verification**: reboot to confirm autologin works

### Ricing Plan (Tasks 7–13 — User Executing Manually)
User is manually completing the following before next session:

| # | Task | Commands |
|---|---|---|
| 7 | JetBrains Mono Nerd Font | Download from Nerd Fonts GitHub → `~/.local/share/fonts/` → `fc-cache -fv` |
| 8 | Rose Pine GTK theme (Dawn) | Download from rose-pine/gtk GitHub → `~/.themes/` |
| 9 | Papirus icons | `sudo apt install papirus-icon-theme` |
| 10 | Apply XFCE theme | `xfconf-query` for GTK theme, icons, font, WM theme |
| 11 | Alacritty config | Rose Pine Dawn colors + JetBrains Mono in `~/.config/alacritty/alacritty.toml` |
| 12 | Starship | `sudo apt install starship` + `~/.config/starship.toml` + `~/.bashrc` |
| 13 | XFCE panel | Bottom panel — app menu / taskbar / systray / clock (next session) |

### CLAUDE.md Updated
- Changed "Fedora Linux" → "Debian Linux (Debian 13 Trixie, XFCE, X11)"

### Decisions Made
- NVIDIA 550.163.01 chosen — stable branch, pre-580.x Wayland regression, community-confirmed on GTX 1060
- `ftp.cl.debian.org` chosen as apt mirror — official Chile country mirror, fastest in benchmark
- Autologin via LightDM `[Seat:*]` config — standard, reversible, no extra packages
- Ricing: Rose Pine Dawn GTK + Papirus-Light icons + JetBrains Mono Nerd Font + Starship

### Quickstart Replication Script
```bash
# 1. Install kernel headers + NVIDIA driver
sudo apt install linux-headers-$(uname -r)
sudo apt install nvidia-driver
sudo dkms autoinstall
sudo reboot

# 2. Switch apt mirror to Chile
sudo sed -i 's|http://deb.debian.org/debian|http://ftp.cl.debian.org/debian|g' /etc/apt/sources.list
sudo apt update && sudo apt upgrade

# 3. Configure autologin (LightDM)
sudo groupadd -f autologin && sudo gpasswd -a $USER autologin
sudo sed -i '/^\[Seat:\*\]/a autologin-user=$USER\nautologin-user-timeout=0' /etc/lightdm/lightdm.conf
```

### Pending for Next Session
1. Verify autologin works after reboot
2. Verify Tasks 7–12 completed by user (font, theme, icons, Alacritty, Starship)
3. Complete Task 13 — XFCE panel layout (app menu, taskbar, systray, clock)
4. Monitor GPU stability (first session on 550.163.01 + Debian kernel)
5. Address external HDD storage (84% full — 73GB free)

### Status
**Autologin: configured, pending reboot verification.**
**NVIDIA 550.163.01: installed and confirmed.**
**Ricing: in progress (Tasks 7–12 user-executed).**

### Lessons
- On Debian, `linux-headers-$(uname -r)` is NOT installed by default — always install before any DKMS-based driver (NVIDIA, VirtualBox, etc.). DKMS silently skips the build if headers are missing.
- `deb.debian.org` is a CDN that should auto-route to the nearest mirror, but it doesn't always win — benchmark local country mirrors explicitly.
- LightDM autologin requires TWO things: the config file entry AND the user in the `autologin` group. Missing the group membership will silently fail.
- A 100 Mbps speed test result on a 900 Mbps plan is a strong signal of physical layer degradation — check cables and couplers before touching software.

---

## Session #12 — February 18, 2026 — Health Check, Theme Fix, Volume Keys, SSD Mount, Warning Cleanup

### Purpose
Routine health check after a day of software installs, followed by fixing four user-reported issues.

### Health Check Findings

#### System — Cleanest Session Yet
- **4 consecutive clean shutdowns** (systemd-exit) in previous boots — zero hard resets since migrating to Debian.
- **Zero failed services**, zero priority-3 errors, zero NVIDIA Xid errors on current boot.
- **GPU**: 21°C, 9W idle, 316 MiB / 3072 MiB VRAM — NVIDIA 550.163.01 stable.
- **RAM**: 3.5 GiB / 15 GiB used, swap untouched.
- **Disk**: / at 19% (39 GB used) — up from 3% due to new software installs. 167 GB free.

#### Minor Warnings (pre-fix)
- `gtk.css: border-spacing is not a valid property` — Rose Pine theme CSS using an unsupported GTK3 property.
- `wsdd daemon not found` — gvfs-wsdd trying to spawn the `wsdd` binary (not installed).
- `gnome-keyring: asked to register item login/2, but it's already registered` — two Chromium-based Flatpaks competing for the same keyring slot.

### Issues Fixed

#### 1. Black-on-black Error Message Windows (Rose Pine Dawn Theme)
- **Root cause**: `messagedialog.background` in `~/.themes/Rosepine-B-MB-Light/gtk-3.0/gtk.css` had `background-color: #191724` — the Rose Pine *dark* variant's background. The text was dark too, making dialogs unreadable.
- **Fix**: Changed `#191724` → `#faf4ed` (Rose Pine Dawn base color) in two rules: `messagedialog.background` and `messagedialog.background .titlebar`.
- **Theme reloaded** via xfconf-query toggle (no logout needed).

#### 2. Volume Keys Not Working (Fn+F2/F3/F4)
- **Root cause**: Keybindings were correctly set to `pactl set-sink-volume @DEFAULT_SINK@ ±5%` and `pactl set-sink-mute @DEFAULT_SINK@ toggle`, but `pactl` was not installed. Audio server is PipeWire 1.4.2 with `pipewire-pulse` compatibility layer.
- **Fix**: `sudo apt install pulseaudio-utils` — provides `pactl`, which works transparently with PipeWire-Pulse.

#### 3. Second SSD Auto-Mount
- **Device**: `/dev/sdb1`, ext4, label "Francisco's Main", UUID `391a3647-e6f6-4282-bcbc-df81840ffe8e`
- **Mount point**: `/media/main` (Debian convention)
- **fstab entry added**:
  ```
  UUID=391a3647-e6f6-4282-bcbc-df81840ffe8e  /media/main  ext4  defaults,nofail  0  2
  ```
- **Verified**: `df -h /media/main` shows 458 GB total, 362 GB used, 73 GB free, mounted rw.
- `nofail` option added so a missing drive won't block boot.

#### 4. Journal Warnings

| Warning | Fix | Status |
|---|---|---|
| `wsdd` not found | Created `/usr/local/share/gvfs/mounts/wsdd.mount` with `AutoMount=false` — overrides system file, survives package updates | Takes effect after reboot |
| `gtk.css: border-spacing` | Removed `border-spacing: 6px` from `dropdown > button > box, combobox > button > box` rule in Rose Pine theme | Fixed |
| gnome-keyring duplicate item | Caused by Chromium Flatpak + VSCodium Flatpak both registering "Chrome Safe Storage" in the same keyring slot. Applied `flatpak override --user --env=VSCODE_PASSWORD_STORE=gnome-libsecret com.vscodium.codium` to give VSCodium its own keyring path | Fixed |

### Actions Taken
1. Edited `~/.themes/Rosepine-B-MB-Light/gtk-3.0/gtk.css` — fixed `messagedialog.background` colors (dark → Dawn).
2. Edited `~/.themes/Rosepine-B-MB-Light/gtk-3.0/gtk.css` — removed invalid `border-spacing: 6px` property.
3. `sudo apt install pulseaudio-utils` — installed pactl for volume keybindings.
4. `sudo mkdir -p /media/main` + fstab entry + `sudo mount -a` — second SSD now auto-mounts.
5. Created `/usr/local/share/gvfs/mounts/wsdd.mount` with `AutoMount=false` — disables gvfs Windows network discovery.
6. `flatpak override --user --env=VSCODE_PASSWORD_STORE=gnome-libsecret com.vscodium.codium` — stops VSCodium competing with Chromium for keyring slot.

### Decisions Made
- `/media/main` chosen as mount point (Debian convention for secondary storage).
- gnome-keyring warning traced to two Chromium-based Flatpaks (Chromium + VSCodium/Electron) — fixed via Flatpak env override rather than disabling keyring integration.
- wsdd override placed in `/usr/local/share/` rather than editing system file in `/usr/share/` — survives package updates.

### Pending for Next Session
1. Verify wsdd warning is gone after this reboot.
2. Verify gnome-keyring duplicate is gone after reboot.
3. Monitor GPU — still on NVIDIA 550.163.01, Debian stable kernel. System has been crash-free since migration.

### Status
**All four issues resolved. System healthy. Rebooting.**

### Lessons
- `messagedialog.background` is a separate CSS rule from the general `.background` — light themes ported from dark themes often miss this, leaving dialogs with the old dark background color. Always check dialog-specific rules when porting a GTK theme.
- `pactl` is not installed by default on Debian even when PipeWire is running. PipeWire-Pulse provides the socket compatibility, but the `pactl` binary itself comes from `pulseaudio-utils` and must be installed separately.
- fstab `nofail` option is essential for secondary drives — without it, a missing or failed drive drops the system into emergency mode at boot.
- `/usr/local/share/` overrides `/usr/share/` for gvfs mount files — use this pattern to override system gvfs config without modifying package-owned files.
- Both Chromium and VSCodium (Electron) use the same "Chrome Safe Storage" keyring item path. When both run, the second one logs a duplicate registration warning. Fix: `VSCODE_PASSWORD_STORE=gnome-libsecret` for VSCodium.
- `border-spacing` is a standard CSS table property not supported by GTK3 CSS — it silently does nothing but logs a warning. Safe to remove from any GTK theme.

---

## Session #13 — February 18, 2026 — Post-Reboot Fixes, Theme Audit, Thunar Sidebar

### Purpose
Continuation of Session #12. Verified fixes after reboot, corrected the wsdd fix (wrong approach), fixed Thunar sidebar color, corrected gnome-keyring fix, and audited the Rose Pine theme for remaining dark-variant color leaks.

### Post-Reboot Findings

#### wsdd Fix — Wrong Approach, Corrected
- `/usr/local/share/gvfs/mounts/wsdd.mount` override did NOT work — gvfs only reads from `/usr/share/gvfs/mounts/`, not `/usr/local/share/`.
- The warning still appeared in the post-reboot journal.
- **Corrected fix**: Edited `/usr/share/gvfs/mounts/wsdd.mount` directly (package-owned file), changing `AutoMount=true` → `AutoMount=false`. Removed the non-working `/usr/local/share/` override.
- Takes effect on next login (gvfs daemon must restart).

#### xfce4-notifyd — Transient Crash, Self-Recovered
- Crashed once at 09:24:18 (exit code 1), restarted automatically at 09:24:27.
- Timing matched the GTK theme toggle we performed during Session #12 — notifyd was briefly confused when the theme switched mid-flight.
- Not a recurring issue, no action needed.

#### gnome-keyring Duplicate — Previous Fix Ineffective
- Warning still appeared after VSCodium open/close.
- Root cause of fix failure: `VSCODE_PASSWORD_STORE=gnome-libsecret` still uses gnome-keyring — both Chromium and VSCodium write a key named "Chrome Safe Storage" to the same item path (`/collection/login/2`), regardless of which backend is selected.
- **Corrected fix**: `flatpak override --user --env=VSCODE_PASSWORD_STORE=basic com.vscodium.codium` — `basic` makes VSCodium use a local file-based store instead of gnome-keyring entirely, eliminating the competition. Verify after reboot.

### Thunar Sidebar Active Item Color

#### Root Cause
- Thunar's side panel uses a `GtkTreeView` widget, NOT `GtkPlacesSidebar`.
- The `placessidebar.sidebar row:selected` rules (correctly styled in Dawn colors) don't apply to Thunar.
- `treeview.view:selected` rule had `background-color: #191724` (dark variant near-black) — another dark-theme leftover. Matched with `color: #faf4ed` (cream/white), producing the white-on-black appearance.
- **Fix**: Changed `background-color: #191724` → `background-color: #56949f` (Rose Pine Dawn foam/teal) in `~/.themes/Rosepine-B-MB-Light/gtk-3.0/gtk.css` line 60.
- Theme reloaded via xfconf-query toggle.

#### Scrollbar Overlap
- The sidebar's scrollbar appeared because the "Network" place was visible, making the list tall enough to scroll.
- User deactivated the Network place in Thunar — scrollbar gone, overlap moot.
- If scrollbar returns, teal highlight will still overlap it but is visually acceptable.

### Rose Pine Theme Audit — Remaining `#191724` Occurrences
Full scan of `~/.themes/Rosepine-B-MB-Light/gtk-3.0/gtk.css` for remaining dark-variant color:

| Line | Context | Verdict |
|---|---|---|
| 541, 554, 4865 | `color: #191724` on cream/light backgrounds | Correct — dark text on light bg |
| 773 | `button.osd` background | Intentional — OSD overlays are always dark |
| 4812, 7336, 7447 | `box-shadow` border outline | Minor, gedit-specific, not worth changing |

**Conclusion**: The two bugs we fixed (`messagedialog.background` and `treeview.view:selected`) were the only real offenders. Remaining uses of `#191724` are legitimate.

### Rose Pine Theme Fixes — Complete List (Sessions #12 + #13)
| Rule | Bug | Fix |
|---|---|---|
| `messagedialog.background` | `background-color: #191724` | → `#faf4ed` (Dawn base) |
| `messagedialog.background .titlebar` | `background-color: #191724` | → `#faf4ed` (Dawn base) |
| `treeview.view:selected` | `background-color: #191724` | → `#56949f` (Dawn foam/teal) |

### Actions Taken
1. Edited `/usr/share/gvfs/mounts/wsdd.mount` — `AutoMount=true` → `AutoMount=false`.
2. Removed `/usr/local/share/gvfs/mounts/wsdd.mount` (non-working override).
3. `flatpak override --user --env=VSCODE_PASSWORD_STORE=basic com.vscodium.codium` — corrected keyring fix.
4. Edited `~/.themes/Rosepine-B-MB-Light/gtk-3.0/gtk.css` line 60 — treeview selection color fixed.
5. Deactivated Network place in Thunar (user action) — eliminated scrollbar overlap.

### Decisions Made
- Scrollbar overlap in Thunar sidebar: accepted as-is for now. Teal color is visually acceptable even if it extends under the scrollbar.
- OSD buttons (`button.osd`) kept dark — correct behavior for overlay controls.
- gedit box-shadow outlines not changed — minor, app not in daily use.

### Pending for Next Session (after reboot)
1. Verify wsdd warning is gone (took effect on this login — should be clean next boot).
2. Verify gnome-keyring duplicate is gone (VSCodium `basic` store fix).
3. System stability monitoring — crash-free since Debian migration.

### Status
**All fixes applied. Rebooting to verify.**

### Lessons
- **Correction from Session #12**: `/usr/local/share/` does NOT override `/usr/share/` for gvfs mount files. The gvfs daemon only reads from `/usr/share/gvfs/mounts/`. Edit the system file directly, or use `dpkg-divert` for a package-safe override.
- Thunar uses `GtkTreeView` for its sidebar, not `GtkPlacesSidebar`. CSS rules targeting `placessidebar` have no effect in Thunar — target `treeview.view:selected` instead.
- `VSCODE_PASSWORD_STORE=gnome-libsecret` and `VSCODE_PASSWORD_STORE=basic` are very different: `gnome-libsecret` still uses the keyring (and can still clash), `basic` bypasses keyring entirely.
- When auditing a ported GTK theme for light/dark mix-ups, grep for the dark variant's background color (`#191724` for Rose Pine) and check each hit: is it used as a background or as text? Background = almost always wrong in a light theme; text = often correct.
- xfce4-notifyd can crash transiently when the GTK theme is toggled while a notification is in flight — it self-recovers in seconds and is not a real problem.

---

## Session #16 — February 18, 2026 — Idle Freeze Investigation, DPMS Fix

### Purpose
Investigate a system freeze that occurred during the 19:36 boot session. User reported the computer froze while they were away from it.

### Boot History at Session Start
- 21:08 — current boot (clean, ongoing)
- 19:36 → ~20:48 — **crash** (this session's subject)
- 15:55 → 19:36 — **crash** (Session #15 MCE event, previously investigated)
- 12:37 → 13:41 — clean shutdown

### Crash Investigation

#### What Was Ruled Out
| Cause | Evidence | Verdict |
|---|---|---|
| AMD MCE | No hardware error entries in current boot dmesg (unlike 15:55 crash which left MCE in registers) | **Ruled out** |
| Kernel panic | pstore empty (no dump written) | **Ruled out** |
| Package change causing crash | apt/dpkg logs show last install was rasdaemon at 19:54; the 20:12 `apt install libnvidia-gl-550:i386` FAILED silently — no entry in apt history or dpkg log | **Ruled out** |
| nvidia-modprobe version mismatch (570.133.07-1 vs 550.163.01-2) | Present since initial nvidia-driver install on Feb 17 — not new, system was stable before | **Not the cause** |

#### Key Finding: User Was Away From Computer
User confirmed they were not at the machine when it froze. This rules out user-triggered GPU load (gaming, video). Points to idle/background cause.

#### Root Cause Identified: DPMS Display Power Transition
- DPMS was enabled with Standby=600s, Off=900s
- After ~10–15 min idle, X11 signaled the NVIDIA driver to enter display power-save mode
- NVIDIA driver on X11 can hang during DPMS state transitions (known issue)
- The entire X11/display session froze; kernel could not log the event before hard reset
- xfce4-power-manager was barely configured (only power-button-action=3); all DPMS came from raw X11 defaults

#### Side Finding: libnvidia-gl-550:i386
- User attempted `sudo dpkg --add-architecture i386` + `sudo apt install libnvidia-gl-550:i386` to try to fix WoW
- Package does not exist in Debian repos — install failed immediately (apt session opened/closed in <1 second)
- i386 architecture was left registered but no i386 packages were installed

### Actions Taken
1. Disabled DPMS and screen blanking immediately (current session):
   ```bash
   xset dpms 0 0 0 && xset s off
   ```
2. Disabled DPMS persistently via xfce4-power-manager (survives reboots):
   ```bash
   xfconf-query -c xfce4-power-manager -p /xfce4-power-manager/dpms-enabled -t bool -s false --create
   xfconf-query -c xfce4-power-manager -p /xfce4-power-manager/blank-on-ac -t int -s 0 --create
   ```
3. Verified: `xset q` confirms DPMS Disabled, all timers at 0.

### Decisions Made
- DPMS disabled entirely (no monitor auto-sleep). User turns PC off when leaving, so no need for auto-sleep.
- i386 architecture cleanup deferred (harmless, pending `sudo dpkg --remove-architecture i386 && sudo apt update`).
- WoW fix (Flatpak filesystem override) still pending from Session #15.

### Pending for Next Session
1. Verify system stability — if no crashes with DPMS off, cause is confirmed.
2. Clean up i386 architecture: `sudo dpkg --remove-architecture i386 && sudo apt update`
3. Apply WoW Flatpak fix: `flatpak override --user --filesystem=/media/main com.valvesoftware.Steam`
4. Check rasdaemon for any new MCE entries: `ras-mc-ctl --summary`
5. Monitor GPU (NVIDIA 550.163.01) — still the primary stability concern.

### Status
**DPMS fix applied. Monitoring for recurrence.**

### Lessons
- An idle freeze (user away from machine) is a strong indicator of display power management interaction with the GPU driver. Always check DPMS settings when a freeze happens with no user activity.
- On X11 + NVIDIA, raw DPMS transitions (xset) can trigger driver hangs. XFCE Power Manager provides a more controlled path, but disabling entirely is safest for users who don't need auto-sleep.
- `dpkg --add-architecture` persists across reboots (stored in /var/lib/dpkg/arch) but does NOT appear in dpkg.log. Check `dpkg --print-foreign-architectures` explicitly.
- If `apt install <package>` leaves no entry in apt/history.log and no entry in dpkg.log, the install failed — the package likely doesn't exist for that arch.
- The nvidia-modprobe package in Debian Trixie ships at version 570.x even when the nvidia-driver is 550.x. This is expected Debian packaging behavior, not a real mismatch.
- rasdaemon cannot write to its SQLite database during a hard reset — so a crash that triggers rasdaemon shutdown before the write completes will show "No MCE errors" even if there was one. Always cross-check with dmesg of the next boot.

---

## Session #14 — February 18, 2026 — Routine Health Check

### Purpose
Post-reboot health check. Verify pending fixes from Session #13 (wsdd, gnome-keyring). Assess overall system stability.

### Findings

#### System Health — Clean
- Zero failed systemd services.
- Zero priority-3 (error) journal entries.
- Zero NVIDIA Xid errors.
- Two clean boots recorded today (09:24 and 15:55).

#### GPU — NVIDIA 550.163.01
- 36°C, 8.2W idle, 336 MiB / 3072 MiB VRAM. Healthy.
- Crash-free since Debian migration. This was the primary concern.

#### RAM / Swap
- 4.8 GiB / 15 GiB used. Swap: 0 used. Comfortable headroom.

#### Disk
- `/` → 23% (47G / 216G). Fine.
- `/media/main` → 84% (362G / 458G). Stable, not growing.

#### Pending Fix Verdicts

| Item | Status |
|---|---|
| gnome-keyring duplicate registration | **FIXED** — `asked to register item login/2` warning gone. VSCodium `basic` store fix confirmed working. |
| wsdd warning | **PARTIAL** — Old `wsdd daemon not found` warning gone, but new warning: `gvfsd-network: Couldn't create directory monitor on wsdd:///. Error: The specified location is not mounted`. Different message, same source. Deferred to next session. |

#### New Warnings (low priority, deferred)
- `xdg-desktop-portal: Unhandled parent window type / Failed to associate portal window with parent window` — Repeated 5 times. Cosmetic. Happens when Flatpak apps open file dialogs on X11; portal can't identify the native parent window. Dialogs still work. Common on X11 + XFCE + Flatpak.
- `VSCodium: Error registering Steam/steamapps — Invalid fd passed` — VSCodium tried to watch Steam folder through Flatpak portal, got invalid fd. Graceful failure, nothing broken.
- `wireplumber: BlueZ not available / UPower no battery` — Expected on a desktop PC. Informational only.

### Actions Taken
- None. Read-only health check session.

### Decisions Made
- wsdd fix deferred to next session (low priority).
- xdg-desktop-portal and VSCodium/Steam warnings noted but not actioned (cosmetic, no user impact).
- Primary concern (GPU stability / no crashes) confirmed healthy. Session closed.

### Pending for Next Session
1. wsdd warning — take another pass at the fix.
2. Continue monitoring GPU stability (NVIDIA 550.163.01 + Debian kernel).

### Status
**System healthy. No crashes. Monitoring.**

### Lessons
- `VSCODE_PASSWORD_STORE=basic` (Flatpak env override for VSCodium) confirmed effective — eliminates gnome-keyring duplicate registration by using a local file-based store instead of the keyring entirely.
- xdg-desktop-portal `Unhandled parent window type` is a known cosmetic issue on X11 with Flatpak apps. It does not affect functionality — safe to ignore.
- The primary migration goal (GPU crash elimination) is confirmed. After 9 sessions of chasing NVIDIA 580.x instability on Fedora, Debian 13 + NVIDIA 550.163.01 + XFCE/X11 has been crash-free.

---

## Session #15 — February 18, 2026 — Crash Investigation, MCE, WoW Flatpak

### Purpose
Investigate a spontaneous system reboot that occurred during the previous boot session (15:55–19:36).

### Crash Investigation

#### Confirmed: Hard Reset (Not Clean Shutdown)
- `sudo last -x` showed `"crash"` for the 15:55 boot — vs `"shutdown"` for all clean boots.
- Kernel log ended at 19:19:45, system rebooted at 19:36:29 — 17 minutes of silence.
- No clean shutdown sequence in journal. Hardware-level reset.

#### What Was Ruled Out
| Cause | Evidence | Verdict |
|---|---|---|
| NVIDIA driver (Xid) | Zero Xid errors in 3.5h session | **Ruled out** |
| Thermal | CPU at 24.6°C (k10temp) | **Ruled out** |
| RAM | memtest86+ 5 passes clean, 2133 MHz stock | **Ruled out** |
| Kernel panic | pstore empty (efi_pstore registered but no dump written) | **Ruled out** |
| OOM killer | No entries in journal | **Ruled out** |

#### Root Cause: AMD MCE (Machine Check Exception)
Recovered from CPU MCE bank registers on the next boot:
```
[0.732560] mce: [Hardware Error]: Machine check events logged
[0.732564] mce: [Hardware Error]: CPU 12: Machine Check: 0 Bank 5: bea0000000000108
[0.732591] mce: [Hardware Error]: TSC 0 ADDR 1ffffb51181c0 MISC d012000100000000 SYND 4d000000 IPID 500b000000000
[0.732626] mce: [Hardware Error]: PROCESSOR 2:800f11 TIME 1771454174 SOCKET 0 APIC 9 microcode 8001139
```
- **UC=1** (Uncorrectable error), **PCC=1** (Processor Context Corrupted)
- **SYND 4d000000** — non-zero syndrome = actual data integrity failure detected
- **ADDR 1ffffb51181c0** — address in AMD data fabric / PCIe MMIO range (>256 TB, above physical RAM)
- **pstore empty** = hardware reset the machine before the kernel could react — no panic was written
- **SP5100 TCO watchdog** is present and loaded

#### Assessment
Most likely a transient PCIe / data fabric error. Steam attempted to initialize the GPU at ~17:00 and failed repeatedly. A failed PCIe transaction may have left the AMD data fabric in an unstable state; hours later, a second access triggered the uncorrectable error. Same geographic territory as the Fedora MCE sync flood (reset reason 0x08000800) but different bank and no Xid errors — the NVIDIA 550.x driver itself did not hang.

**Context:** This was the FIRST crash since migrating to Debian. Previously crashed every 1–3 hours on Fedora. This appears to be a low-frequency hardware event, not a systematic driver bug.

### Actions Taken
1. `sudo apt install rasdaemon edac-utils` — installed MCE monitoring daemon.
2. `sudo systemctl enable --now rasdaemon` — rasdaemon now running.
3. `ras-mc-ctl --summary` — clean post-install (historical crash not captured; rasdaemon wasn't running during it).

### WoW Private Server Client — Not Working

#### Setup
- Game: World of Warcraft 3.3.5a (WotLK private server client, HD-modded)
- Location: `/media/main/Games/WoW 3.3.5a HD/WoW.exe`
- Launcher: Steam Flatpak, GE-Proton10-32, Sniper runtime
- Shortcut type: Non-Steam game (App ID 3398439703)

#### Symptoms
All game processes exit with code -1 within 2–20 seconds. Three attempts failed.

#### Incorrect Diagnosis (Corrected During Session)
Initially suspected missing 32-bit NVIDIA libraries. **This was wrong.** `flatpak list | grep nvidia` confirmed all four Flatpak NVIDIA extensions are correctly installed, including `org.freedesktop.Platform.GL32.nvidia-550-163-01` (32-bit). Debian does not ship i386 NVIDIA packages — the Flatpak extension is the correct mechanism.

#### Actual Root Cause: Flatpak Filesystem Permissions
`flatpak info --show-permissions com.valvesoftware.Steam` showed `/media/main` is not listed. The Steam Flatpak has no access to the second SSD. The document portal gave access to `WoW.exe` only — not the surrounding game directory (MPQ data files, DLLs, mods, realmlist.wtf). Wine/Proton crashed immediately trying to open game resources invisible to the sandbox.

**Also noted:** Steam launch options had `PROTON_USE_WINED3D=1 PROTON_NO_ESYNC=1 PROTON_NO_FSYNC=1` — workarounds to clear. Let GE-Proton use DXVK defaults (better for this DX9 client).

#### Fix — NOT YET APPLIED
```bash
flatpak override --user --filesystem=/media/main com.valvesoftware.Steam
```
Then: Steam → WoW → Properties → Launch Options → clear everything → restart Steam → test.

### Pending for Next Session
1. **Apply WoW fix** — Flatpak filesystem override + clear Steam launch options → verify WoW launches.
2. **Monitor MCE** — check `ras-mc-ctl --summary` at session start.
3. **System stability monitoring** — one crash in several days of Debian use.

### Status
**Crash: Diagnosed — AMD MCE, likely transient PCIe/data fabric event. Monitoring.**
**WoW: Fix identified, not yet applied.**

### Lessons
- `sudo last -x` is the fastest way to distinguish a crash (`crash`) from a clean reboot (`shutdown`).
- AMD MCE errors are stored in hardware registers that survive soft resets. The kernel reads them at the start of the *next* boot — MCE evidence appears in `dmesg` of the post-crash boot, not in the crashed boot's journal.
- pstore being empty rules out a kernel panic. If efi_pstore is registered but pstore is empty, the machine was reset by hardware before the kernel could react.
- Addresses above 256 TB on AMD Ryzen = AMD data fabric / PCIe MMIO range, not RAM. MCE with such an address = PCIe interconnect issue.
- **Flatpak NVIDIA 32-bit on Debian**: No i386 NVIDIA packages exist in Debian repos. Correct solution is `org.freedesktop.Platform.GL32.nvidia-VERSION` Flatpak extension. Check `flatpak list | grep nvidia` before diagnosing 32-bit GPU issues.
- Flatpak Steam's document portal grants access to a *specific file only*, not its parent directory. A game on a secondary drive needs `flatpak override --user --filesystem=/path` so Wine/Proton can access the full game folder.
- Always check `flatpak info --show-permissions com.valvesoftware.Steam` when a Flatpak game fails — missing filesystem access is a common and non-obvious cause.

---

## Session #17 — February 25, 2026 — Post-Vacation Health Check, Kernel/NVIDIA Fix

### Purpose
First session after ~3 days away. User returned to find desktop environment not loading. Health check after fix.

### Issue: Desktop Not Loading After apt upgrade

#### Root Cause
`apt upgrade` installed kernel 6.12.73+deb13-amd64 (previously on 6.12.69). The `linux-headers-6.12.73` package was NOT installed alongside it. Without headers, DKMS could not build the NVIDIA kernel module for the new kernel. X11 started without a GPU driver → LightDM/XFCE failed to load.

#### Fix Applied (by user in TTY)
```bash
sudo apt install linux-headers-6.12.73+deb13-amd64
sudo dkms autoinstall
sudo reboot
```
- DKMS confirmed: `nvidia-current/550.163.01` built for both 6.12.69 and 6.12.73.
- Desktop loaded normally after reboot.

### Post-Fix Health Check — All Clear

| Area | Status | Notes |
|---|---|---|
| Failed services | ✅ OK | 0 failed units |
| Journal errors | ✅ OK | 0 priority-3 errors |
| GPU | ✅ OK | 36°C, 28.6W, 225 MiB VRAM, driver 550.163.01 |
| RAM | ✅ OK | 2.5 GiB / 15 GiB, 0 swap |
| Disk / | ✅ OK | 24% (48G / 216G) |
| Disk /media/main | ✅ OK | 84% — stable, not growing |
| DKMS | ✅ OK | nvidia-current built for both kernels |
| rasdaemon | ✅ OK | Active, no new MCE errors |
| Boot history | ✅ OK | Clean shutdown before vacation (Feb 21), no crashes |

### Resolved Pending Items
- **WoW Flatpak fix** — user applied `flatpak override --user --filesystem=/media/main com.valvesoftware.Steam` independently. WoW 3.3.5a now running via Steam Flatpak + GE-Proton 10. **RESOLVED**.

### Resolved Pending Items (continued)
- **i386 architecture cleanup** — user ran `sudo dpkg --remove-architecture i386 && sudo apt autoremove`. **RESOLVED**.
- **Monitor blanking (DPMS)** — screen was still blanking after idle despite DPMS being disabled. Root cause: X11 screensaver (`xset s`) is separate from DPMS and was still active at 600s timeout. Fixed with `xset s off` + autostart entry at `~/.config/autostart/disable-screensaver.desktop` to persist across reboots. **RESOLVED**.

### Still Pending
- None.

### Boot History Note
On Feb 21, 4 short `lightdm :1` sessions appeared while the main `:0` user session was active. Not alarming — possibly LightDM greeter being triggered (switch-user, Steam overlay, or similar). No action taken.

### Status
**System healthy. Desktop restored. WoW working.**

### Lessons
- After `apt upgrade`, always verify that `linux-headers-$(uname -r)` is installed. Debian does not guarantee headers are pulled in automatically with a kernel update — this can silently break DKMS-built modules (NVIDIA, VirtualBox, etc.).
- If the desktop doesn't load after an upgrade, first suspect: (1) new kernel, (2) missing headers, (3) DKMS module not built. Check `uname -r` vs installed headers, then `dkms status`.
- GE-Proton 10 + Steam Flatpak + `/media/main` filesystem override = working WoW 3.3.5a on Debian 13. No 32-bit NVIDIA packages needed — Flatpak NVIDIA GL32 extension handles it.

---

## Session #18 — February 26, 2026 — Crash Investigation, PCIe MCE, BIOS Gen2 Fix

### Purpose
Investigate a spontaneous system reboot that occurred during boot -1 (16:43–18:22).

### Boot History at Session Start
- 0 (20:34) — current boot (clean, ongoing)
- -1 (16:43 → 18:22) — **crash** (this session's subject)
- -2 (13:30 → 14:33) — clean shutdown
- -3 (09:12 → 11:24) — clean shutdown

### Crash Investigation

#### Confirmed: Hard Reset (Not Clean Shutdown)
- `last -x` showed `"crash"` for the 16:43 boot.
- Journal from boot -1 ended abruptly at 18:22:46 with no shutdown sequence.
- No kernel panic: pstore empty.
- No priority-3 journal errors in the crashed boot.

#### Activity Before the Crash
| Time | Event |
|------|-------|
| 17:19 | `sudo apt install rofi` |
| 17:52 | `sudo apt install papirus-icon-theme` |
| 18:07 | `sudo apt install neovim` |
| 18:16:08 | **mGBA Flatpak launched** (`io.mgba.mGBA`) |
| 18:22:24 | **mGBA closed** — consumed 1m37s CPU, 309.7M memory peak |
| 18:22:46 | **Last journal entry** (Thunar/tumblerd) — system died here |

#### Why rasdaemon Showed "No MCE Errors"
rasdaemon starts at systemd boot second ~14. The MCE is logged by the kernel at second 0.73 (read from hardware registers). rasdaemon always misses early-boot MCEs. **Always cross-check with `sudo dmesg | head -80` for MCE evidence.**

#### Root Cause: AMD MCE — Identical to Session #15
Found in `sudo dmesg` of the current (post-crash) boot:
```
[0.731970] mce: [Hardware Error]: Machine check events logged
[0.731973] mce: [Hardware Error]: CPU 3: Machine Check: 0 Bank 5: bea0000000000108
[0.732000] mce: [Hardware Error]: TSC 0 ADDR 1ffff929b8028 MISC d012000100000000 SYND 4d000000 IPID 500b000000000
```

Comparison with Session #15:
| Field | Session #15 | Session #18 |
|-------|-------------|-------------|
| Bank | 5 | 5 |
| Status | `bea0000000000108` | `bea0000000000108` ← identical |
| SYND | `4d000000` | `4d000000` ← identical |
| IPID | `500b000000000` | `500b000000000` ← identical |
| ADDR | `1ffffb51181c0` | `1ffff929b8028` (same range) |

Bank 5 + IPID `500b...` = AMD data fabric / PCIe interconnect. Address >256 TB = PCIe MMIO space (not RAM). Syndrome `4d000000` = non-zero data integrity failure.

#### PCIe Link Evidence
`lspci -vv -s 06:00.0` confirmed:
```
LnkCap: Speed 8GT/s (Gen3), Width x16
LnkSta: Speed 2.5GT/s (downgraded), Width x16
```
The kernel itself labels the link "downgraded" — GPU supports Gen3 but sits at Gen1 at idle.

PCIe AER status (UESta, CESta) all clear — errors were wiped by the hardware reset, as expected.

ASPM L0s L1 supported — further confirms aggressive PCIe power management is active.

#### Full Trigger Chain
1. mGBA used the GPU via OpenGL for ~6 minutes
2. mGBA closed → GPU released OpenGL context → entered idle
3. NVIDIA driver downclocked PCIe link: Gen3 (8.0 GT/s) → Gen1 (2.5 GT/s)
4. PCIe link retraining triggered an uncorrectable error in the AMD B450 data fabric
5. Hardware killed the system instantly — kernel had no time to write anything

#### Session #15 Reassessment
Session #15 was logged as "likely transient PCIe/data fabric event." **This is now confirmed as a recurring, reproducible pattern.** The trigger is the same each time: GPU active → GPU idle → PCIe link retraining → MCE. Session #15 trigger was Steam GPU use; Session #18 trigger was mGBA.

#### Additional Contributing Factor: NVIDIA 550 GSP Firmware
Community research confirms:
- NVIDIA 550 series enabled GSP (GPU System Processor) firmware by default
- Multiple confirmed freeze/crash reports specifically in 550.x on Linux
- mGBA has historical NVIDIA OpenGL bugs (fixed progressively through 0.9.x–0.10.x)
- Known fix: `NVreg_EnableGpuFirmware=0`

### Fix Applied

#### Decision: BIOS Gen2 Only (No System File Changes)
User preferred not to modify system files. The BIOS fix is the cleaner, more direct solution:
- Forces PCIe link speed to Gen2 (5.0 GT/s) permanently
- Eliminates Gen3↔Gen1 speed changes and all associated link retraining
- Completely reversible (change BIOS back to Auto)
- Survives package updates, initramfs rebuilds, kernel upgrades
- Performance impact: negligible (<1% for GTX 1060 gaming/emulation)

**BIOS path (ASRock B450M/ac R2.0):**
> Advanced → AMD PBS → PCIe x16 Link Speed → **Gen2**

**(Pending user action — not yet applied.)**

#### Software Options (Deferred — Apply Only If BIOS Fix Is Insufficient)
Create `/etc/modprobe.d/nvidia-crash-fix.conf`:
```
options nvidia-current NVreg_PreserveVideoMemoryAllocations=1
options nvidia-current NVreg_EnableGpuFirmware=0
```
Then: `sudo update-initramfs -u && sudo reboot`

### DPMS / Suspend Clarification
- **System suspend (S3)**: Unaffected by BIOS Gen2 fix. Safe to use.
- **Monitor sleep (DPMS)**: Still disabled (from Session #16 fix). The BIOS Gen2 fix does NOT re-enable DPMS safety — DPMS transitions are a separate NVIDIA/X11 issue.
- **Safe monitor-off workaround**: Use XFCE screensaver (blank screen) instead of DPMS — monitor stays signaled, no power state transition for NVIDIA to choke on.

### Pending for Next Session
1. **Verify BIOS Gen2 fix** — confirm PCIe link no longer retrains after GPU-intensive use. Check with `cat /sys/bus/pci/devices/0000:06:00.0/current_link_speed` (should show 5.0 GT/s).
2. **Monitor MCE** — check `sudo dmesg | grep -i "machine check"` at next session start.
3. **If crash recurs**: Add NVIDIA modprobe options (PreserveVideoMemoryAllocations + EnableGpuFirmware=0).

### Status
**Root cause identified. BIOS fix pending user action. Monitoring.**

### Lessons
- **rasdaemon always misses early-boot MCEs.** The MCE is read from hardware registers at kernel second ~0.73 — before rasdaemon's systemd unit starts. Always run `sudo dmesg | head -80` to check for MCE evidence after a crash, regardless of what rasdaemon reports.
- **Session #15's "likely transient" MCE was wrong** — it was the first instance of a reproducible pattern. Two identical MCEs (same bank, same status, same syndrome, same IPID) under the same trigger (GPU active → idle) = systematic, not random.
- **`lspci -vv` "downgraded" label is diagnostic gold.** When the PCIe link shows "downgraded", the kernel is flagging that the link negotiated below capability. This is a direct indicator of dynamic speed scaling — the root mechanism behind the MCE crashes.
- **PCIe AER bits clear ≠ no PCIe errors.** AER status registers are typically cleared by the hardware reset that follows the crash. Absence of AER errors in the post-crash boot is expected and says nothing about what happened during the crash.
- **BIOS PCIe Gen2 fix is safer than software modprobe options** for this class of problem. It's hardware-enforced, reversible, and survives all software updates.
- **The MCE trigger pattern**: Any OpenGL/GPU application that runs long enough to cause the PCIe link to step up to Gen3, then exits, can trigger the Gen3→Gen1 retraining crash. mGBA confirmed. Steam confirmed (Session #15).

---

## Session #19 — February 27, 2026 — Freeze Investigation, DPM Misdiagnosis, Root Cause Open

### Purpose
Investigate a system freeze that occurred during boot -1 (15:41–~18:17). System froze (display unresponsive), user unplugged keyboard, computer went dark. `last -x` shows "crash" (not clean shutdown).

### Boot History at Session Start
- 0 (18:26) — current boot (clean, ongoing)
- -1 (15:41 → crash) — **this session's subject**
- -2 (12:57 → 14:21) — clean shutdown

### Key Findings

#### BIOS Gen2 Fix — Verified Working
`lspci -vv -s 06:00.0` confirmed:
```
LnkCap:  Speed 5GT/s          ← Gen2 cap enforced correctly
LnkCap2: 2.5-5GT/s            ← Gen3 (8GT/s) fully excluded
LnkCtl:  ASPM Disabled        ← ASPM already off on this link
LnkSta:  Speed 2.5GT/s (downgraded)  ← link still drops to Gen1 at idle
```
No MCE in current boot's dmesg. The Gen3→Gen1 crash pattern from Sessions #15/#18 is resolved.

#### The Gen1 Idle Drop — Not ASPM
Despite ASPM being disabled at the device level, the link still drops to Gen1 when the GPU idles. This is **NVIDIA driver P-state management** (part of the GPU's internal Gen/power state transitions when entering P8), not ASPM, not RTD3. It happens independently of ASPM.

#### GSP Firmware — Not Running on GTX 1060
`nvidia-smi -q | grep GSP` returned `GSP Firmware Version: N/A`. GTX 1060 is Pascal architecture — GSP requires Turing or newer. Any GSP-related fixes are irrelevant for this hardware.

#### Crash Timeline
- 15:41 — Boot, session started
- 15:42 — gcr-prompter (password prompt, likely logging into something)
- 16:06–16:30 — Multiple GPU client connections (AppArmor audit bursts): apps using OpenGL
- 16:29–16:30 — Peak RTKit activity: 12 threads / 8 processes (Google Meet + audio)
- 16:30 — **Last GPU audit entry** — Google Meet ended, user walked away
- 16:42 → 18:17 — System running quietly (CRON jobs, rtkit winding down 12→9 threads)
- 18:17:01 — **Last journal entry** (CRON hourly) — journald stopped writing here
- 18:26 — Current boot started (9-minute gap = crash window)

#### Trigger Identified
User confirmed: **Google Meet in Firefox ESR**, ended meeting, walked away. System froze while unattended. This matches the same trigger pattern as Sessions #15/#18 (GPU heavy use → GPU idle). However, the freeze occurred ~1.5 hours **after** the GPU went idle, not immediately — ruling out an instant PCIe-transition-caused crash.

#### Keyboard/Shutdown Mystery — Resolved
The system was in a partial freeze (display/GPU hung, kernel alive — evidenced by cron running at 18:17). When the keyboard was unplugged, the USB event likely pushed the already-degraded kernel into a full crash. `last -x` shows "crash" (not "shutdown") — no clean shutdown occurred. The keyboard did not trigger a logind power event; no such entries were logged.

`systemd-logind` was monitoring the SONiX keyboard (0C45:5004) for system buttons — but no KEY_POWER or shutdown event was ever logged. The "computer turned off" was a hard crash, not a clean shutdown.

#### What Was NOT Found
- No MCE (Bank 5 / data fabric pattern from Sessions #15/#18)
- No Xid or NVRM errors
- No kernel panic (pstore not checked but pattern consistent with empty)
- No OOM, no softlockup, no hung_task messages
- Silent deadlock: kernel alive, display/GPU driver frozen

### Wrong Diagnoses Made This Session (Important — Do Not Repeat)

1. **GSP firmware deadlock** — WRONG. GSP doesn't run on GTX 1060 (Pascal). `EnableGpuFirmware: 18` is a default value, GSP confirmed N/A.
2. **pcie_aspm=off** — WRONG for this issue. ASPM is already disabled on the GPU link (LnkCtl: ASPM Disabled). Would have done nothing.
3. **NVreg_DynamicPowerManagement=0** — WRONG. This parameter controls RTD3 (Runtime D3 — complete GPU power-off for laptops with hybrid graphics). Requires Turing+. Does NOT control PCIe link speed on Pascal. Would have done nothing.

### Root Cause
**UNKNOWN.** Most likely an NVIDIA 550.x driver silent deadlock (550.163 has 68 documented bugs in Debian 13, 57 unresolved). The 1.5-hour delay between GPU going idle and the actual freeze suggests either:
- A slow memory/resource leak in the NVIDIA driver that reached a tipping point
- A driver deadlock triggered by some unrelated system event after 18:17
- A separate, unidentified hardware or kernel issue

### Actions Taken
- **None** — no modprobe changes, no kernel parameter changes. User correctly demanded proof before any changes. All three proposed fixes were withdrawn after research revealed them to be incorrect.

### Pending for Next Session
1. **Enable better crash logging** — set up journal retention and GPU hang verbose logging so next freeze produces actual evidence. Run: `sudo journalctl --disk-usage` to start.
2. **Investigate NMI watchdog / kdump** — if a kernel hang occurs again, having a crash dump would identify the exact stuck call.
3. **Check if nvidia-driver 560.x+ is available** via Debian backports or alternative source — 550.x is the only version in Trixie repos currently.
4. **Monitor pattern** — if freeze recurs under same conditions (heavy GPU use followed by idle period), it's reproducible and we can plan targeted logging.

### Status
**Freeze: Root cause unidentified. No changes made. Monitoring.**
**PCIe MCE crashes: Resolved by BIOS Gen2 fix.**

### Lessons
- **Always verify GSP support by GPU architecture before diagnosing GSP issues.** Pascal (GTX 10xx) does NOT use GSP firmware. Turing (RTX 20xx) and newer do. Check with `nvidia-smi -q | grep GSP`.
- **ASPM state and PCIe link speed are independent mechanisms.** ASPM disabled (LnkCtl) does NOT prevent the NVIDIA driver from changing link speed via P-state transitions. They are separate registers.
- **NVreg_DynamicPowerManagement controls RTD3, not PCIe link speed.** RTD3 = complete GPU power-off (laptops only, Turing+ only). PCIe link speed changes on Pascal are driven by GPU P-state transitions in the NVIDIA driver, not RTD3 or ASPM.
- **Timing matters for root cause.** If the freeze happens 1.5 hours after the suspected trigger, the trigger is not a direct cause. Correlation ≠ causation.
- **When three proposed fixes are wrong in a row, stop and admit uncertainty.** Do not apply modprobe changes without verified research. The user was right to demand proof.
- **Silent freezes are the hardest to diagnose.** No MCE, no Xid, no kernel panic = likely a driver-level deadlock. Need crash dump / NMI watchdog data to identify the stuck call stack. Cannot be diagnosed from journal alone.
- **`last -x` showing "crash" vs "shutdown"** distinguishes hard crash from logind-initiated shutdown. Always check this first.

---

## Session #16 — February 28, 2026 — Network Speed Stuck at 100Mbps

### Issue
Ethernet connection capped at 100Mbps while another computer on the same Gigabit switch reached 1Gbps. User assumed the problem was in their computer.

### Findings
- Interface: `enp4s0`, driver: `r8169`, chip: Realtek RTL8168 (PCI ID 10EC:8168)
- `ethtool` output revealed the key clue: **link partner (switch port) was only advertising 10/100Mbps**, not 1000baseT
- User's NIC was correctly advertising 1000baseT/Full — the computer was NOT the problem
- Root cause: **faulty Cat5e cable** — a damaged cable can pass 100Mbps (uses 2 pairs) but fail at 1Gbps (requires all 4 pairs), causing the switch port to downgrade its advertised capabilities

### Actions Taken
- Installed `ethtool` via apt
- Ran `sudo ethtool --set-eee enp4s0 eee off` (tested EEE hypothesis — did not fix it)
- Ran `/sbin/ethtool enp4s0` — revealed link partner only advertising 100Mbps
- User replaced the cable → resolved

### Decisions Made
- Investigated EEE (Energy Efficient Ethernet) first based on web research — plausible but wrong in this case
- `ethtool` link partner advertisement was the decisive diagnostic step

### Status
Resolved — cable replacement fixed the issue.

### Lessons
- **Always check `ethtool` link partner advertised modes first.** If the switch isn't advertising 1000baseT, the problem is upstream of the NIC (cable or switch port), not the computer.
- **A "working" cable at 100Mbps does not mean it's good.** 100Mbps only uses 2 wire pairs; 1Gbps needs all 4. A damaged cable can pass one but not the other.
- **Don't assume the problem is in the machine just because the other machine works.** The other machine may be on a different port or cable.
- **EEE is a real cause of 100Mbps downshift on r8169/RTL8168**, but rule out the physical layer (cable, switch port) first.

---

## Session #16 (continued) — General Health Check + WoW MOP

### General System Health Check (post cable fix)
- **RAM**: 3.2/15GB used, 0 swap — healthy
- **CPU**: ~95% idle, load 0.55 — healthy
- **Services**: No failed systemd units
- **System disk** (`/dev/sdb2`): 28% used — healthy
- **Main disk** (`/dev/sda1`): Was 88% (382/458GB) — cleaned up to 81% (350GB)
  - Deleted `/media/main/timeshift` (29GB) — leftover Fedora-era snapshot, root-owned, removed with `sudo rm -rf`
  - Emptied trash (4.6GB)

### NVIDIA vs Nouveau for Gaming
- **Verdict**: Proprietary NVIDIA driver is the only viable option for gaming on GTX 1060
- Nouveau cannot reclock Pascal GPUs (GTX 10xx) due to NVIDIA signed firmware requirement — GPU runs at boot clocks only (fraction of full speed)
- User is already on 550.x (Debian stable branch, pre-580.x regression) — correct choice, no change needed

### WoW MOP — Stormforge Private Server (Steam + Proton GE)
- **Symptom**: Login showed "SUCCESSFUL" → "Retrieving Realms" window appeared → stuck indefinitely
- **Client**: `MOP-5.4.8.18414-enUS-Repack`, launched via Steam as non-Steam game with Proton GE
- **Config.wtf**: realmlist and portal settings were correct (`logon.stormforge.gg` / `logon.stormforge.gg:1118`)
- **Network test**: Both ports 1118 and 3724 on logon.stormforge.gg were open and reachable
- **Resolution**: Resolved on its own — likely a transient server-side issue on Stormforge's end
- **Note**: WotLK client (Chromiecraft) works fine on same Proton GE setup — MOP issue was not local

### Status
All issues resolved.

### Lessons
- **Disk cleanup order**: Timeshift snapshots and trash are always the first targets. Timeshift snapshots are root-owned — use `sudo rm -rf /path/to/timeshift` or the timeshift CLI, not a file manager.
- **"Retrieving Realms" stuck on MOP private servers** is often transient (server side) or caused by a repack client incompatible with the server. Always check if the server provides their own official client.
- **Nouveau is never the answer for gaming** on NVIDIA hardware, especially Pascal and older with signed firmware restrictions.

---

## Session #20 — March 3, 2026 — Freeze After Suspend/Resume

### Purpose
Investigate a system freeze that occurred during boot -1 (16:16 → crash ~20:22). User was in the browser, had suspended at ~19:00 and resumed at ~19:45.

### Boot History at Session Start
- 0 (20:22) — current boot (clean, ongoing)
- -1 (16:16 → crash ~20:22) — **this session's subject**
- -2 (09:42 → 11:42) — clean shutdown

### Key Findings

#### Crash Timeline
| Time | Event |
|------|-------|
| 16:17 | Boot, user session started |
| 17:35 | Thunar activity |
| 19:05 | **Suspend started** (nvidia-suspend.service ran, S3 deep sleep) |
| 19:42 | **Resume** — nvidia-resume.service completed + xHCI USB controller error |
| 20:09 | xfce4-panel activity (user active in desktop) |
| 20:16 | xfwm4-workspace-settings launched |
| 20:21:30 | `sudo apt install xfce4-settings` completed (last journal entry) |
| ~20:22 | **Crash** — hard reboot |

#### xHCI USB Error on Resume
```
kernel: xhci_hcd 0000:01:00.0: xHC error in resume, USBSTS 0x401, Reinit
```
USBSTS 0x401 = STS_HALT (bit 0) + STS_CNR (bit 10). USB controller halted on resume, kernel performed full reinit. **Known quirk on AMD/Ryzen, not harmful, scope limited to USB devices — does NOT cause display freezes.** Explains why keyboard disconnect did not trigger a reboot this time (USB subsystem already reinitializing).

#### Root Cause: NVIDIA 550.x + Pascal + Debian 13 + X11 + Suspend
Confirmed real bug via web research:
- NVIDIA Developer Forums thread exists with **exact stack** (550.163.01, Debian 13, kernel 6.12, X11) documenting black screen / freeze on resume.
- GTX 1060 (Pascal) has had suspend/resume freeze issues since driver 375 era, never fully resolved.
- systemd 256 broke NVIDIA suspend (SLEEP_FREEZE_USER_SESSIONS incompatibility) — Debian's package includes the fix, but driver instability persists.
- ~39-minute delay between resume and freeze matches "delayed/accumulating" failure mode seen in multiple Pascal reports.

#### What Fixes Were Researched and Rejected
- `NVreg_PreserveVideoMemoryAllocations=1` — **REJECTED**. Mixed results for Pascal on X11; multiple reports of making things worse. Not safe to recommend.
- Disabling nvidia-suspend/resume/hibernate services — confirmed fix for some Debian 13 users, but user declined system changes.
- Kernel 6.12 has a separate non-NVIDIA suspend regression (Debian bug #1100153) — keep in mind if issues persist.

#### Pascal End-of-Life Note
NVIDIA driver 590 dropped Pascal entirely. Driver 550 receives security-only patches from October 2025. Suspend/resume bugs on Pascal will not be fixed upstream.

### Actions Taken
None — no system changes.

### Decision
User will use **shutdown instead of suspend** going forward. Eliminates the suspend/resume trigger entirely.

### Still Open
Session #19's freeze (Feb 27) happened WITHOUT suspend — GPU heavy use → idle → ~1.5h later → silent freeze. That root cause is still unknown. Avoiding suspend does not eliminate that risk.

### Status
**Session #20 freeze: root cause identified (NVIDIA 550 + Pascal + suspend = known unfixed bug). Resolved by avoiding suspend.**
**Session #19 silent freeze pattern: still open.**

### Lessons
- **xhci USBSTS 0x401 Reinit on resume = known AMD/Ryzen quirk, not harmful.** Do not chase it as a cause of display/GPU freezes.
- **NVreg_PreserveVideoMemoryAllocations=1 is NOT safe for Pascal + X11.** Documented to cause black screens on some Pascal setups. Do not propose without verified success for this hardware.
- **Always research before proposing modprobe changes.** Repeated lesson from Sessions #19 and #20.
- **NVIDIA 550.x + Pascal + X11 + S3 suspend is a confirmed, end-of-life, unfixed bug.** Cleanest mitigation: avoid suspend entirely.
- **The last logged event before a crash is not necessarily the cause.** The apt install completed successfully — coincidental timing, not causal.

---

## Session #21 — March 4, 2026 — Final Freeze Investigation, NVIDIA Pascal EOL Conclusion

### Purpose
Investigate a system freeze that occurred during boot -1 (15:49–~16:51). User reported freeze with no suspend, no warnings.

### Boot History at Session Start
- 0 (16:51) — current boot (clean, ongoing)
- -1 (15:49 → crash ~16:51) — **this session's subject**
- -2 (10:10 → 10:16) — clean shutdown (user turned on briefly)
- -3 (Mar 3, 20:23 → 22:12) — clean shutdown

### Key Findings

#### Crash Timeline (Reconstructed)
| Time | Event |
|------|-------|
| 15:49 | Boot, user session started |
| 15:49:37 | Firefox-ESR opened |
| 15:53:01 | NVIDIA device re-accessed (new GLX client connected) |
| 15:55:29 | **Three consecutive `/dev/nvidiactl` opens** — Xorg managing multiple simultaneous GLX contexts |
| 15:56:16 | Last normal kernel log entry (cupsd AppArmor) |
| ~15:57 | **User-space froze** — display unresponsive |
| 15:57:07 | Last user-space journal entry (tumblerd) |
| 16:49:50 | **Kernel logged RCU stall warning** — 53 minutes after display froze |
| ~16:51 | User hard-rebooted |

#### The Smoking Gun — RCU Stall Warning
```
Mar 04 16:49:50 WARNING: CPU: 2 PID: 18 at kernel/rcu/tree.c:334 rcu_watching_snap_recheck
Tainted: [P]=PROPRIETARY_MODULE, [O]=OOT_MODULE, [E]=UNSIGNED_MODULE
nvidia_drm(POE) present in module list
```
- `rcu_preempt` (PID 18) tried to force quiescent states on a CPU stuck in NVIDIA driver code
- The kernel waited 53 minutes before printing the warning
- No MCE (BIOS Gen2 fix confirmed still working), no panic, no OOM — pure driver deadlock

#### What the User Was Doing
Alacritty (GPU-accelerated terminal) running Claude Code + Firefox open. Three simultaneous GLX contexts (Firefox, Alacritty, xfwm4 compositor) active — Xorg logged three rapid `/dev/nvidiactl` opens at 15:55:29.

#### nvidia-persistenced — Researched and Rejected
Initially proposed as a fix. NVIDIA's own docs confirm: designed for compute-only platforms where the GPU is NOT used for display. On a desktop with Xorg, Xorg already holds the NVIDIA device open. Wrong recommendation.

#### No Confirmed Fix Exists
- NVIDIA 550.107.02 fix was notebook-specific, not applicable
- `nvidia-open-dkms` open-source driver requires Turing (RTX 20xx)+. Pascal excluded.
- No confirmed fix for NVIDIA 550.x + Pascal (GTX 1060) + X11 deadlock exists anywhere

### Decision
**User decided to migrate to Windows.**

Rationale: NVIDIA's Windows driver for GTX 1060 is stable and free of X11/compositor bugs. Pascal is fully supported on Windows. This freeze pattern is Linux-specific. Primary use case (browser + dev + WoW) works better on this hardware under Windows. Every other Linux issue was resolved; this one has no upstream fix.

### Status
**CLOSED. Root cause: NVIDIA 550.x + Pascal + X11 driver deadlock. No Linux fix available. Migration to Windows.**

### Lessons
- **The user-space journal ending ≠ the kernel dying.** On a display freeze, user-space stops logging but the kernel can run for hours. Always check `sudo journalctl -b N -k` separately — the kernel log may have critical entries long after user-space went silent.
- **RCU stall warnings with NVIDIA taint = driver deadlock signature.** `rcu_watching_snap_recheck` firing from `rcu_preempt` with `Tainted: P O E` and nvidia_drm in the module list = NVIDIA driver holding a kernel lock indefinitely.
- **nvidia-persistenced is for compute-only (CUDA, HPC), not X11 desktops.** Never propose this for display/freeze issues on a desktop.
- **When a proprietary driver is EOL on a platform, the bugs are permanent.** NVIDIA 550.x is the last driver for Pascal on Linux, security-only patches only. X11 deadlock bugs will not be fixed.
- **Correlation ≠ causation for freeze timing.** The freeze appeared to happen when Thunar opened. The actual cause was building 2+ minutes earlier. Always check the full kernel log timeline.

---

