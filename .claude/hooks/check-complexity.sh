#!/bin/bash

# Extract the file path from the hook input (JSON from stdin)
file_path=$(cat | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# Only check Python files
if [[ ! "$file_path" =~ \.py$ ]]; then
  exit 0
fi

# Check if file exists
if [[ ! -f "$file_path" ]]; then
  exit 0
fi

# Run radon complexity check (only show grade C or worse)
result=$(uv run radon cc "$file_path" -s -n C 2>/dev/null)

if [[ -n "$result" ]]; then
  echo "⚠️  Complexity Warning: $file_path"
  echo "$result"
  echo ""
  echo "Functions with grade C+ should be refactored."
fi
