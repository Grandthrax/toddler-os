# Raspberry Pi guide

## Hardware and supported setup

The reference machine is a Raspberry Pi 5 running 64-bit Raspberry Pi OS / Debian
13, with a monitor, USB keyboard, mouse and USB speaker. You also need a suitable
Pi power supply, cooling and reliable storage. Other Pi models and HDMI audio
have not been validated for this release. Use a spare SD card or back up your
existing installation first.

## First run on the normal desktop

These steps run under your ordinary account and leave desktop/login settings
alone. Internet is needed for installation.

1. Install Raspberry Pi OS with a desktop using Raspberry Pi Imager. Create your
   own account and password. Enable remote access only if you need it.
2. Boot the Pi, update it using the normal OS tools, and confirm the keyboard,
   monitor and speaker work in the normal desktop.
3. Download and extract this repository. Open a terminal in its folder.
4. Run `python3 run.py` and open
   `http://127.0.0.1:8876/?desktop-preview=1` in Chromium **on the Pi**.
5. Follow [audio setup](AUDIO.md) for the local reading voice and your phonics
   recordings. If needed, install `python3-venv` using your OS package manager.
   Run the app using `.venv/bin/python run.py` after installing the voice packages.
6. Complete a maths mission and a Space Cat book, write and read a short story,
   restart the app, and check the saved work is still there. Make a test backup.

The address uses loopback: a browser on another computer cannot open the Pi app
at its own `127.0.0.1`. Use a trusted remote-desktop session to view the Pi browser.
The preview has no remote authentication service and is not intended to be
exposed on your LAN or the internet.

## A desktop window versus a child appliance

The homepage imitates a desktop **inside a website**. In the normal desktop
preview, Alt+Tab, Alt+F4 and OS shortcuts still belong to Linux. Browser fullscreen
is useful for trying it, but does not restrict the OS account.

The original family appliance uses a separate restricted child account and
**Cage**, a small Wayland compositor running just Chromium. System services start
the local app and the child display session. Parent remote access is separate.
OS permissions and session configuration provide the restrictions; the webpage
does not block Linux shortcuts itself.

That existing installer assumes a particular parent login, device permissions,
USB speaker and recovery setup. It is not included as a generic installer in this
public preview. Until a portable kiosk installer has been tested, use this release
with supervision on the normal desktop. See [the roadmap](ROADMAP.md).

A public appliance installer needs to configure a child account without sudo,
an unprivileged app service, a Cage/Chromium session, shortcut/console restrictions,
network policy, parent access and a reliable way to restore the normal desktop.
It must also preserve saved books during updates. These are deployment tasks,
not switches in the website.
