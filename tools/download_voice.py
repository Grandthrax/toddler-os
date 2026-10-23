"""Download the optional reference voice; verify bytes before installing."""
import argparse
import hashlib
from pathlib import Path
import tempfile
from urllib.request import urlopen

BASE = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/cori/high/'
FILES = {
    'en_GB-cori-high.onnx': '470b4dd634c98f8a4850d7626ffc3dfc90774628eeef6605a6dd8f88f30a5903',
    'en_GB-cori-high.onnx.json': '9e7fb5b5671612c22f3c81cbe46c1ae87b031a4632bcb509e499dad6f1e2adec',
}


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path,
                        default=Path(__file__).resolve().parents[1] / '.local/models')
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    print('Model provenance and terms: see THIRD_PARTY.md and the Cori model card.')
    for name, expected in FILES.items():
        destination = args.destination / name
        if destination.exists() and digest(destination) == expected:
            print(name + ': already verified')
            continue
        with tempfile.TemporaryDirectory(dir=args.destination) as temporary:
            candidate = Path(temporary) / name
            print('Downloading ' + name, flush=True)
            with urlopen(BASE + name, timeout=60) as response, candidate.open('wb') as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            if digest(candidate) != expected:
                raise SystemExit('Hash mismatch; download was not installed. Check the upstream release.')
            candidate.replace(destination)
        print(name + ': verified')


if __name__ == '__main__':
    main()
