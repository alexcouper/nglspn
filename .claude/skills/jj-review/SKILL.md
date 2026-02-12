---
name: jj-review
description: Code review changes since main branch using JJ (Jujutsu). Use when asked to review code, check changes, or audit recent work.
disable-model-invocation: true
---

# Code Review

Review the changes since main branch using JJ (Jujutsu).

## Review Focus Areas

1. **Style** - Do the changes match our standards: simple, elegant, concise?
2. **Comments** - Are there unnecessary comments that don't aid readability?
3. **Tests** - Do tests cover obvious cases? Are any missing?
4. **Performance** - Will any added queries cause issues at scale? N+1 problems?

## Process

1. Get the diff since main:
   ```bash
   jj log --no-graph -r "main::@" --template 'commit_id.short() ++ " " ++ description ++ "\n"'
   jj diff -r "main::@" --stat
   jj diff -r "main::@" --git
   ```

2. For large diffs, focus on:
   - Model changes (migrations, models.py)
   - API endpoints (routers/, schemas/)
   - Business logic (services/, utils/)
   - Test coverage (tests/)
   - UI components (components/, app/)

3. Look for:
   - Duplicated code that should be extracted
   - Missing error handling
   - Untested edge cases
   - Queries inside loops (N+1)
   - Hardcoded values that should be constants

## Output Format

Group findings by priority:

### Priority 1: Must Fix Before Merge
Issues that will cause bugs, security problems, or significant tech debt.

### Priority 2: Should Fix
Code quality issues, missing tests for new functionality, duplication.

### Priority 3: Minor / Style
Nitpicks, formatting, suggestions for future improvement.

### What Looks Good
Acknowledge well-done aspects.

Include code snippets where helpful. Reference files with `file_path:line_number` format.
