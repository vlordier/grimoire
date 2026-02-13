#!/usr/bin/env bash
set -euo pipefail

# audit-constitution-docs.sh
# Purpose: Audit docs/ directory and report which files are not referenced in constitution
# Usage: ./audit-constitution-docs.sh [--fix]

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
CONSTITUTION="${REPO_ROOT}/.specify/memory/constitution.md"
DOCS_DIR="${REPO_ROOT}/docs"

echo "════════════════════════════════════════════════════════════"
echo "Constitution Documentation Audit"
echo "════════════════════════════════════════════════════════════"
echo ""

# Find all markdown files in docs/
all_docs=$(find "$DOCS_DIR" -type f -name "*.md" | sed "s|$REPO_ROOT/||" | sort)
total_docs=$(echo "$all_docs" | wc -l | tr -d ' ')

# Find all docs referenced in constitution (extract from markdown links)
referenced_docs=$(grep -o 'docs/[^)]*\.md' "$CONSTITUTION" | sort -u)
referenced_count=$(echo "$referenced_docs" | wc -l | tr -d ' ')

# Find unreferenced docs
unreferenced_docs=$(comm -13 <(echo "$referenced_docs") <(echo "$all_docs"))
if [ -z "$unreferenced_docs" ]; then
    unreferenced_count=0
else
    unreferenced_count=$(echo "$unreferenced_docs" | wc -l | tr -d ' ')
fi

echo "📊 Status:"
echo "   Total docs in docs/: $total_docs"
echo "   Referenced in constitution: $referenced_count"
echo "   Unreferenced: $unreferenced_count"
echo ""

if [ "$unreferenced_count" -eq 0 ]; then
    echo "✅ All docs/ files are referenced in constitution!"
    echo ""
    echo "Constitution is up to date."
    exit 0
fi

echo "⚠️  Missing from constitution:"
echo ""
if [ -n "$unreferenced_docs" ]; then
    echo "$unreferenced_docs" | while IFS= read -r doc; do
        if [ -n "$doc" ]; then
            echo "   ✗ $doc"
        fi
    done
fi
echo ""

echo "────────────────────────────────────────────────────────────"
echo "Next Steps:"
echo "────────────────────────────────────────────────────────────"
echo ""
echo "1. Review each unreferenced file"
echo ""
echo "2. Determine which section it belongs to:"
echo "   - Vision & Strategy (PRD, goals, target users)"
echo "   - Domain Knowledge (problem types, FSMs, dangers)"
echo "   - Data & Storage (schemas, storage mapping)"
echo "   - Implementation Reference (algorithms, pipelines)"
echo "   - Operational Specifications (auth, versioning, etc.)"
echo ""
echo "3. Update constitution:"
echo "   $ vim .specify/memory/constitution.md"
echo "   Add reference under appropriate section"
echo ""
echo "4. Version bump:"
echo "   MINOR: New knowledge domain added"
echo "   PATCH: Documentation reference added"
echo ""
echo "5. Update version in sync report header"
echo ""
echo "6. Commit:"
echo "   $ git add .specify/memory/constitution.md"
echo "   $ git commit -m 'constitution: v1.x.y - add [description]'"
echo ""

if [ "${1:-}" = "--fix" ]; then
    echo "════════════════════════════════════════════════════════════"
    echo "Auto-fix not implemented yet."
    echo "Manual review required to determine correct section placement."
    echo "════════════════════════════════════════════════════════════"
fi

exit 0
