"""
Unit tests for merge.py and automate.py (no browser required).
Run: python -m pytest test_app.py -v
"""

import copy
import json
import os
import pytest
import tempfile

from merge import merge, FIELD_MAP
from automate import validate_form, dry_run, VALID_MONTHS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SCHEMA = {
    "form": {
        "entries": [
            {
                "id": 1,
                "fields": {
                    "title":             {"value": ""},
                    "company":           {"value": ""},
                    "currentlyWorkHere": {"value": False},
                    "startDate":         {"value": {"month": "", "year": ""}},
                    "endDate":           {"value": {"month": "", "year": ""}},
                    "city":              {"value": ""},
                    "description":       {"value": ""},
                },
            }
        ]
    }
}

CANDIDATE = {
    "candidate": "Jane Doe",
    "entries": [
        {
            "id": 1,
            "title": "Engineer",
            "company": "Acme",
            "currentlyWorkHere": False,
            "startMonth": "January",
            "startYear": 2022,
            "endMonth": "June",
            "endYear": 2023,
            "city": "Lagos, Nigeria",
            "description": "Did stuff.",
        }
    ],
}


def write_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f)


# ---------------------------------------------------------------------------
# merge.py tests
# ---------------------------------------------------------------------------

class TestMerge:
    def test_single_entry_filled_correctly(self, tmp_path):
        schema_path    = str(tmp_path / "schema.json")
        candidate_path = str(tmp_path / "candidate.json")
        output_path    = str(tmp_path / "out.json")
        write_json(SCHEMA, schema_path)
        write_json(CANDIDATE, candidate_path)

        merge(schema_path, candidate_path, output_path)

        with open(output_path) as f:
            result = json.load(f)

        entry = result["form"]["entries"][0]
        fields = entry["fields"]
        assert fields["title"]["value"] == "Engineer"
        assert fields["company"]["value"] == "Acme"
        assert fields["city"]["value"] == "Lagos, Nigeria"
        assert fields["startDate"]["value"] == {"month": "January", "year": 2022}
        assert fields["endDate"]["value"] == {"month": "June", "year": 2023}
        assert fields["description"]["value"] == "Did stuff."

    def test_multiple_entries_cloned(self, tmp_path):
        candidate = copy.deepcopy(CANDIDATE)
        candidate["entries"].append({
            "id": 2,
            "title": "Senior Engineer",
            "company": "BigCo",
            "currentlyWorkHere": True,
            "startMonth": "March",
            "startYear": 2020,
            "endMonth": "",
            "endYear": "",
            "city": "Berlin, Germany",
            "description": "Led team.",
        })
        schema_path    = str(tmp_path / "schema.json")
        candidate_path = str(tmp_path / "candidate.json")
        output_path    = str(tmp_path / "out.json")
        write_json(SCHEMA, schema_path)
        write_json(candidate, candidate_path)

        merge(schema_path, candidate_path, output_path)

        with open(output_path) as f:
            result = json.load(f)

        assert len(result["form"]["entries"]) == 2
        assert result["form"]["entries"][1]["fields"]["title"]["value"] == "Senior Engineer"

    def test_missing_schema_raises(self, tmp_path):
        candidate_path = str(tmp_path / "candidate.json")
        write_json(CANDIDATE, candidate_path)
        with pytest.raises(FileNotFoundError):
            merge("nonexistent.json", candidate_path, str(tmp_path / "out.json"))

    def test_missing_candidate_raises(self, tmp_path):
        schema_path = str(tmp_path / "schema.json")
        write_json(SCHEMA, schema_path)
        with pytest.raises(FileNotFoundError):
            merge(schema_path, "nonexistent.json", str(tmp_path / "out.json"))

    def test_no_candidate_data_for_entry_skips(self, tmp_path, capsys):
        candidate = copy.deepcopy(CANDIDATE)
        candidate["entries"] = []  # no entries
        schema_path    = str(tmp_path / "schema.json")
        candidate_path = str(tmp_path / "candidate.json")
        output_path    = str(tmp_path / "out.json")
        write_json(SCHEMA, schema_path)
        write_json(candidate, candidate_path)

        merge(schema_path, candidate_path, output_path)
        captured = capsys.readouterr()
        assert "skipping" in captured.out


# ---------------------------------------------------------------------------
# automate.py — validate_form tests
# ---------------------------------------------------------------------------

def _make_form(overrides=None):
    """Build a minimal valid filled-form dict, with optional field overrides."""
    form = {
        "form": {
            "entries": [
                {
                    "id": 1,
                    "fields": {
                        "title":             {"value": "Engineer"},
                        "company":           {"value": "Acme"},
                        "currentlyWorkHere": {"value": False},
                        "startDate":         {"value": {"month": "January", "year": 2022}},
                        "endDate":           {"value": {"month": "June",    "year": 2023}},
                        "city":              {"value": "Lagos"},
                        "description":       {"value": "Did stuff."},
                    },
                }
            ]
        }
    }
    if overrides:
        for key, value in overrides.items():
            form["form"]["entries"][0]["fields"][key] = value
    return form


class TestValidateForm:
    def test_valid_form_passes(self):
        validate_form(_make_form(), "test.json")  # should not raise

    def test_missing_form_key_raises(self):
        with pytest.raises(ValueError, match="Missing top-level"):
            validate_form({}, "test.json")

    def test_empty_title_raises(self):
        form = _make_form({"title": {"value": ""}})
        with pytest.raises(ValueError, match="title"):
            validate_form(form, "test.json")

    def test_empty_company_raises(self):
        form = _make_form({"company": {"value": ""}})
        with pytest.raises(ValueError, match="company"):
            validate_form(form, "test.json")

    def test_invalid_month_raises(self):
        form = _make_form({"startDate": {"value": {"month": "Octember", "year": 2022}}})
        with pytest.raises(ValueError, match="Octember"):
            validate_form(form, "test.json")

    def test_all_valid_months_pass(self):
        for month in VALID_MONTHS:
            form = _make_form({"startDate": {"value": {"month": month, "year": 2022}}})
            validate_form(form, "test.json")  # should not raise

    def test_non_numeric_year_raises(self):
        form = _make_form({"startDate": {"value": {"month": "January", "year": "twenty-twenty"}}})
        with pytest.raises(ValueError, match="year"):
            validate_form(form, "test.json")

    def test_description_over_2000_chars_raises(self):
        form = _make_form({"description": {"value": "x" * 2001}})
        with pytest.raises(ValueError, match="2000"):
            validate_form(form, "test.json")

    def test_description_exactly_2000_chars_passes(self):
        form = _make_form({"description": {"value": "x" * 2000}})
        validate_form(form, "test.json")  # should not raise


# ---------------------------------------------------------------------------
# automate.py — dry_run tests
# ---------------------------------------------------------------------------

class TestDryRun:
    def _entries(self, currently=False):
        return [
            {
                "fields": {
                    "title":             {"value": "Engineer"},
                    "company":           {"value": "Acme"},
                    "currentlyWorkHere": {"value": currently},
                    "startDate":         {"value": {"month": "January", "year": 2022}},
                    "endDate":           {"value": {"month": "June",    "year": 2023}},
                    "city":              {"value": "Lagos"},
                    "description":       {"value": "Short desc."},
                }
            }
        ]

    def test_dry_run_prints_title_and_company(self, capsys):
        dry_run(self._entries())
        out = capsys.readouterr().out
        assert "Engineer" in out
        assert "Acme" in out

    def test_dry_run_shows_present_when_currently_working(self, capsys):
        dry_run(self._entries(currently=True))
        out = capsys.readouterr().out
        assert "Present" in out

    def test_dry_run_truncates_long_description(self, capsys):
        entries = self._entries()
        entries[0]["fields"]["description"]["value"] = "A" * 200
        dry_run(entries)
        out = capsys.readouterr().out
        assert "..." in out
