"""Regression tests for apply.py — no network, no gh binary required.

Run with:  python3 -m pytest tests/   (or: python3 tests/test_apply.py)
"""

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import apply  # noqa: E402


def fake_run(responses):
    """Build a subprocess.run stand-in driven by a {endpoint-substring: payload} map."""
    def _run(command, input=None, capture_output=True, text=True):
        endpoint = command[2] if len(command) > 2 else ""
        class Result:
            returncode = 0
            stdout = json.dumps(responses.get(endpoint, []))
            stderr = ""
        return Result()
    return _run


class TestDryRunReadsAndWrites(unittest.TestCase):
    def test_write_is_simulated(self):
        with mock.patch.object(apply.subprocess, "run") as run:
            result = apply.gh("-X", "PUT", "repos/o/r/vulnerability-alerts", dry_run=True)
        run.assert_not_called()
        self.assertEqual(result, {})

    def test_post_is_simulated(self):
        with mock.patch.object(apply.subprocess, "run") as run:
            result = apply.gh("repos/o/r/rulesets", body={"name": "x"}, dry_run=True)
        run.assert_not_called()  # default method is POST
        self.assertEqual(result, {})

    def test_read_executes_even_in_dry_run(self):
        responses = {"repos/o/r/rulesets?includes_parents=false": [{"id": 1, "name": "protect-main"}]}
        with mock.patch.object(apply.subprocess, "run", fake_run(responses)):
            result = apply.gh("repos/o/r/rulesets?includes_parents=false", dry_run=True)
        self.assertEqual(result, [{"id": 1, "name": "protect-main"}])

    def test_delete_and_patch_are_writes(self):
        for method in ("DELETE", "PATCH"):
            with mock.patch.object(apply.subprocess, "run") as run:
                apply.gh("-X", method, "repos/o/r/x", dry_run=True)
            run.assert_not_called()


class TestUpsertRuleset(unittest.TestCase):
    BODY = {"name": "protect-main", "rules": [{"type": "branch_name_pattern"}]}

    def test_existing_ruleset_previews_update_not_create(self):
        responses = {
            "repos/o/r/rulesets?includes_parents=false": [{"id": 7, "name": "protect-main"}],
            "repos/o/r/rulesets/7": {"rules": [{"type": "required_status_checks",
                                                "parameters": {"required_status_checks":
                                                               [{"context": "real-check"}]}}]},
        }
        with mock.patch.object(apply.subprocess, "run", fake_run(responses)), \
             mock.patch("builtins.print") as out:
            printed = []
            out.side_effect = lambda *a, **k: printed.append(" ".join(str(x) for x in a))
            apply.upsert_ruleset("o/r", dict(self.BODY), dry=True, keep_checks=True)
        joined = "\n".join(printed)
        self.assertIn("(updated)", joined)          # honest preview: update, not create
        self.assertIn("would keep 1 existing", joined)
        self.assertIn("PUT", joined)

    def test_missing_ruleset_previews_create(self):
        responses = {"repos/o/r/rulesets?includes_parents=false": []}
        with mock.patch.object(apply.subprocess, "run", fake_run(responses)), \
             mock.patch("builtins.print") as out:
            printed = []
            out.side_effect = lambda *a, **k: printed.append(" ".join(str(x) for x in a))
            apply.upsert_ruleset("o/r", dict(self.BODY), dry=True, keep_checks=True)
        joined = "\n".join(printed)
        self.assertIn("POST repos/o/r/rulesets", joined)

    def test_real_update_keeps_existing_checks(self):
        body = json.loads(json.dumps(self.BODY))  # deep copy
        responses = {
            "repos/o/r/rulesets?includes_parents=false": [{"id": 7, "name": "protect-main"}],
            "repos/o/r/rulesets/7": {"rules": [{"type": "required_status_checks",
                                                "parameters": {"required_status_checks":
                                                               [{"context": "real-check"}]}}]},
        }
        with mock.patch.object(apply.subprocess, "run", fake_run(responses)):
            apply.upsert_ruleset("o/r", body, dry=False, keep_checks=True)
        self.assertEqual(len(body["rules"]), 2)  # own rule + kept status checks
        self.assertEqual(body["rules"][1]["type"], "required_status_checks")

    def test_tag_ruleset_does_not_keep_manual_rules(self):
        # Documents the current ownership policy (Policy A for tags):
        # without keep_checks, existing rules are NOT merged into the body.
        body = json.loads(json.dumps(self.BODY))
        responses = {
            "repos/o/r/rulesets?includes_parents=false": [{"id": 9, "name": "protect-main"}],
        }
        with mock.patch.object(apply.subprocess, "run", fake_run(responses)):
            apply.upsert_ruleset("o/r", body, dry=False, keep_checks=False)
        self.assertEqual(len(body["rules"]), 1)


class TestWantedScope(unittest.TestCase):
    def test_scopes(self):
        self.assertTrue(apply.wanted("all", True))
        self.assertTrue(apply.wanted("all", False))
        self.assertTrue(apply.wanted("public", True))
        self.assertFalse(apply.wanted("public", False))
        self.assertFalse(apply.wanted("private", True))
        self.assertTrue(apply.wanted("private", False))
        self.assertFalse(apply.wanted("none", True))
        self.assertFalse(apply.wanted("none", False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
