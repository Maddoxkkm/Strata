# scratch/ — our local working set

Everything here is **ours**, not upstream Strata: the measurement harnesses we run against a live server,
the engine config they drive, cached PR diffs, and the notes we accumulate. Nothing in this directory is
needed to build or run the engine — `setup.py`, `serve/`, `src/`, `tools/` and the two launchers stay
where upstream puts them.

```
scratch/
  scripts/    the harnesses (see below) - run them with the repo's venv python
  configs/    strata-iq2_xs.json            the live engine config (gitignored: local state)
              strata-iq2_xs.shared-settings.json   the web UI's Chat settings, kept next to the config
              strata-iq2_xs.log           the engine's own log (append across restarts, gitignored)
              variants/ab-variants-*.json the A/B sets the harnesses replay
  reports/    UPDATES-*.md (what changed and what it measured), TRIAGE-*.md, OPTIONS-REFERENCE.md
              + options-inventory.csv (regenerate: scripts/make-options-inventory.py)
  prs/        cached PR diffs we triaged
```

## Running the harnesses

Run from **anywhere** with the repo's interpreter — every script resolves paths from the repo root, not
from the current directory:

```bash
cd /d/llm-dev/strata
.venv/Scripts/python.exe scratch/scripts/now.py              # current engine's prefill/decode, live server
.venv/Scripts/python.exe scratch/scripts/rate-ladder.py      # prefill rate vs prompt size, from all logs
.venv/Scripts/python.exe scratch/scripts/ab-group.py scratch/configs/variants/ab-variants-chunks.json
```

`ab-group.py` is the A/B harness: it stops the server, rewrites the config per arm, starts the engine,
sends the arm's prompt, and prints one line per arm (prefill, host staging ms, decode, RAM budget, from-files
share, disk MB/s). Variant files name their engine as a repo-relative path (`logs/binaries/*.exe`) and their
prompt as `logs/prompt*-ids.txt`, so both keep working wherever the variant file itself sits.

## Where things are written

Outputs stay in the project's own directories rather than here: `logs/` (bench logs, `logs/binaries/*.exe`,
prompt token files, `logs/dumps/`) and `scratch/configs/strata-iq2_xs.log` (the engine's log, next to the
config that names it).

## Starting the server

`run-iq2_xs.bat` (repo root) starts it from `scratch/configs/strata-iq2_xs.json`; `stop-server.bat` stops it.
Both are for you to run — a server started from an agent session dies with that session.
