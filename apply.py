# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Apply settings.yml to one repository with the gh CLI.

    uv run apply.py owner/repo [--check test --check lint] [--dry-run]
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


API_TIMEOUT_SECONDS = 60
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
REPO_SLUG_RE = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")


def is_valid_repo_slug(value):
    """Accept only a plain owner/repository path before interpolating it into API routes."""
    if not isinstance(value, str) or not REPO_SLUG_RE.fullmatch(value):
        return False
    owner, name = value.split("/", 1)
    return not owner.startswith("-") and not owner.endswith("-") and name not in {".", ".."}


def is_write_call(args, body):
    """Conservatively identify writes before executing a gh api call in dry-run.

    `gh api` defaults to GET; a body without an explicit method defaults to
    POST. Only known safe HTTP methods are allowed to execute during a preview.
    Unknown methods and a malformed dangling -X are treated as writes so a new
    or malformed verb cannot accidentally mutate GitHub during --dry-run.
    """
    try:
        idx = list(args).index("-X")
    except ValueError:
        return body is not None
    if idx + 1 >= len(args):
        return True
    return str(args[idx + 1]).upper() not in SAFE_METHODS


def gh(*args, body=None, dry_run=False):
    command = ["gh", "api", *args]
    # --dry-run previews every write but still performs reads (GET), so a
    # preview like upsert_ruleset reflects the repository's real current state.
    # Requires network + authenticated gh + read access; unit tests mock this.
    is_write = is_write_call(args, body)
    if dry_run and is_write:
        print("  would run:", " ".join(command), json.dumps(body) if body else "")
        return {}
    try:
        result = subprocess.run(
            command + (["--input", "-"] if body is not None else []),
            input=json.dumps(body) if body is not None else None,
            capture_output=True,
            text=True,
            timeout=API_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        detail = " The write outcome is unknown; inspect GitHub before retrying." if is_write else ""
        raise RuntimeError(f"gh api timed out after {API_TIMEOUT_SECONDS}s.{detail}") from error
    except OSError as error:
        raise RuntimeError(f"Could not run gh api: {error}") from error
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError as error:
        raise RuntimeError("gh api returned invalid JSON; inspect GitHub before retrying writes.") from error


def step(name, action):
    try:
        action()
        print(f"✓ {name}")
    except RuntimeError as error:
        print(f"✗ {name}: {error}")
        return False
    return True


def wanted(mode, public):
    """settings.yml gives a scope: all, public, private or none."""
    return mode == "all" or (mode == "public" and public) or (mode == "private" and not public)


def build_branch_ruleset(rules, checks=()):
    """Build the desired default-branch ruleset from settings and explicit CI checks.

    Passing checks is an explicit replacement policy: callers must provide every
    check that should block merging. An empty list intentionally omits the
    required_status_checks rule; upsert_ruleset may preserve the live rule only
    when configured to keep that rule type.
    """
    body = {
        "name": rules["name"],
        "target": "branch",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
        "rules": [],
    }
    if rules["block_deletion"]:
        body["rules"].append({"type": "deletion"})
    if rules["block_force_push"]:
        body["rules"].append({"type": "non_fast_forward"})
    if rules["require_signed_commits"]:
        body["rules"].append({"type": "required_signatures"})
    if rules["require_pull_request"]:
        body["rules"].append({"type": "pull_request", "parameters": {
            "allowed_merge_methods": rules["allowed_merge_methods"],
            "dismiss_stale_reviews_on_push": False,
            "require_code_owner_review": False,
            "require_last_push_approval": False,
            "required_approving_review_count": rules["required_approvals"],
            "required_review_thread_resolution": False,
        }})
    if checks:
        body["rules"].append({"type": "required_status_checks", "parameters": {
            "strict_required_status_checks_policy": False,
            "do_not_enforce_on_create": False,
            "required_status_checks": [{"context": name} for name in checks],
        }})
    return body


def upsert_ruleset(repo, body, dry, keep_rules=()):
    """Create the ruleset, or update the one with the same name.

    Ownership policy (documented in settings.yml): settings.yml owns every
    rule except the types named in `keep_rules`. On an update those types are
    read from the live ruleset and appended to the payload, so per-repository
    additions survive re-apply. Explicit check names replace only the list; the
    live check policy and bindings of retained names survive that replacement.
    Other rules return to the central state.
    """
    def action():
        existing = [r for r in gh(f"repos/{repo}/rulesets?includes_parents=false")
                    if r["name"] == body["name"]]
        request_body = json.loads(json.dumps(body)) if dry else body
        check_rule = next((r for r in request_body["rules"]
                           if r["type"] == "required_status_checks"), None)
        if existing and (keep_rules or check_rule is not None):
            current = gh(f"repos/{repo}/rulesets/{existing[0]['id']}")
            # --check replaces names, but retains the live policy and source
            # binding for each retained context. New contexts use the defaults.
            if check_rule is not None:
                previous = next((r for r in current["rules"]
                                 if r["type"] == "required_status_checks"), None)
                if previous is not None:
                    parameters = previous["parameters"]
                    check_rule["parameters"].update({
                        key: value for key, value in parameters.items()
                        if key != "required_status_checks"
                    })
                    bindings = {check["context"]: check["integration_id"]
                                for check in parameters["required_status_checks"]
                                if "integration_id" in check}
                    for check in check_rule["parameters"]["required_status_checks"]:
                        if check["context"] in bindings:
                            check.setdefault("integration_id", bindings[check["context"]])
            kept = [r for r in current["rules"] if r["type"] in keep_rules
                    and not (check_rule is not None and r["type"] == "required_status_checks")]
            if dry and keep_rules:
                print(f"  would keep {len(kept)} existing {'/'.join(keep_rules)} rule(s) on {body['name']}")
            request_body["rules"] += kept
        if existing:
            gh("-X", "PUT", f"repos/{repo}/rulesets/{existing[0]['id']}",
               body=request_body, dry_run=dry)
            print(f"  Ruleset {body['name']} (updated)")
        else:
            gh("-X", "POST", f"repos/{repo}/rulesets", body=request_body, dry_run=dry)

    return step(f"Ruleset {body['name']}", action)


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # the Windows console defaults to a legacy code page
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", help="owner/repo")
    parser.add_argument("--check", action="append", default=[], help="a required CI check")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not is_valid_repo_slug(args.repo):
        parser.error("repo must be a plain owner/repository slug (letters, digits, dots, underscores or hyphens only)")
    if any(not name.strip() or name != name.strip() for name in args.check):
        parser.error("each --check must be non-empty and have no leading/trailing whitespace")
    if len(set(args.check)) != len(args.check):
        parser.error("duplicate --check values are not allowed")
    settings = yaml.safe_load((Path(__file__).parent / "settings.yml").read_text())
    repo, dry = args.repo, args.dry_run

    try:
        info = gh(f"repos/{repo}")
    except RuntimeError as error:
        sys.exit(f"Could not read repository {repo}: {error}. No settings were applied.")
    if info.get("archived"):
        sys.exit(f"{repo} is archived: nothing can be changed.")
    public = not info["private"]
    print(f"{repo} ({'public' if public else 'private'})")
    ok = True

    security = settings["security"]
    if security["dependabot_alerts"]:
        ok &= step("Dependabot alerts", lambda: gh("-X", "PUT", f"repos/{repo}/vulnerability-alerts", dry_run=dry))
    if security["dependabot_security_updates"]:
        ok &= step("Dependabot security updates", lambda: gh("-X", "PUT", f"repos/{repo}/automated-security-fixes", dry_run=dry))

    analysis = {}
    if security["secret_scanning"]:
        analysis["secret_scanning"] = {"status": "enabled"}
    if security["secret_scanning_push_protection"]:
        analysis["secret_scanning_push_protection"] = {"status": "enabled"}

    def secret_scanning():
        result = gh("-X", "PATCH", f"repos/{repo}", body={"security_and_analysis": analysis}, dry_run=dry)
        if dry:
            return
        statuses = {name: (result.get("security_and_analysis") or {}).get(name, {}).get("status")
                    for name in analysis}
        if any(status != "enabled" for status in statuses.values()):
            raise RuntimeError(f"GitHub did not enable it: {statuses}")

    if analysis:
        ok &= step("Secret scanning and push protection", secret_scanning)
    if wanted(security["codeql_default_setup"], public):
        ok &= step("CodeQL default setup", lambda: gh(
            "-X", "PATCH", f"repos/{repo}/code-scanning/default-setup", body={"state": "configured"}, dry_run=dry))
    if wanted(security["private_vulnerability_reporting"], public):
        ok &= step("Private vulnerability reporting", lambda: gh(
            "-X", "PUT", f"repos/{repo}/private-vulnerability-reporting", dry_run=dry))
    if wanted(security["gitleaks_workflow"], public):
        print("• gitleaks: add workflows/secrets.yml by a pull request (README.md).")
    if wanted(security["semgrep_workflow"], public):
        print("• Semgrep: add workflows/semgrep.yml by a pull request (README.md).")
    if wanted(security["dependabot_version_updates"], public):
        print("• Dependabot version updates: add templates/dependabot.yml as .github/dependabot.yml by a pull request.")
    if wanted(security["security_policy"], public):
        print("• Security policy: add templates/SECURITY.md by a pull request.")

    merge = settings["merge"]
    ok &= step("Merge settings", lambda: gh("-X", "PATCH", f"repos/{repo}", body={
        "delete_branch_on_merge": merge["delete_branch_on_merge"],
        "allow_auto_merge": merge["allow_auto_merge"],
        "allow_squash_merge": merge["allow_squash_merge"],
        "allow_merge_commit": merge["allow_merge_commit"],
        "allow_rebase_merge": merge["allow_rebase_merge"],
    }, dry_run=dry))

    actions = settings["actions"]
    ok &= step("Actions: token permissions", lambda: gh(
        "-X", "PUT", f"repos/{repo}/actions/permissions/workflow", body={
            "default_workflow_permissions": actions["default_workflow_permissions"],
            "can_approve_pull_request_reviews": actions["can_approve_pull_request_reviews"],
        }, dry_run=dry))
    if public:  # GitHub refuses this setting on private repositories
        ok &= step("Actions: approval of pull requests from outside", lambda: gh(
            "-X", "PUT", f"repos/{repo}/actions/permissions/fork-pr-contributor-approval",
            body={"approval_policy": actions["fork_pr_approval"]}, dry_run=dry))

    rules = settings["ruleset"]
    if repo in settings.get("ruleset_exclude", []):
        print(f"• Ruleset {rules['name']}: {repo} is excluded.")
    else:
        body = build_branch_ruleset(rules, args.check)
        ok &= upsert_ruleset(
            repo, body, dry,
            keep_rules=rules.get("keep_existing_rules", []) if not args.check else [])

    tags = settings["tag_ruleset"]
    tag_body = {
        "name": tags["name"],
        "target": "tag",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": {"ref_name": {"include": [f"refs/tags/{tags['pattern']}"], "exclude": []}},
        "rules": [],
    }
    if tags["block_deletion"]:
        tag_body["rules"].append({"type": "deletion"})
    if tags["block_update"]:
        tag_body["rules"].append({"type": "update"})
    ok &= upsert_ruleset(repo, tag_body, dry, keep_rules=tags.get("keep_existing_rules", []))

    if not ok:
        print("Some steps failed; earlier successful changes were not rolled back. Review the output before retrying.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
