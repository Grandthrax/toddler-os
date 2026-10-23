import argparse
"""Generate bundled British spoken prompts with the existing offline Piper model."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "app"))
from core import Speech
from ninja_content import prompts

PROMPTS = prompts()


def main():
    import hashlib
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, required=True)
    speech = Speech(parser.parse_args().model)
    folder = HERE / "app/static/ninja/audio"
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {}
    old = json.loads((folder / "manifest.json").read_text())["prompts"] if (folder / "manifest.json").exists() else {}
    by_text = {entry["text"]:(folder / (key + ".wav")).read_bytes() for key,entry in old.items() if (folder / (key + ".wav")).exists()}
    for name, text in PROMPTS.items():
        file = folder / (name + ".wav")
        if name in old and old[name]["text"] == text and file.exists():
            audio = file.read_bytes()
        elif text in by_text:
            audio = by_text[text];file.write_bytes(audio)
        else:
            audio = speech.read(text);file.write_bytes(audio)
        by_text[text] = audio
        manifest[name] = {"text": text, "sha256": hashlib.sha256(audio).hexdigest()}
        print(name, len(audio), flush=True)
    (folder / "manifest.json").write_text(json.dumps({"voice": "en_GB-cori-high", "prompts": manifest}, indent=2) + "\n")


if __name__ == "__main__":
    main()
