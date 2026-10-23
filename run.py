"""Portable local launcher; no installation or system settings changes."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8876)
    parser.add_argument('--data-dir', type=Path, default=root / '.local/data')
    parser.add_argument('--model', type=Path, default=root / '.local/models/en_GB-cori-high.onnx')
    parser.add_argument('--phonics-dir', type=Path, default=root / '.local/phonics')
    args = parser.parse_args()
    command = [sys.executable, '-B', str(root / 'app/server.py'), '--port', str(args.port),
               '--data-dir', str(args.data_dir), '--phonics-dir', str(args.phonics_dir)]
    if args.model.is_file():
        command += ['--model', str(args.model)]
    else:
        print('Optional reading voice not installed. See docs/AUDIO.md.', flush=True)
    try:
        return subprocess.call(command)
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
