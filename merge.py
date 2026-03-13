"""
merge.py — Injects candidate data into the form schema to produce a filled form.

Usage:
    python merge.py [--schema schema.json] [--candidate candidate_data.json] [--output filled_form.json]
"""

import json
import copy
import argparse
import sys


FIELD_MAP = {
    "title":             lambda e: e["title"],
    "company":           lambda e: e["company"],
    "currentlyWorkHere": lambda e: e["currentlyWorkHere"],
    "startDate":         lambda e: {"month": e["startMonth"], "year": e["startYear"]},
    "endDate":           lambda e: {"month": e["endMonth"],   "year": e["endYear"]},
    "city":              lambda e: e["city"],
    "description":       lambda e: e["description"],
}


def merge(schema_path: str, candidate_path: str, output_path: str) -> None:
    with open(schema_path) as f:
        schema = json.load(f)
    with open(candidate_path) as f:
        candidate = json.load(f)

    filled_form = copy.deepcopy(schema)

    # Build a lookup from entry id → candidate entry data
    candidate_lookup = {entry["id"]: entry for entry in candidate["entries"]}

    for entry in filled_form["form"]["entries"]:
        entry_id = entry["id"]
        if entry_id not in candidate_lookup:
            print(f"  Warning: no candidate data for entry id={entry_id}, skipping.")
            continue

        entry_data = candidate_lookup[entry_id]
        fields = entry["fields"]

        for field_name, extractor in FIELD_MAP.items():
            if field_name in fields:
                try:
                    fields[field_name]["value"] = extractor(entry_data)
                except KeyError as e:
                    print(f"  Warning: missing key {e} in candidate entry id={entry_id}.")

    # The schema only has one template entry; clone it for every extra candidate entry
    template_entry = copy.deepcopy(schema["form"]["entries"][0])
    for entry_data in candidate["entries"]:
        entry_id = entry_data["id"]
        # Skip id=1 — already handled above from the schema template
        if entry_id == filled_form["form"]["entries"][0]["id"]:
            continue

        new_entry = copy.deepcopy(template_entry)
        new_entry["id"] = entry_id
        fields = new_entry["fields"]

        for field_name, extractor in FIELD_MAP.items():
            if field_name in fields:
                try:
                    fields[field_name]["value"] = extractor(entry_data)
                except KeyError as e:
                    print(f"  Warning: missing key {e} in candidate entry id={entry_id}.")

        filled_form["form"]["entries"].append(new_entry)

    with open(output_path, "w") as f:
        json.dump(filled_form, f, indent=2)

    candidate_name = candidate.get("candidate", "unknown")
    entry_count = len(filled_form["form"]["entries"])
    print(f"Form filled for '{candidate_name}' — {entry_count} entr{'y' if entry_count == 1 else 'ies'} written to '{output_path}'.")


def main():
    parser = argparse.ArgumentParser(description="Merge candidate data into a form schema.")
    parser.add_argument("--schema",    default="schema.json",         help="Path to schema JSON (default: schema.json)")
    parser.add_argument("--candidate", default="candidate_data.json", help="Path to candidate data JSON (default: candidate_data.json)")
    parser.add_argument("--output",    default="filled_form.json",    help="Path for output JSON (default: filled_form.json)")
    args = parser.parse_args()

    try:
        merge(args.schema, args.candidate, args.output)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
