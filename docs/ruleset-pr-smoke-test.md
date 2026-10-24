# Required status checks: PR #18 test record

## Purpose

Verify that the active `main` ruleset requires the expected GitHub Actions checks and blocks a pull request when a required check fails. This is a historical test record; PR #18 was subsequently merged after cleanup.

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

بعد تسجيل رفض الدمج بسبب فشل الفحص، أُزيل التعليق المؤقت وعاد ملفا Semgrep إلى التطابق. نجحت الفحوص على commit التنظيف `6c1530d97a19696841915d380462c993a1067fa2`، ثم دُمج PR #18 بطريقة squash بتاريخ 24 أكتوبر 2026 الساعة 10:15:42 بتوقيت دمشق، إلى commit `45c1363b7375066fdc5f17f54f6cfc3e3a235f5a`.

نجحت أيضاً فحوص الاختبارات والاتساق وGitleaks وSemgrep وCodeQL على commit الدمج. رفض محاولة الدمج أثناء الفشل دليل الاختبار السلبي؛ الدمج اللاحق بعد التنظيف حدث منفصل.

## Conclusion

The negative test succeeded: GitHub explicitly rejected the merge because a required status check was failing. This is direct evidence that the required-check rule was enforced for this PR at the time of the test. The cleanup and subsequent merge results are recorded above.
