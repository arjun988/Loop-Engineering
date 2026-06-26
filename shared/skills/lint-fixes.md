---
name: lint-fixes
description: Apply automated linting and formatting fixes
category: code-quality
difficulty: easy
---

# Lint & Format Fixes Skill

## Your Task

1. Run linter in auto-fix mode
2. Apply safe formatting changes
3. Verify no logic changes
4. Commit fixes
5. Verify tests still pass

## Supported Tools

### JavaScript/TypeScript
- **ESLint:** `eslint --fix`
- **Prettier:** `prettier --write`
- **Both:** Run ESLint first, then Prettier

### Python
- **Black:** `black .`
- **isort:** `isort .`
- **Ruff:** `ruff check --fix`

### Rust
- **rustfmt:** `cargo fmt`
- **clippy:** `cargo clippy --fix`

### Go
- **gofmt:** `go fmt ./...`
- **goimports:** `goimports -w .`

## Process

### 1. Run Auto-fix

```bash
# Example for Node project
npm run lint:fix
# or
eslint --fix .
prettier --write .
```

### 2. Review Changes

**Safe changes (auto-commit):**
- Indentation/whitespace
- Semicolons
- Quote style
- Import ordering
- Trailing commas
- Line length wrapping

**Unsafe changes (review required):**
- Variable renames
- Logic changes
- Removed code
- Added code

### 3. Verify

Run full test suite:
```bash
npm test
# or
pytest
# or
cargo test
```

### 4. Commit

```
lint: apply automated fixes

- Fixed indentation in src/
- Sorted imports
- Applied prettier formatting

No logic changes.
```

## Never Do

- Apply fixes that change logic
- Skip testing after fixes
- Commit fixes mixed with feature changes
- Ignore linter warnings that can't auto-fix
- Modify generated files

## Always Do

- Run tests after applying fixes
- Review diffs before committing
- Keep lint fixes in separate commits
- Document what was fixed
- Ensure no logic changes

## Safety Checks

Before committing:

1. **Diff review:**
   - Are all changes formatting-only?
   - No logic changes?
   - No removed functionality?

2. **Test verification:**
   - All tests pass?
   - No new failures?
   - Same coverage?

3. **Build check:**
   - Project still builds?
   - No new errors?
   - Types still check?

## Special Cases

### Generated Files
**Examples:** Protobuf, GraphQL codegen, migrations
**Action:** Skip (add to .prettierignore or similar)
**Reason:** Will be regenerated, changes will be lost

### Third-party Code
**Examples:** vendor/, node_modules/, copied libraries
**Action:** Skip
**Reason:** Not our code to lint

### Config Files
**Examples:** package.json, tsconfig.json
**Action:** Format but verify carefully
**Reason:** Easy to break builds

## Success Criteria

- All auto-fixable issues resolved
- Tests pass
- Build succeeds
- No logic changes
- Clean git diff (formatting only)
- State updated

## State Tracking

```json
{
  "timestamp": "ISO-8601",
  "files_modified": 23,
  "issues_fixed": 145,
  "categories": {
    "indentation": 45,
    "quotes": 32,
    "imports": 28,
    "whitespace": 40
  },
  "tests_passed": true
}
```

## Examples

### Good: Clean Formatting Fix
```
Files: src/components/*.tsx
Changes:
- Fixed indentation (2 spaces)
- Sorted imports
- Added trailing commas
Tests: ✅ All pass
Commit: "lint: format components directory"
```

### Good: Caught Logic Change
```
Linter suggested: Remove unused variable
Review: Variable is used in different file
Action: Keep variable, add eslint-disable comment
Reason: Auto-fix would have broken code
```

### Bad: Mixed Changes
```
Commit includes:
- Lint fixes (formatting)
- New feature (added function)
- Bug fix (changed logic)
Problem: Can't revert cleanly, hard to review
Should have: Three separate commits
```

### Bad: Skipped Testing
```
Applied: prettier --write .
Changed: 50 files
Tests: Didn't run (assumed formatting is safe)
Result: Broke JSX due to comment placement
Should have: Tested before committing
```

## Integration with PR Workflow

### On PR Open
1. Run lint:fix automatically
2. If fixes needed:
   - Apply fixes
   - Push as new commit
   - Comment on PR: "Applied automated lint fixes"
3. If no fixes needed:
   - Add comment: "✅ Lint checks pass"

### Pre-commit Hook
```bash
#!/bin/bash
# Run linter on staged files only
npm run lint:fix --staged
git add -u  # Add fixes to commit
```

## Performance Notes

- Run on changed files only for speed
- Use `--cache` flags when available
- Consider parallel execution for large codebases
- Cache lint results in CI

## Troubleshooting

### Linter Conflicts
**Problem:** ESLint and Prettier disagree
**Solution:** Use eslint-config-prettier to disable conflicting rules

### Auto-fix Loops
**Problem:** Linter keeps changing same file
**Solution:** Check for conflicting rules, disable one

### Test Failures
**Problem:** Tests fail after formatting
**Solution:** Review diffs, likely unsafe change
