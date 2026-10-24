# Required status checks: PR #18 test record

## Purpose

Verify that the active `main` ruleset requires the expected GitHub Actions checks and blocks a pull request when a required check fails. This is a test record; do not merge PR #18.

## Required contexts

The active ruleset requires these exact status-check contexts (names preserved):

- `gitleaks`
- `semgrep`
- `Regression and consistency checks`

All three were configured as required checks from GitHub Actions. The ruleset's strict required-status-check policy was enabled.

## Test procedure

1. Opened PR #18 (`test/ruleset-checks-20261024` into `main`).
2. Temporarily added a comment to `workflows/semgrep.yml` that intentionally made it differ from `.github/workflows/semgrep.yml`.
3. GitHub Actions ran for test commit `663b17605615c13fe02c75f1701718c345ffebfb`.
4. The `Regression and consistency checks` job failed at **Check workflow template synchronization**. The `Run offline regression tests` step passed. The `gitleaks` and `semgrep` checks completed successfully.
5. Attempted to merge PR #18 using GitHub's merge API with squash merge. GitHub rejected the attempt with HTTP 405 and this explicit message: `Repository rule violations found — Required status check "Regression and consistency checks" is failing.` No merge occurred.

## Evidence

- PR: https://github.com/kenanwahbeh/github-settings/pull/18
- Checks: https://github.com/kenanwahbeh/github-settings/pull/18/checks
- Failed workflow run: https://github.com/kenanwahbeh/github-settings/actions/runs/40072500680
- Test commit: `663b17605615c13fe02c75f1701718c345ffebfb`

## Cleanup and current state

After recording the failed-check merge rejection, the temporary comment was removed from `workflows/semgrep.yml` on the test branch, restoring its content to match `.github/workflows/semgrep.yml`. GitHub Actions should be allowed to rerun on the new commit; check the PR Checks tab for the final outcomes. PR #18 is intended to remain open and unmerged. Do not enable auto-merge for this test PR.

## Conclusion

The negative test succeeded: GitHub explicitly rejected the merge because a required status check was failing. This is direct evidence that the required-check rule was enforced for this PR at the time of the test. The new commit's check results must be inspected separately after cleanup.
