---
name: dependency-updates
description: Check for outdated dependencies and create safe update PRs
category: maintenance
difficulty: easy
---

# Dependency Updates Skill

## Your Task

1. Check for outdated dependencies
2. Assess update safety
3. Test compatibility
4. Create update PRs for safe updates
5. Flag breaking changes for human review

## Check Process

### 1. Scan for Updates

**Node/NPM:**
```bash
npm outdated
```

**Python/pip:**
```bash
pip list --outdated
```

**Rust/Cargo:**
```bash
cargo outdated
```

### 2. Classify Updates

**Patch (1.2.3 → 1.2.4):**
- Bug fixes only
- No breaking changes
- Generally safe
- Action: Auto-update

**Minor (1.2.3 → 1.3.0):**
- New features
- Should be backwards compatible
- Test thoroughly
- Action: Update with testing

**Major (1.2.3 → 2.0.0):**
- Breaking changes expected
- Requires code changes
- Action: Flag for human review

## Safety Checks

Before creating update PR:

1. **Read CHANGELOG**
   - Look for breaking changes
   - Note deprecated features
   - Check migration guides

2. **Check semver compliance**
   - Is package following semver?
   - History of breaking changes in minor versions?

3. **Review dependencies**
   - Does update pull in new deps?
   - Any security vulnerabilities?

4. **Test thoroughly**
   - Run full test suite
   - Run E2E tests if available
   - Check build succeeds

## PR Format

### Good Update PR

```markdown
# Update [package] from X.Y.Z to X.Y.Z+1

## Type: Patch/Minor/Major

## Changes
- [List key changes from CHANGELOG]

## Breaking Changes
- None (or list if any)

## Testing
✅ All tests pass
✅ E2E tests pass
✅ Build succeeds
✅ No new vulnerabilities

## Notes
[Any additional context]
```

## Never Do

- Update packages in lock file without updating package.json
- Skip testing after updates
- Update multiple unrelated packages in one PR
- Ignore security advisories
- Auto-merge major version updates

## Always Do

- One package per PR (easier to revert)
- Run full test suite
- Check for security vulnerabilities
- Document breaking changes clearly
- Link to package changelog

## Special Cases

### Security Updates
- **Priority:** High
- **Action:** Update immediately, even if major version
- **Testing:** Extra thorough
- **PR label:** security-update

### Dev Dependencies
- **Risk:** Lower
- **Testing:** Verify build still works
- **Can batch:** Multiple dev deps in one PR is OK

### Production Dependencies
- **Risk:** Higher
- **Testing:** Full E2E suite
- **Never batch:** One at a time

## Success Criteria

- All outdated packages identified
- Safe updates have PRs opened
- Breaking changes flagged for review
- Test suite passes for all PRs
- State updated with actions taken

## State Tracking

```json
{
  "timestamp": "ISO-8601",
  "packages_checked": 45,
  "outdated": 8,
  "prs_opened": 5,
  "flagged_for_review": 3,
  "categories": {
    "patch": 4,
    "minor": 3,
    "major": 1
  }
}
```

## Examples

### Good: Safe Patch Update
```
Package: lodash
From: 4.17.20
To: 4.17.21
Type: Patch
Changes: Security fix for prototype pollution
Tests: ✅ All pass
PR: #789 "Security: Update lodash to 4.17.21"
```

### Good: Flagged Major Update
```
Package: react
From: 17.0.2
To: 18.2.0
Type: Major
Breaking changes: 
- New JSX transform
- Strict mode changes
- Automatic batching
Action: Flagged for human review
Reason: Major version, requires code review
```

### Bad: Batch Update Without Testing
```
Action: Updated 10 packages at once
Tests: Didn't run (assumed they'd pass)
Result: Build broken, hard to identify which package caused it
Should have: One package per PR, test each
```
