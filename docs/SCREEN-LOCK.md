# Optional child unlock and screensaver

The default portable launcher leaves the child screen lock disabled. To set an
unlock word and idle time, start the parent dashboard in a second terminal:

```sh
python app/admin_server.py --lock-settings .local/data/lock-settings.json --token-file .local/parent/access.key
```

Open http://127.0.0.1:8877/ locally. Read the generated `.local/parent/access.key`
on your computer and enter it in the parent access form. Keep this key private.
Enable the lock, choose a child word and save. The default `run.py` data directory
uses the same lock-settings path automatically. For a custom data directory,
point both services at that directory's `lock-settings.json`.

Typed child letters remain visible for copying practice. Letter case is ignored.
The child word is stored as a salted password hash, separate from the parent key.
At the idle limit, a moon/star screensaver covers the apps and pauses audio.
Waking it asks for the same word and restores the child's open apps and writing.

The child web port never serves the parent controls. This is an application lock,
not an OS security boundary: use supervised desktop setup or separately configured
kiosk/account restrictions on a child's dedicated machine. See RASPBERRY-PI.md.
