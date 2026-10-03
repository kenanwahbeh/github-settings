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


def main():
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
    if security["gitleaks_workflow"] == "all" or (security["gitleaks_workflow"] == "private" and not public):
        print("• gitleaks: add workflows/secrets.yml by a pull request (README.md).")
    if security["semgrep_workflow"] == "all" or (security["semgrep_workflow"] == "private" and not public):
        print("• Semgrep: add workflows/semgrep.yml by a pull request (README.md).")

    merge = settings["merge"]
    ok &= step("Merge settings", lambda: gh("-X", "PATCH", f"repos/{repo}", body={
        "delete_branch_on_merge": merge["delete_branch_on_merge"],
        "allow_auto_merge": merge["allow_auto_merge"],
    }, dry_run=dry))

    rules = settings["ruleset"]
    if repo in settings.get("ruleset_exclude", []):
        print(f"• Ruleset: {repo} is excluded.")
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
        if rules["require_pull_request"]:
            body["rules"].append({"type": "pull_request", "parameters": {
                "allowed_merge_methods": ["merge", "squash", "rebase"],
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
        existing = [r for r in gh(f"repos/{repo}/rulesets?includes_parents=false") if r["name"] == rules["name"]]
        if existing and not args.check:
            # Keep the checks the repository already requires.
            current = gh(f"repos/{repo}/rulesets/{existing[0]['id']}")
            body["rules"] += [r for r in current["rules"] if r["type"] == "required_status_checks"]
        if existing:
            ok &= step(f"Ruleset {rules['name']} (updated)", lambda: gh(
                "-X", "PUT", f"repos/{repo}/rulesets/{existing[0]['id']}", body=body, dry_run=dry))
        else:
            ok &= step(f"Ruleset {rules['name']}", lambda: gh(
                "-X", "POST", f"repos/{repo}/rulesets", body=body, dry_run=dry))

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
