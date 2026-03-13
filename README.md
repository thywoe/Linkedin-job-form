# LinkedIn Job Form Automation

Automates filling LinkedIn work-experience forms using Playwright. Supports multiple entries via a JSON data file.

## What it does

- **`merge.py`** — Merges candidate data into a form schema to produce a filled form JSON.
- **`main.py`** — Opens a LinkedIn job application URL in a browser and auto-fills the work-experience form from the JSON.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## LinkedIn Authentication

The app does not handle login — you must authenticate manually before running.

1. Open a browser and log in to [linkedin.com](https://www.linkedin.com)
2. Navigate to the job's Easy Apply page and confirm you can see the application form
3. Copy the page URL — use it as the `--url` argument

> **Tip:** Run without `--headless` so you can intervene if LinkedIn prompts for verification.

## Usage

**Step 1 — Fill in your details in `candidate_data.json`, then merge into the form:**

`candidate_data.json` has two top-level fields:

- `candidate` — your full name (used for reference only)
- `entries` — list of work experience entries, each with:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | number | Unique per entry, determines fill order |
| `title` | string | Job title |
| `company` | string | Company name |
| `currentlyWorkHere` | boolean | Set to `true` to leave end date blank |
| `startMonth` | string | Full month name e.g. `"January"` |
| `startYear` | number | e.g. `2021` |
| `endMonth` | string | Full month name — omit or leave `""` if current role |
| `endYear` | number | Omit or leave `null` if current role |
| `city` | string | e.g. `"Lagos, Nigeria"` |
| `description` | string | Max 2000 characters |

Add as many entries as needed — the automation fills them in `id` order.

```bash
python3 merge.py --schema schema.json --candidate candidate_data.json --output work_experience_form.json
```

**Step 2 — Run the automation:**
```bash
python3 main.py --url https://www.linkedin.com/jobs/...
```

**Options:**
```
--url       LinkedIn job application URL (required)
--form      Path to filled form JSON (default: work_experience_form.json)
--headless  Run browser without UI
--dry-run   Preview entries without launching the browser
```

## Testing

Tests cover `merge.py` (data merging logic) and `automate.py` (form validation, dry-run output) — no browser required.

```bash
python -m pytest test_app.py -v
```

17 tests across three areas:

- **`TestMerge`** — single/multi-entry merging, missing files, skipped entries
- **`TestValidateForm`** — required fields, invalid months, year format, description length
- **`TestDryRun`** — output formatting, current-role display, description truncation

## Known Problems

| Problem | Cause | Fix |
|---|---|---|
| VSCode uses wrong Python / can't find packages | IDE picks system Python instead of `venv` | Add `.vscode/settings.json` with `"python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python3"` |
| `playwright install` fails or browser won't launch | Playwright binaries missing or outdated | Re-run `playwright install chromium` inside the activated `venv` |
| LinkedIn redirects or blocks the automation | Session expired or security check triggered | Log in manually first, run without `--headless` so you can complete any verification prompts |
| Form fields not found / selectors break | LinkedIn updated their UI | Open an issue with the field name and the selector that failed — selectors may need updating |
| `work_experience_form.json` is empty or malformed | Bad merge or wrong schema | Run with `--dry-run` to preview entries before launching the browser |
