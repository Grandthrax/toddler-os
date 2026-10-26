# Contributing

Use a fresh data directory and invented writing when developing. Do not include
children's names, writing, recordings, databases, keys or device addresses in a
patch or bug report. Keep generated data, models and recordings in `.local/`.

Run `python -B -m unittest discover -s tests -q` before proposing a change. Check
the affected app in Chrome/Chromium too. For speech changes, listen to actual
words and sentences: passing an audio hash check cannot judge pronunciation.

For the optional licensed-book browser checks, install Playwright in your own
development environment (`npm install --no-save playwright` and
`npx playwright install chromium`) and run `node tests/bookdash-browser.cjs`.
The harness creates a temporary data directory and local server automatically.
Set `LITTLE_PAGES_PYTHON` to your Python executable if it is not called `python`.
`CHROME_PATH` selects an existing Chrome/Chromium executable instead of the
Playwright browser. Screenshots/logs go to a temporary directory by default;
`LITTLE_PAGES_QA_DIR` can select another private output directory.

Keep core operation offline and avoid analytics, remote fonts, CDNs or cloud API
requirements. Make controls visual and large enough for a beginning reader. Save
progress without silently losing previous writing. Keep parent administration
outside the child interface.

For a new story, update its definition, pictures, prompt provenance and generated
speech together. Supply asset licences and use fictional demo characters. For a
deployment change, describe update, backup and recovery behaviour, including what
happens if installation is interrupted.

Open an issue for a substantial design change before doing a large implementation.
Small fixes can be submitted as pull requests with the problem, change and checks
performed. Contributions must be compatible with the project's GPL-3.0-only
licence; third-party notices must remain intact.
