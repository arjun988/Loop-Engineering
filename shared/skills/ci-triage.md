---
name: ci-triage
description: Classify CI failures and draft fixes for deterministic bugs
category: testing
difficulty: medium
---

# CI Triage Skill

## Your Task

1. Check the latest CI run status
2. Classify each failure by type
3. Take appropriate action
4. Update state with findings

## Classification Rules

### Flake (Non-deterministic failure)
**Indicators:**
- Passes on retry without code changes
- Timing-related errors
- Race conditions
- Network timeouts

**Action:**
- Retry the test once
- If still fails, file an issue with "flaky-test" label
- Tag for human investigation

### Bug (Deterministic failure)
**Indicators:**
- Fails consistently on the same code
- Clear error message
- Tied to recent commit
- Reproducible locally

**Action:**
- Investigate root cause
- Draft a fix PR
- Run verification before opening PR
- Link to failing CI run

### Env (Environment issue)
**Indicators:**
- Missing environment variables
- Missing secrets
- Infrastructure not provisioned
- Wrong configuration

**Action:**
- Document the missing requirement
- Escalate to human with clear instructions
- Do NOT attempt to fix (requires access)

### Dependency (Version issue)
**Indicators:**
- Failure after dependency update
- Breaking API changes
- Version incompatibility

**Action:**
- Draft rollback PR to previous version
- Or draft fix PR if change is simple
- Document the issue for future reference

### Infra (Infrastructure issue)
**Indicators:**
- Runner timeouts
- Out of memory errors
- Disk space issues
- CI platform problems

**Action:**
- Document the issue
- Escalate to human
- Do NOT attempt to fix

## Fix Patterns

### Auth Tests
- Check `src/auth/middleware` first
- Verify JWT configuration
- Check session handling

### Database Tests
- Verify migrations applied in CI environment
- Check seed data
- Verify connection strings

### E2E Tests
- Check selectors against latest UI
- Verify test data setup
- Check for timing issues

## Never Do

- Modify `src/auth/` or `src/payments/` (security-sensitive)
- Disable failing tests (always file issue instead)
- Modify CI config without human approval
- Make changes to prod configuration
- Guess at fixes without understanding root cause

## Success Criteria

- All failures classified
- Appropriate action taken for each
- State updated with:
  - Files checked
  - Classifications made
  - PRs opened
  - Escalations filed
- Verification passed for any code changes

## State Tracking

Update `.loop/state/ci-triage.json` after each run with:

```json
{
  "timestamp": "ISO-8601",
  "failures_found": 3,
  "classifications": {
    "flake": 1,
    "bug": 1,
    "env": 1
  },
  "actions_taken": [
    "Opened PR #123 for deterministic auth failure",
    "Filed issue #456 for flaky payment test",
    "Escalated env issue: missing STRIPE_SECRET"
  ]
}
```

## Examples

### Good: Clear Bug Fix
```
Found: Auth test failing on login endpoint
Root cause: Missing validation for empty password
Fix: Added validation check
Verification: All tests pass
PR: #123 "Fix: Add password validation"
```

### Good: Flake Detection
```
Found: Payment webhook test intermittent
Pattern: Fails ~30% of runs
Root cause: Race condition in async handler
Action: Filed issue #456 with reproduction steps
Tag: flaky-test, needs-investigation
```

### Bad: Guessing
```
Found: Database test failing
Action: Changed connection timeout (guessing)
Result: Still fails, wasted time
Should have: Investigated actual error message first
```
