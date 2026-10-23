# Parent guide

## Where everything is saved

By default, `.local/data/stories.sqlite3` holds writing, revisions, archived
stories, maths progress and picture books. `.local/data/settings.json` holds
parent learning settings. The browser stores the app's volume preference. The
desktop wallpaper choice is in the database. There is one local child's workspace;
this is not a multi-user school system.

Save files survive app updates if you keep `.local/`. Keep them private. No data
is uploaded by the application. Anyone with access to your OS account or its
files can still access the writing. The app does not encrypt the database.

## Change the on-screen letters

Run commands in the project folder using the same Python as the app. Change
settings between sessions, then reopen the story.

```sh
python app/manage.py --data-dir .local/data settings --letters masdt
python app/manage.py --data-dir .local/data settings --first 10
python app/manage.py --data-dir .local/data settings --auto-read-words on
```

The first two commands are alternatives. `--letters` specifies the child's
currently taught letters; `--first` uses the default teaching order. Physical
keyboard A–Z remains available independently of these buttons. Reading on Space
in Storybooks is part of that activity; `--auto-read-words` controls free writing.
There is no parent settings page inside the child interface.

## Back up and restore

Use a new filename each time:

```sh
python app/manage.py --data-dir .local/data backup .local/backups/stories-backup.sqlite3
```

This makes a consistent SQLite backup, including picture books and maths progress.
Copy `settings.json` separately if it exists. Keep another copy on a separate
drive; a backup on the same SD card will not survive a failed card.

To restore, stop the app first. Preserve the entire current `.local/data/`
directory elsewhere. Create a new empty data directory, put the chosen backup
there as `stories.sqlite3`, and copy the saved `settings.json` beside it. Then run
`python run.py --data-dir /path/to/restored-data`. Avoid mixing a restored database
with old `-wal` or `-shm` files. Try the restored copy before replacing your normal
data directory.

For plain-text copies of free-writing stories, including archived stories:

```sh
python app/manage.py --data-dir .local/data export .local/story-exports
```

This export does not include picture books or maths progress; use a database
backup for a complete recovery.

## Privacy when asking for help

Never attach `.local/`, a database, a backup or an existing browser profile to a
public issue. Reproduce problems using a new data directory, such as
`python run.py --data-dir .local/bug-demo --port 8877`, with invented writing.
Review screenshots and logs for names, writing, usernames and addresses.
