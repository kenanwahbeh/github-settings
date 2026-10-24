"""Regression tests for apply.py — no network, no gh binary required.

Run with:  uv run --with pyyaml python tests/test_apply.py
(or inside any environment that already provides PyYAML: python3 tests/test_apply.py)
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
    def _run(command, input=None, capture_output=True, text=True, timeout=None):
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
            apply.upsert_ruleset("o/r", dict(self.BODY), dry=True, keep_rules=("required_status_checks",))
        joined = "\n".join(printed)
        self.assertIn("(updated)", joined)          # honest preview: update, not create
        self.assertIn("would keep 1 existing", joined)  # keeps... required_status_checks
        self.assertIn("PUT", joined)

    def test_dry_run_preview_payload_contains_retained_checks(self):
        # Issue #10: the printed PUT payload must match what a real run sends,
        # i.e. it includes the retained required_status_checks rule...
        responses = {
            "repos/o/r/rulesets?includes_parents=false": [{"id": 7, "name": "protect-main"}],
            "repos/o/r/rulesets/7": {"rules": [{"type": "required_status_checks",
                                                "parameters": {"required_status_checks":
                                                               [{"context": "real-check"}]}}]},
        }
        body = json.loads(json.dumps(self.BODY))  # deep copy so we can check mutation
        with mock.patch.object(apply.subprocess, "run", fake_run(responses)), \
             mock.patch("builtins.print") as out:
            printed = []
            out.side_effect = lambda *a, **k: printed.append(" ".join(str(x) for x in a))
            apply.upsert_ruleset("o/r", body, dry=True, keep_rules=("required_status_checks",))
        joined = "\n".join(printed)
        payload_line = next(line for line in printed if "would run:" in line and "PUT" in line)
        payload = json.loads(payload_line[payload_line.index("{"):payload_line.rindex("}") + 1])
        self.assertEqual(len(payload["rules"]), 2)  # own rule + retained status checks
        self.assertEqual(payload["rules"][1]["type"], "required_status_checks")
        self.assertIn("real-check", joined)
        # ...while the caller's body is NOT mutated by the preview path.
        self.assertEqual(len(body["rules"]), 1)

    def test_missing_ruleset_previews_create(self):
        responses = {"repos/o/r/rulesets?includes_parents=false": []}
        with mock.patch.object(apply.subprocess, "run", fake_run(responses)), \
             mock.patch("builtins.print") as out:
            printed = []
            out.side_effect = lambda *a, **k: printed.append(" ".join(str(x) for x in a))
            apply.upsert_ruleset("o/r", dict(self.BODY), dry=True, keep_rules=("required_status_checks",))
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
            apply.upsert_ruleset("o/r", body, dry=False, keep_rules=("required_status_checks",))
        self.assertEqual(len(body["rules"]), 2)  # own rule + kept status checks
        self.assertEqual(body["rules"][1]["type"], "required_status_checks")

    def test_tag_ruleset_does_not_keep_manual_rules(self):
        # Documents the current ownership policy (Policy A for tags):
        # with an empty keep_rules list (settings.yml tag_ruleset.keep_existing_rules: []),
        # existing rules are NOT merged into the body.
        body = json.loads(json.dumps(self.BODY))
        responses = {
            "repos/o/r/rulesets?includes_parents=false": [{"id": 9, "name": "protect-main"}],
        }
        with mock.patch.object(apply.subprocess, "run", fake_run(responses)):
            apply.upsert_ruleset("o/r", body, dry=False, keep_rules=())
        self.assertEqual(len(body["rules"]), 1)

    def test_keeps_any_exempted_rule_type(self):
        # The policy is type-driven: any rule type listed in
        # settings.yml keep_existing_rules survives re-apply, not only checks.
        body = json.loads(json.dumps(self.BODY))
        responses = {
            "repos/o/r/rulesets?includes_parents=false": [{"id": 7, "name": "protect-main"}],
            "repos/o/r/rulesets/7": {"rules": [
                {"type": "commit_message_pattern", "parameters": {"operator": "starts_with"}}]},
        }
        with mock.patch.object(apply.subprocess, "run", fake_run(responses)):
            apply.upsert_ruleset("o/r", body, dry=False, keep_rules=("commit_message_pattern",))
        self.assertEqual(len(body["rules"]), 2)
        self.assertEqual(body["rules"][1]["type"], "commit_message_pattern")

    def test_non_exempted_rules_are_dropped_on_update(self):
        # Policy A contract: a manual rule whose type is NOT exempted is
        # silently replaced by the central settings — documented, tested.
        responses = {
            "repos/o/r/rulesets?includes_parents=false": [{"id": 7, "name": "protect-main"}],
            "repos/o/r/rulesets/7": {"rules": [
                {"type": "required_status_checks"}, {"type": "pull_request"}]},
        }
        body = json.loads(json.dumps(self.BODY))
        with mock.patch.object(apply.subprocess, "run", fake_run(responses)), \
             mock.patch("builtins.print") as out:
            printed = []
            out.side_effect = lambda *a, **k: printed.append(" ".join(str(x) for x in a))
            apply.upsert_ruleset("o/r", body, dry=True, keep_rules=("required_status_checks",))
        text = next(line for line in printed if "would run:" in line and "PUT" in line)
        payload = json.loads(text[text.index("{"): text.rindex("}") + 1])
        types = [r["type"] for r in payload["rules"]]
        self.assertIn("required_status_checks", types)   # exempted: kept
        self.assertNotIn("pull_request", types)          # not exempted: dropped


class TestBuildBranchRuleset(unittest.TestCase):
    def setUp(self):
        self.settings = apply.yaml.safe_load(
            (Path(__file__).resolve().parent.parent / "settings.yml").read_text()
        )["ruleset"]

    def test_baseline_includes_signed_commits_and_pull_requests(self):
        body = apply.build_branch_ruleset(self.settings)
        types = [rule["type"] for rule in body["rules"]]
        self.assertIn("required_signatures", types)
        self.assertIn("pull_request", types)
        self.assertIn("deletion", types)
        self.assertIn("non_fast_forward", types)
        self.assertNotIn("required_status_checks", types)

    def test_explicit_checks_are_all_added_to_the_ruleset(self):
        checks = ["gitleaks", "semgrep", "Regression and consistency checks"]
        body = apply.build_branch_ruleset(self.settings, checks)
        check_rules = [rule for rule in body["rules"] if rule["type"] == "required_status_checks"]
        self.assertEqual(len(check_rules), 1)
        parameters = check_rules[0]["parameters"]
        self.assertEqual(
            parameters["required_status_checks"],
            [{"context": name} for name in checks],
        )
        self.assertIn("required_signatures", [rule["type"] for rule in body["rules"]])

    def test_explicit_checks_replace_the_check_list_not_other_rules(self):
        body = apply.build_branch_ruleset(self.settings, ["actual-ci-check"])
        self.assertEqual(
            [rule["type"] for rule in body["rules"]].count("required_status_checks"),
            1,
        )
        self.assertNotIn(
            "old-check",
            json.dumps(body),
        )
        self.assertIn("required_signatures", [rule["type"] for rule in body["rules"]])


class TestWriteDetection(unittest.TestCase):
    """is_write_call() is the safety gate of --dry-run: a missed write would
    execute against GitHub during a preview. Cases mirror real gh api usage."""

    def test_get_without_body_is_read(self):
        self.assertFalse(apply.is_write_call(("repos/o/r",), None))

    def test_explicit_get_with_body_stays_read(self):
        # An explicit -X GET overrides the body-default-to-POST rule.
        self.assertFalse(apply.is_write_call(("-X", "GET", "repos/o/r/x"), {"q": 1}))

    def test_body_without_x_is_post_write(self):
        self.assertTrue(apply.is_write_call(("repos/o/r/rulesets",), {"name": "x"}))

    def test_lowercase_method_detected(self):
        self.assertTrue(apply.is_write_call(("-X", "put", "repos/o/r/x"), None))

    def test_dangling_x_is_treated_as_write_for_safety(self):
        self.assertTrue(apply.is_write_call(("-X",), None))

    def test_only_known_safe_methods_execute_in_dry_run(self):
        for method in ("GET", "HEAD", "OPTIONS", "get", "options"):
            self.assertFalse(apply.is_write_call(("-X", method, "repos/o/r/x"), None))

    def test_mutating_and_unknown_methods_are_writes(self):
        for method in ("DELETE", "PATCH", "PUT", "POST", "COPY", "MERGE", "TRACE"):
            self.assertTrue(apply.is_write_call(("-X", method, "repos/o/r/x"), None))

    def test_body_with_explicit_safe_method_is_read(self):
        self.assertFalse(apply.is_write_call(("-X", "GET", "repos/o/r/x"), {"q": 1}))


class TestRepoSlugValidation(unittest.TestCase):
    def test_valid_repository_slugs(self):
        for value in ("owner/repo", "owner-1/repo_name", "owner/repo.name", "A/a"):
            self.assertTrue(apply.is_valid_repo_slug(value), value)

    def test_invalid_repository_slugs_are_rejected(self):
        for value in ("", "owner", "owner/repo/extra", "/repo", "owner/",
                      "../repo", "owner/..", "owner/repo?x=1", "owner/repo#x",
                      "owner/repo\\n", "owner name/repo", "-owner/repo",
                      "owner/repo\\x"):
            self.assertFalse(apply.is_valid_repo_slug(value), repr(value))

    def test_github_slug_length_limits(self):
        self.assertFalse(apply.is_valid_repo_slug("a" * 40 + "/repo"))
        self.assertFalse(apply.is_valid_repo_slug("owner/" + "a" * 101))


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


class TestApiErrors(unittest.TestCase):
    def test_timeout_is_bounded_and_write_outcome_is_explicit(self):
        with mock.patch.object(apply.subprocess, "run", side_effect=
                               apply.subprocess.TimeoutExpired("gh", 60)) as run:
            with self.assertRaisesRegex(RuntimeError, "write outcome is unknown"):
                apply.gh("-X", "PUT", "repos/o/r/x")
        self.assertEqual(run.call_args.kwargs["timeout"], 60)

    def test_missing_binary_is_reported(self):
        with mock.patch.object(apply.subprocess, "run", side_effect=FileNotFoundError("gh")):
            with self.assertRaisesRegex(RuntimeError, "Could not run gh api"):
                apply.gh("repos/o/r")

    def test_api_failure_preserves_diagnostic(self):
        result = mock.Mock(returncode=1, stderr="HTTP 403: denied", stdout="")
        with mock.patch.object(apply.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "HTTP 403: denied"):
                apply.gh("-X", "PUT", "repos/o/r/x")

    def test_invalid_json_is_reported(self):
        result = mock.Mock(returncode=0, stdout="not json")
        with mock.patch.object(apply.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "invalid JSON"):
                apply.gh("repos/o/r")


class TestPreservedCheckPolicy(unittest.TestCase):
    def test_replacing_names_keeps_policy_and_matching_source_in_both_modes(self):
        for dry in (True, False):
            with self.subTest(dry=dry):
                body = {"name": "main", "rules": [{"type": "required_status_checks", "parameters": {
                    "strict_required_status_checks_policy": False,
                    "do_not_enforce_on_create": False,
                    "required_status_checks": [{"context": "kept"}, {"context": "new"}],
                }}]}
                original = json.loads(json.dumps(body))
                current = {"rules": [{"type": "required_status_checks", "parameters": {
                    "strict_required_status_checks_policy": True,
                    "do_not_enforce_on_create": True,
                    "required_status_checks": [{"context": "kept", "integration_id": 15368},
                                               {"context": "removed", "integration_id": 42}],
                }}]}
                with mock.patch.object(apply, "gh", side_effect=[
                        [{"id": 7, "name": "main"}], current, {}]) as gh:
                    self.assertTrue(apply.upsert_ruleset("o/r", body, dry))
                payload = gh.call_args.kwargs["body"]
                parameters = payload["rules"][0]["parameters"]
                self.assertTrue(parameters["strict_required_status_checks_policy"])
                self.assertTrue(parameters["do_not_enforce_on_create"])
                self.assertEqual(parameters["required_status_checks"], [
                    {"context": "kept", "integration_id": 15368}, {"context": "new"}])
                self.assertEqual(gh.call_args.kwargs["dry_run"], dry)
                if dry:
                    self.assertEqual(body, original)

    def test_failed_ruleset_read_prevents_write(self):
        for responses in ([RuntimeError("list failed")],
                          [[{"id": 7, "name": "main"}], RuntimeError("detail failed")]):
            with mock.patch.object(apply, "gh", side_effect=responses) as gh:
                self.assertFalse(apply.upsert_ruleset(
                    "o/r", {"name": "main", "rules": []}, False,
                    keep_rules=("required_status_checks",)))
            self.assertTrue(all("-X" not in call.args for call in gh.call_args_list))


class TestMainFlow(unittest.TestCase):
    def run_main(self, responder, *args):
        with mock.patch.object(sys, "argv", ["apply.py", "o/r", *args]), \
             mock.patch.object(apply, "gh", side_effect=responder) as gh, \
             mock.patch("builtins.print") as output, \
             self.assertRaises(SystemExit) as stopped:
            apply.main()
        return stopped.exception.code, gh.call_args_list, output

    @staticmethod
    def responder(private=False, fail_rules=False):
        def respond(*args, **kwargs):
            if args == ("repos/o/r",):
                return {"private": private}
            if args[0].endswith("rulesets?includes_parents=false"):
                if fail_rules:
                    raise RuntimeError("ruleset read denied")
                return []
            if kwargs.get("body", {}).get("security_and_analysis"):
                return kwargs["body"]
            return {}
        return respond

    def test_public_and_private_success_paths(self):
        for private in (True, False):
            code, calls, _ = self.run_main(self.responder(private))
            self.assertEqual(code, 0)
            endpoints = [call.args[-1] for call in calls]
            self.assertEqual("repos/o/r/code-scanning/default-setup" in endpoints, not private)
            self.assertEqual("repos/o/r/private-vulnerability-reporting" in endpoints, not private)
            self.assertEqual("repos/o/r/actions/permissions/fork-pr-contributor-approval" in endpoints,
                             not private)
            writes = [call for call in calls if call.args[:2] == ("-X", "POST")]
            self.assertEqual([call.kwargs["body"]["name"] for call in writes], ["main", "tags"])

    def test_read_failure_after_changes_exits_nonzero_and_summarizes(self):
        code, calls, output = self.run_main(self.responder(fail_rules=True))
        self.assertEqual(code, 1)
        self.assertTrue(any(call.args[:2] == ("-X", "PATCH") for call in calls))
        self.assertFalse(any(call.args[:2] == ("-X", "POST") for call in calls))
        self.assertTrue(any("not rolled back" in str(call) for call in output.call_args_list))

    def test_write_failure_is_reported_and_later_steps_continue(self):
        respond = self.responder()

        def fail_first_write(*args, **kwargs):
            if args == ("-X", "PUT", "repos/o/r/vulnerability-alerts"):
                raise RuntimeError("HTTP 403: denied")
            return respond(*args, **kwargs)

        code, calls, output = self.run_main(fail_first_write)
        self.assertEqual(code, 1)
        self.assertTrue(any(call.kwargs.get("body", {}).get("name") == "tags" for call in calls))
        self.assertTrue(any("HTTP 403: denied" in str(call) for call in output.call_args_list))
        self.assertTrue(any("not rolled back" in str(call) for call in output.call_args_list))

    def test_initial_read_failure_stops_before_writes(self):
        code, calls, _ = self.run_main(RuntimeError("connection failed"))
        self.assertIn("No settings were applied", code)
        self.assertEqual(len(calls), 1)

    def test_dry_run_cli_never_executes_write_subprocesses(self):
        def respond(command, **kwargs):
            self.assertNotIn("-X", command)
            payload = {"private": False} if command[-1] == "repos/o/r" else []
            return mock.Mock(returncode=0, stdout=json.dumps(payload))
        with mock.patch.object(sys, "argv", ["apply.py", "o/r", "--dry-run", "--check", "real"]), \
             mock.patch.object(apply.subprocess, "run", side_effect=respond) as run, \
             mock.patch("builtins.print"), self.assertRaises(SystemExit) as stopped:
            apply.main()
        self.assertEqual(stopped.exception.code, 0)
        self.assertEqual(run.call_count, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
