#!/bin/bash

# ============================================
# Complexity & Lint Checker Hook
# ============================================
# Modes:
#   1. Single file mode (PostToolUse): Checks one file from JSON stdin
#   2. Batch mode (--changed): Checks all git changed/staged files
#
# Usage:
#   PostToolUse: cat json | ./check-complexity.sh
#   Batch mode:  ./check-complexity.sh --changed
# ============================================

# Batch mode: check all changed/staged files
if [[ "$1" == "--changed" ]]; then
  # Get git root directory
  git_root=$(git rev-parse --show-toplevel 2>/dev/null)
  if [[ -z "$git_root" ]]; then
    echo "Error: Not a git repository"
    exit 1
  fi

  # Get changed and staged files (both modified and new)
  changed_files=$(git diff --name-only HEAD 2>/dev/null)
  staged_files=$(git diff --cached --name-only 2>/dev/null)
  untracked_files=$(git ls-files --others --exclude-standard 2>/dev/null)

  # Combine and deduplicate
  all_files=$(echo -e "${changed_files}\n${staged_files}\n${untracked_files}" | sort -u | grep -v '^$')

  if [[ -z "$all_files" ]]; then
    echo "✅ No changed files to check."
    exit 0
  fi

  echo "📋 Checking changed/staged files for complexity and lint issues..."
  echo ""

  has_issues=0

  while IFS= read -r rel_path; do
    file_path="$git_root/$rel_path"

    # Skip if file doesn't exist
    [[ ! -f "$file_path" ]] && continue

    # Python files
    if [[ "$file_path" =~ \.py$ ]]; then
      result=$(uv run radon cc "$file_path" -s -n C 2>/dev/null)
      if [[ -n "$result" ]]; then
        echo "⚠️  Python Complexity Warning: $rel_path"
        echo "$result"
        echo ""
        has_issues=1
      fi
    fi

    # TypeScript/TSX files in src/web
    if [[ "$file_path" =~ \.(ts|tsx)$ ]] && [[ "$file_path" =~ src/web/ ]]; then
      web_dir=$(echo "$file_path" | sed 's|\(.*src/web\)/.*|\1|')

      # Biome lint check
      biome_result=$(cd "$web_dir" && npx biome lint "$file_path" 2>&1 | head -30)
      if [[ -n "$biome_result" && "$biome_result" =~ (error|warning) ]]; then
        echo "⚠️  TypeScript/Biome Warning: $rel_path"
        echo "$biome_result"
        echo ""
        has_issues=1
      fi

      # tsc type check
      tsc_result=$(cd "$web_dir" && npx tsc --noEmit --project tsconfig.json 2>&1 | grep -F "$file_path" | head -20)
      if [[ -n "$tsc_result" && "$tsc_result" =~ "error TS" ]]; then
        echo "⚠️  TypeScript Type Error: $rel_path"
        echo "$tsc_result"
        echo ""
        has_issues=1
      fi
    fi
  done <<< "$all_files"

  if [[ $has_issues -eq 0 ]]; then
    echo "✅ No complexity or lint issues found in changed files."
  fi

  exit 0
fi

# ============================================
# Single file mode (PostToolUse)
# ============================================

# Extract the file path from the hook input (JSON from stdin)
file_path=$(cat | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# Skip if no file path
if [[ -z "$file_path" ]]; then
  exit 0
fi

# Check if file exists
if [[ ! -f "$file_path" ]]; then
  exit 0
fi

# ============================================
# Python files: Check with radon cc
# ============================================
if [[ "$file_path" =~ \.py$ ]]; then
  result=$(uv run radon cc "$file_path" -s -n C 2>/dev/null)

  if [[ -n "$result" ]]; then
    echo "⚠️  Python Complexity Warning: $file_path"
    echo "$result"
    echo ""
    echo "Functions with grade C+ should be refactored."
  fi
fi

# ============================================
# TypeScript/TSX files: Check with Biome and tsc
# ============================================
if [[ "$file_path" =~ \.(ts|tsx)$ ]]; then
  # Only check files in src/web directory
  if [[ "$file_path" =~ src/web/ ]]; then
    # Get the web directory path
    web_dir=$(echo "$file_path" | sed 's|\(.*src/web\)/.*|\1|')

    # Run Biome lint
    result=$(cd "$web_dir" && npx biome lint "$file_path" 2>&1 | head -20)

    if [[ -n "$result" && "$result" =~ (error|warning) ]]; then
      echo "⚠️  TypeScript/Biome Warning: $file_path"
      echo "$result"
      echo ""
    fi

    # Run tsc --noEmit for type checking (like IDE)
    # Use project tsconfig to get proper lib settings
    tsc_result=$(cd "$web_dir" && npx tsc --noEmit --project tsconfig.json 2>&1 | grep -F "$file_path" | head -20)

    if [[ -n "$tsc_result" && "$tsc_result" =~ "error TS" ]]; then
      echo "⚠️  TypeScript Type Error: $file_path"
      echo "$tsc_result"
      echo ""
    fi
  fi
fi
