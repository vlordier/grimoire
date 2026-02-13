# Constitution Update Workflow

This document describes the systematic process for keeping the constitution synchronized with documentation in `docs/`.

## Quick Audit

Run the audit script to check if all docs are referenced:

```bash
.specify/scripts/bash/audit-constitution-docs.sh
```

Expected output if up to date:
```
✅ All docs/ files are referenced in constitution!
```

## Full Update Process

### 1. Discovery Phase

Identify unreferenced documentation:

```bash
# Automated check
./.specify/scripts/bash/audit-constitution-docs.sh

# Manual check
comm -13 \
  <(grep -o 'docs/[^)]*\.md' .specify/memory/constitution.md | sort -u) \
  <(find docs -type f -name "*.md" | sort)
```

### 2. Review Phase

For each unreferenced file:

```bash
# Read first 50 lines to understand purpose
head -50 docs/path/to/file.md

# Identify section placement in constitution:
# - Vision & Strategy: Product goals, target users, success metrics
# - Domain Knowledge: Problem types, FSMs, dangers, control patterns
# - Data & Storage: Schemas, storage mapping, database setup
# - Implementation Reference: Algorithms, classifiers, pipelines
# - Operational Specifications: Auth, versioning, multi-tenancy, etc.
```

### 3. Update Phase

Edit [.specify/memory/constitution.md](.specify/memory/constitution.md):

```markdown
### [Section Name]

- [New Doc Title](../../docs/path/to/file.md) — Brief description of content
```

**Guidelines:**
- Place in appropriate section based on content type
- Add descriptive summary (10-20 words) after the em-dash
- Maintain alphabetical or logical ordering within section
- Update the Sync Impact Report header with version bump

### 4. Version Bump

Follow semantic versioning:

- **PATCH** (1.2.1 → 1.2.2): Documentation reference added, clarifications
- **MINOR** (1.2.0 → 1.3.0): New principle added, material expansion
- **MAJOR** (1.0.0 → 2.0.0): Breaking changes to core principles

Update Sync Impact Report at top of constitution.md:

```markdown
<!--
  Sync Impact Report
  ===================
  Version change: 1.2.x → 1.2.y (patch update - description)

  Added documentation:
    - docs/path/file.md: Purpose and key content

  Modified sections:
    - Section name: What changed

  Removed sections: None

  ...
-->
```

### 5. Validation Phase

Check feature spec compliance:

```bash
# Find all specs with constitution version references
grep -r "Constitution Version" specs/*/spec.md

# Update each spec.md to reference new version (if MINOR/MAJOR bump)
# PATCH bumps typically don't require spec updates
```

### 6. Commit

```bash
git add .specify/memory/constitution.md
git commit -m 'constitution: v1.x.y - brief description

- Added docs/path/file1.md reference
- Added docs/path/file2.md reference
- Updated [Section] with new documentation'
```

## Recurring Audit Schedule

**Recommended frequency:** Quarterly or before major releases

**Checklist:**
1. Run audit script
2. Review any new docs/ files added since last audit
3. Update constitution if needed
4. Version bump appropriately
5. Update feature specs if principles changed (MINOR/MAJOR only)
6. Commit changes

## Automation Opportunities

Future enhancements:

- [ ] Pre-commit hook to run audit script
- [ ] CI check that fails if docs/ has unreferenced files
- [ ] Auto-generate constitution section from docs/ metadata
- [ ] Track docs-to-principles mapping for impact analysis

## Example: Recent Update (v1.2.2)

```bash
# Discovered missing files
$ .specify/scripts/bash/audit-constitution-docs.sh
⚠️  Missing from constitution:
   ✗ docs/vision/prd-executive.md
   ✗ docs/vision/prd.md

# Reviewed content
$ head -50 docs/vision/prd.md
# Product Requirements Document (PRD)
...target users, problem statement, product vision...

# Determined section: Vision & Strategy

# Updated constitution.md:
- [PRD Executive Summary](../../docs/vision/prd-executive.md) — 1-page overview
- [Product Requirements Document](../../docs/vision/prd.md) — Full PRD

# Version bump: 1.2.1 → 1.2.2 (PATCH - documentation only)

# Committed
$ git commit -m 'constitution: v1.2.2 - add PRD documentation'
```

## Troubleshooting

**Issue:** Script shows unreferenced but file is in constitution
- Check that file path uses exact relative path format
- Ensure markdown link syntax: `[Title](../../docs/path/file.md)`
- No spaces or extra characters in path

**Issue:** Can't determine which section for new doc
- Read full doc to understand purpose
- Look for similar existing docs in constitution
- When in doubt: place in Vision & Strategy or Reference Documentation
- Ask in PR review for section placement feedback

