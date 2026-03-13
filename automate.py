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


def fill_entry(page, fields: dict, entry_index: int) -> None:
    """Fill one work-experience entry on the page."""
    f = fields

    # Open a new entry panel (skip for first entry if form already has one open)
    if entry_index > 0:
        page.click(SELECTORS["add_more_button"])
        page.wait_for_timeout(500)

    page.fill(SELECTORS["title_input"],   f["title"]["value"])
    page.fill(SELECTORS["company_input"], f["company"]["value"])

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

    page.select_option(SELECTORS["start_month"], start["month"])
    page.select_option(SELECTORS["start_year"],  str(start["year"]))

    if not currently:
        page.select_option(SELECTORS["end_month"], end["month"])
        page.select_option(SELECTORS["end_year"],  str(end["year"]))

    page.fill(SELECTORS["city_input"],  f["city"]["value"])
    page.fill(SELECTORS["description"], f["description"]["value"])

    page.click(SELECTORS["save_button"])
    page.wait_for_timeout(800)
    print(f"  Entry {entry_index + 1} saved: {f['title']['value']} @ {f['company']['value']}")


def automate(form_path: str, url: str, headless: bool) -> None:
    with open(form_path) as f:
        form = json.load(f)

    entries = form["form"]["entries"]
    print(f"Loaded {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} from '{form_path}'.")

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
