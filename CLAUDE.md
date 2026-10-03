# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## This is the reference ("model") repository

This repository (`kenanwahbeh/github-settings`) is the **model repository** (المستودع النموذج) for Kinan's GitHub setup. If an agent is asked to read the model repository and "do the same" for another repository, it must reproduce what this repository does for that target:

1. Run `apply.py` against the target (`--dry-run` first), passing `--check <name>` only for CI checks the target really reports.
2. For a **private** target, also add `workflows/secrets.yml` (gitleaks) and `workflows/semgrep.yml` via a pull request, following the steps in `README.md`, then re-apply with `--check gitleaks --check semgrep` plus the target's other CI checks.
3. Add `templates/dependabot.yml` (as `.github/dependabot.yml`, adding the target's ecosystems) and, for a public target, `templates/SECURITY.md`, in the same pull request.
4. Report the manual, no-API items from `README.md` ("ما لا API له") rather than trying to automate them.

The README and user-facing explanations are written in Arabic; keep that language when editing them.

## Commands

Requires an authenticated `gh` and `uv` (dependencies are declared inline in `apply.py`; there is no build, lint, or test suite).

```bash
uv run apply.py kenanwahbeh/<repo> --dry-run      # print the gh api calls only
uv run apply.py kenanwahbeh/<repo>                # apply
uv run apply.py kenanwahbeh/<repo> --check test   # also require CI check "test"; repeatable
```

Exit code is non-zero if any step failed. `gitleaks` / Semgrep are not run by `apply.py`; it only prints a reminder to add them by pull request.

## Architecture

- `settings.yml` is the single source of truth (security toggles, merge options, `ruleset`, `ruleset_exclude`). `apply.py` reads it and translates each key into `gh api` REST calls via `gh()`; `step()` wraps each call so one failure (e.g. paid features refused on private repos) is printed and the rest continue.
- The `main` ruleset is built from `settings.yml` (`deletion`, `non_fast_forward`, `pull_request` rules) with `bypass_actors: []` on `~DEFAULT_BRANCH`. If a ruleset named `main` already exists it is `PUT`-updated, and when no `--check` is passed its existing `required_status_checks` rule is carried over so re-running does not drop required checks.
- A second ruleset (`tag_ruleset`, target `tag`, pattern `v*`) blocks deleting or moving release tags. The `main` ruleset also requires signed commits and allows squash merges only (keep `merge.allow_*` and `ruleset.allowed_merge_methods` consistent). Both go through `upsert_ruleset()`.
- `apply.py` also sets Actions defaults (read-only `GITHUB_TOKEN`, approval for outside-contributor PRs) and, on public repos only, private vulnerability reporting. `sha_pinning_required` is deliberately not enforced because `workflows/semgrep.yml` accepts tag-pinned actions.
- Repos listed in `ruleset_exclude` skip the `main` ruleset only; the tag ruleset and all other settings still apply.
- `workflows/*.yml` are templates to copy into target repos' `.github/workflows/`. `.github/workflows/*.yml` here are identical copies, so this repo is protected by the same gitleaks and Semgrep checks. Keep the two directories in sync when editing either. `templates/dependabot.yml` is likewise mirrored at `.github/dependabot.yml`; `templates/SECURITY.md` (public targets) is mirrored at `SECURITY.md`.

## Gotchas

- Never pass `--check` with a name the target's CI does not report: the ruleset would then block every merge.
- Secret scanning and CodeQL may be rejected on private repos (paid add-ons); that is expected, and gitleaks/Semgrep are the substitute.
- Changes to this repo itself go through pull requests (the `main` ruleset applies here too).
