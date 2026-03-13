"""
automate.py — Uses Playwright to fill a job-application form from work_experience_form.json.

Usage:
    python automate.py [--form work_experience_form.json] [--url <application-url>] [--headless]

Requirements:
    pip install playwright
    playwright install chromium
"""

import json
import argparse
import sys

def _import_playwright():
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
        return sync_playwright, PWTimeoutError
    except ImportError:
        print("Playwright is not installed. Run: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Selectors — adjust these to match the target site's actual HTML structure.
# ---------------------------------------------------------------------------
SELECTORS = {
    "add_more_button": "text=Add more",
    "save_button":     "text=Save",
    "title_input":     '[placeholder="Title"]',
    "company_input":   '[placeholder="Company"]',
    "currently_here":  'input[type="checkbox"][name="currentlyWorkHere"]',
    "start_month":     '[name="startMonth"]',
    "start_year":      '[name="startYear"]',
    "end_month":       '[name="endMonth"]',
    "end_year":        '[name="endYear"]',
    "city_input":      '[placeholder="City"]',
    "description":     "textarea",
}


# Human-readable labels for selector error messages
SELECTOR_LABELS = {
    "add_more_button": "Add more button",
    "save_button":     "Save button",
    "title_input":     "Title field",
    "company_input":   "Company field",
    "currently_here":  "Currently work here checkbox",
    "start_month":     "Start month dropdown",
    "start_year":      "Start year dropdown",
    "end_month":       "End month dropdown",
    "end_year":        "End year dropdown",
    "city_input":      "City field",
    "description":     "Description textarea",
}


def _safe_fill(page, selector_key: str, value: str) -> None:
    label = SELECTOR_LABELS.get(selector_key, selector_key)
    try:
        page.fill(SELECTORS[selector_key], value)
    except Exception:
        raise RuntimeError(f"{label} not found — LinkedIn may have updated their HTML. "
                           f"Check the selector: {SELECTORS[selector_key]!r}")


def _safe_select(page, selector_key: str, value: str) -> None:
    label = SELECTOR_LABELS.get(selector_key, selector_key)
    try:
        page.select_option(SELECTORS[selector_key], value)
    except Exception:
        raise RuntimeError(f"{label} not found — LinkedIn may have updated their HTML. "
                           f"Check the selector: {SELECTORS[selector_key]!r}")


def _safe_click(page, selector_key: str) -> None:
    label = SELECTOR_LABELS.get(selector_key, selector_key)
    try:
        page.click(SELECTORS[selector_key])
    except Exception:
        raise RuntimeError(f"{label} not found — LinkedIn may have updated their HTML. "
                           f"Check the selector: {SELECTORS[selector_key]!r}")


def dry_run(entries: list) -> None:
    """Print a preview of what would be filled without launching the browser."""
    print(f"Dry run — {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} would be filled:\n")
    for i, entry in enumerate(entries, start=1):
        f = entry["fields"]
        start = f["startDate"]["value"]
        end   = f["endDate"]["value"]
        currently = f["currentlyWorkHere"]["value"]
        print(f"  Entry {i}:")
        print(f"    Title    : {f['title']['value']}")
        print(f"    Company  : {f['company']['value']}")
        print(f"    Location : {f['city']['value']}")
        print(f"    Start    : {start['month']} {start['year']}")
        print(f"    End      : {'Present' if currently else f\"{end['month']} {end['year']}\"}")
        print(f"    Desc     : {f['description']['value'][:80]}{'...' if len(f['description']['value']) > 80 else ''}")
        print()


def fill_entry(page, fields: dict, entry_index: int) -> None:
    """Fill one work-experience entry on the page."""
    f = fields

    # Open a new entry panel (skip for first entry if form already has one open)
    if entry_index > 0:
        _safe_click(page, "add_more_button")
        page.wait_for_timeout(500)

    _safe_fill(page, "title_input",   f["title"]["value"])
    _safe_fill(page, "company_input", f["company"]["value"])

    # Checkbox for "currently work here"
    currently = f["currentlyWorkHere"]["value"]
    checkbox = page.locator(SELECTORS["currently_here"])
    if checkbox.count():
        if currently and not checkbox.is_checked():
            checkbox.check()
        elif not currently and checkbox.is_checked():
            checkbox.uncheck()

    start = f["startDate"]["value"]
    end   = f["endDate"]["value"]

    _safe_select(page, "start_month", start["month"])
    _safe_select(page, "start_year",  str(start["year"]))

    if not currently:
        _safe_select(page, "end_month", end["month"])
        _safe_select(page, "end_year",  str(end["year"]))

    _safe_fill(page, "city_input",  f["city"]["value"])
    _safe_fill(page, "description", f["description"]["value"])

    _safe_click(page, "save_button")
    page.wait_for_timeout(800)
    print(f"  Entry {entry_index + 1} saved: {f['title']['value']} @ {f['company']['value']}")


VALID_MONTHS = {
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
}


def validate_form(form: dict, form_path: str) -> None:
    """Validate the filled form JSON before launching the browser."""
    errors = []

    if "form" not in form or "entries" not in form.get("form", {}):
        errors.append("Missing top-level 'form.entries' key.")
        raise ValueError(f"Invalid form file '{form_path}':\n  " + "\n  ".join(errors))

    for i, entry in enumerate(form["form"]["entries"], start=1):
        fields = entry.get("fields", {})
        prefix = f"Entry {i}"

        # Required fields
        for required in ("title", "company", "startDate"):
            field = fields.get(required, {})
            if not field.get("value"):
                errors.append(f"{prefix}: '{required}' is required but empty.")

        # startDate / endDate structure
        for date_field in ("startDate", "endDate"):
            date_val = fields.get(date_field, {}).get("value", {})
            if not isinstance(date_val, dict):
                errors.append(f"{prefix}: '{date_field}.value' must be an object with 'month' and 'year'.")
                continue
            month = date_val.get("month", "")
            year  = date_val.get("year", "")
            if month and month not in VALID_MONTHS:
                errors.append(f"{prefix}: '{date_field}.month' is '{month}', expected a full month name (e.g. 'January').")
            if year and not str(year).isdigit():
                errors.append(f"{prefix}: '{date_field}.year' must be a number, got '{year}'.")

        # Description length
        desc = fields.get("description", {}).get("value", "")
        if len(desc) > 2000:
            errors.append(f"{prefix}: 'description' exceeds 2000 characters ({len(desc)}).")

    if errors:
        raise ValueError(f"Validation failed for '{form_path}':\n  " + "\n  ".join(errors))


def automate(form_path: str, url: str, headless: bool, is_dry_run: bool = False) -> None:
    with open(form_path) as f:
        form = json.load(f)

    validate_form(form, form_path)

    entries = form["form"]["entries"]
    print(f"Loaded {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} from '{form_path}'.")

    if is_dry_run:
        dry_run(entries)
        return

    sync_playwright, PWTimeoutError = _import_playwright()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        print(f"Navigating to: {url}")
        page.goto(url, wait_until="domcontentloaded")

        for i, entry in enumerate(entries):
            try:
                fill_entry(page, entry["fields"], i)
            except PWTimeoutError as e:
                print(f"  Timeout on entry {i + 1}: {e}", file=sys.stderr)
            except Exception as e:
                print(f"  Error on entry {i + 1}: {e}", file=sys.stderr)

        print("All entries processed. Browser will stay open for 5 seconds.")
        page.wait_for_timeout(5000)
        browser.close()


def main():
    parser = argparse.ArgumentParser(description="Automate form filling with Playwright.")
    parser.add_argument("--form",     default="work_experience_form.json", help="Path to filled form JSON (default: work_experience_form.json)")
    parser.add_argument("--url",      required=True,              help="URL of the job-application page")
    parser.add_argument("--headless", action="store_true",        help="Run browser in headless mode (no UI)")
    args = parser.parse_args()

    try:
        automate(args.form, args.url, args.headless)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
