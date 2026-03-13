# LinkedIn Job Form Automation

Automates filling LinkedIn work-experience forms using Playwright. Supports multiple entries via a JSON data file.

## What it does

- **`merge.py`** — Merges candidate data into a form schema to produce a filled form JSON.
- **`main.py`** — Opens a LinkedIn job application URL in a browser and auto-fills the work-experience form from the JSON.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install playwright
playwright install chromium
```

## Usage

**Step 1 — Fill in your details in `candidate_data.json` (a template is provided), then merge into the form:**
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
```
