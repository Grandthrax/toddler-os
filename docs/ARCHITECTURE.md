# How it works

```text
Keyboard / mouse / speaker
           |
Chrome or Chromium: pretend desktop and four web apps
           | HTTP on 127.0.0.1 only
Python server: stories, settings, missions and optional Piper reading
           |
SQLite database + local pictures, recordings, font and voice files
```

`run.py` starts `app/server.py`. The server binds to loopback and validates Host,
Origin and the custom request header for changes. Static files have a restrictive
Content Security Policy. This is a single-device app, not an internet server.

`app/core.py` handles settings, versioned free writing and optional local speech.
`app/ninja.py` and `ninja_content.py` handle maths missions and upgrades.
`app/storybooks.py` defines the two sample branching books and versioned page progress.
`app/static/` contains the frontend and bundled assets. There is no npm build or
external CDN. The server's only optional runtime dependencies are for speech.

SQLite revisions preserve earlier writing and optimistic version checks prevent
silently overwriting a newer save. Archiving hides stories without destroying
them. Tests use temporary databases, not real writing.

Letter feedback is a separate recording per letter. Reading new text uses Piper
with measured word alignments. Storybook word clips are taken from continuous
spoken sentences, rather than spelling out ambiguous isolated words. The maths
and storybook audio manifests record the text and WAV hashes. Regenerate those
recordings after changing content, using the builders in the repository root and
`--model /path/to/en_GB-cori-high.onnx`. Listen to the results as well as testing
hashes and alignments.

Ninja characters combine a masked body, weapon layer and rear power layer.
`app/static/ninja/gear-v2/prompts.json` records the generated asset prompts;
`ninja-upgrades.html` previews all four ranks in each path. AI-generated PNGs are
included as editable/replaceable assets; there are no hidden original 3D files.

The Python test suite covers storage, backup behaviour, request boundaries,
progression, upgrade choices, saved book choices and bundled asset integrity.
It does not prove Linux kiosk confinement, physical speaker reliability or every
browser interaction. Test those separately on the target machine.
