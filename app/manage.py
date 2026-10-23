"""Parent-only settings and portable story exports; no admin HTTP endpoint."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from core import ORDER, Settings, Store

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--data-dir", type=Path, required=True)
parser.add_argument("--settings", type=Path)
actions = parser.add_subparsers(dest="action", required=True)
settings = actions.add_parser("settings")
choice = settings.add_mutually_exclusive_group()
choice.add_argument("--first", type=int, choices=range(1, len(ORDER) + 1))
choice.add_argument("--letters", help="Individual lowercase letters, e.g. masdt")
settings.add_argument("--auto-read-words", choices=("on", "off"))
export = actions.add_parser("export")
export.add_argument("destination", type=Path)
backup = actions.add_parser("backup")
backup.add_argument("destination", type=Path)
args = parser.parse_args()
config = Settings(args.settings or args.data_dir / "settings.json")
if args.action == "settings":
    changes = {}
    if args.first:
        changes["letters"] = ORDER[:args.first]
    elif args.letters is not None:
        changes["letters"] = list(dict.fromkeys(args.letters.replace(" ", "").lower()))
    if args.auto_read_words is not None:
        changes["auto_read_words"] = args.auto_read_words == "on"
    print(json.dumps(config.update(**changes) if changes else config.load(), indent=2))
elif args.action == "export":
    store = Store(args.data_dir, config)
    args.destination.mkdir(parents=True, exist_ok=True)
    for summary in store.stories(archived=None):
        story = store.story(summary["id"])
        (args.destination / (story["id"] + ".txt")).write_text(story["text"], "utf-8")
    print("Stories exported as plain text.")
elif args.action == "backup":
    store = Store(args.data_dir, config)
    if args.destination.exists():
        raise SystemExit("Choose a new backup filename")
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    with store.connect() as source, closing(sqlite3.connect(args.destination)) as destination:
        source.backup(destination)
    print("Consistent SQLite backup created; settings are backed up separately.")
