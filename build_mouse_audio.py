import argparse
"""Build checked, offline British speech for the Mouse Missions picture blocks."""
from pathlib import Path
import hashlib
import json
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'app'))
from core import Speech
from mouse_content import prompts


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',type=Path,required=True)
    speech=Speech(parser.parse_args().model)
    folder=HERE/'app/static/mouse/audio';folder.mkdir(parents=True,exist_ok=True)
    manifest_path=folder/'manifest.json'
    previous=json.loads(manifest_path.read_text())['prompts'] if manifest_path.exists() else {}
    entries={}
    for name,text in prompts().items():
        file=folder/(name+'.wav')
        if not file.exists() or previous.get(name,{}).get('text')!=text:file.write_bytes(speech.read(text))
        entries[name]={'text':text,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
        print(name,flush=True)
    manifest_path.write_text(json.dumps({'voice':'en_GB-cori-high','prompts':entries},indent=2)+'\n')


if __name__=='__main__':main()
