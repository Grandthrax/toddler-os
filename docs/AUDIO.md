# Offline sound setup

The bundled maths and Space Cat recordings work without additional packages.
Reading new writing uses Piper on this computer. Letter feedback uses your own
recorded sounds. Neither uses an online speech API or browser speech synthesis.

## Reading voice

Create a virtual environment in the project folder. On Windows:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python tools/download_voice.py
.venv\Scripts\python run.py
```

On Linux / Raspberry Pi OS:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tools/download_voice.py
.venv/bin/python run.py
```

The download tool retrieves the official Cori high model and its configuration
over HTTPS, checks the recorded SHA256 hashes, and stores them in `.local/models/`.
It does not download phonics. Read the model card linked in THIRD_PARTY.md before
using or redistributing a voice. Downloads require internet; playback does not.
The pinned speech environment was tested on Python 3.14 / Windows and ARM64 Pi.
If packages have no wheel for your Python/CPU, use a supported interpreter rather
than installing global packages with sudo.

Restart the app with this virtual environment's Python after setup. Try writing
`the red cat` in The Book and reading it. Piper reads natural language; it may
pronounce invented words unexpectedly. A missing or mismatched alignment disables
word highlighting instead of inventing timings.

## Phonics recordings

Create `.local/phonics/`. Supply `a.wav`, `b.wav`, … `z.wav` (OGG or MP3 also work)
containing the **letter sounds**, not the letter names. Use recordings you made
yourself or have permission to use. Listen to every sound and check pronunciation
against the child's school guidance. The default on-screen keys are m, a, s, d, t.

Do not upload privately licensed school packs or children's voice recordings to
this repository. The original private pack is not included. An open-licensed,
reviewed phonics pack is a planned improvement.

Start with `python run.py --phonics-dir /path/to/your/recordings` to use a different
folder. In the browser, `/api/settings` reports `voice_ready` and
`phonics_available`; neither includes writing.

## If sound stops

First check the desktop speaker control, OS output device and physical speaker.
The in-app control changes the app's playback volume, not the USB hardware's
mixer volume. Start at a comfortable level. Close other programs holding the
device, then restart the app/browser if necessary.

The private prototype needed a device-specific WirePlumber workaround and audio
recovery service for one USB speaker. Those hardware rules are not installed by
this preview. Include OS, speaker model and audio-service error messages in a bug
report, with personal details removed. Avoid blanket USB resets or running the
browser as root.
