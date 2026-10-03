# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Apply settings.yml to one repository with the gh CLI.

    uv run apply.py owner/repo [--check test --check lint] [--dry-run]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml


def gh(*args, body=None, dry_run=False):
    command = ["gh", "api", *args]
    if dry_run:
        print("  would run:", " ".join(command), json.dumps(body) if body else "")
        return {}
    result = subprocess.run(
        command + (["--input", "-"] if body is not None else []),
        input=json.dumps(body) if body is not None else None,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout) if result.stdout.strip() else {}


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


def upsert_ruleset(repo, body, dry, keep_checks=False):
    """Create the ruleset, or update the one with the same name."""
    existing = [r for r in gh(f"repos/{repo}/rulesets?includes_parents=false") if r["name"] == body["name"]]
    if existing and keep_checks:
        # Keep the checks the repository already requires.
        current = gh(f"repos/{repo}/rulesets/{existing[0]['id']}")
        body["rules"] += [r for r in current["rules"] if r["type"] == "required_status_checks"]
    if existing:
        return step(f"Ruleset {body['name']} (updated)", lambda: gh(
            "-X", "PUT", f"repos/{repo}/rulesets/{existing[0]['id']}", body=body, dry_run=dry))
    return step(f"Ruleset {body['name']}", lambda: gh(
        "-X", "POST", f"repos/{repo}/rulesets", body=body, dry_run=dry))


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # the Windows console defaults to a legacy code page
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", help="owner/repo")
    parser.add_argument("--check", action="append", default=[], help="a required CI check")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    settings = yaml.safe_load((Path(__file__).parent / "settings.yml").read_text())
    repo, dry = args.repo, args.dry_run

    info = gh(f"repos/{repo}")
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
    if security["codeql_default_setup"]:
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
        if args.check:
            body["rules"].append({"type": "required_status_checks", "parameters": {
                "strict_required_status_checks_policy": False,
                "do_not_enforce_on_create": False,
                "required_status_checks": [{"context": name} for name in args.check],
            }})
        ok &= upsert_ruleset(repo, body, dry, keep_checks=not args.check)

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
    ok &= upsert_ruleset(repo, tag_body, dry)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
