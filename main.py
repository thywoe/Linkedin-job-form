"""
main.py — Drives the browser to fill the LinkedIn work-experience form
           from work_experience_form.json (already a fully-populated filled form).

Usage:
    python main.py --url https://www.linkedin.com/jobs/...
    python main.py --url https://... --form work_experience_form.json
    python main.py --url https://... --headless
    python main.py --url https://... --dry-run
"""

import argparse
import sys
from automate import automate


def main():
    parser = argparse.ArgumentParser(
        description="Fill a LinkedIn work-experience form using Playwright.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--url",      required=True,                       help="URL of the job-application page")
    parser.add_argument("--form",     default="work_experience_form.json", help="Path to form JSON (default: work_experience_form.json)")
    parser.add_argument("--headless", action="store_true",                 help="Run browser headlessly (no UI)")
    parser.add_argument("--dry-run",  action="store_true",                 help="Preview entries without launching the browser")

    args = parser.parse_args()

    try:
        automate(args.form, args.url, args.headless, is_dry_run=args.dry_run)
    except SystemExit:
        raise
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
