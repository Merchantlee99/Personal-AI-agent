#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${ROOT_DIR}" ]]; then
  echo "[guard] Not inside a git repository."
  exit 1
fi

cd "${ROOT_DIR}"

declare -a blocked_paths=()
while IFS= read -r file; do
  case "${file}" in
    .env|.env.local|.env.*.local|shared_data/*|.next/*|node_modules/*|*.db|*.db-*|*.sqlite|*.sqlite3)
      blocked_paths+=("${file}")
      ;;
  esac
done < <(git ls-files)

if [[ "${#blocked_paths[@]}" -gt 0 ]]; then
  echo "[guard] Push blocked: sensitive/runtime files are tracked."
  for file in "${blocked_paths[@]}"; do
    echo " - ${file}"
  done
  echo "[guard] Untrack them first: git rm --cached <file>"
  exit 1
fi

SECRET_PATTERN='(OPENAI_API_KEY[[:space:]]*=|ANTHROPIC_API_KEY[[:space:]]*=|GEMINI_API_KEY[[:space:]]*=|N8N_BASIC_AUTH_PASSWORD[[:space:]]*=|sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{20,})'
secret_hits="$(git grep -n -I -E "${SECRET_PATTERN}" -- . || true)"
secret_hits="$(printf "%s\n" "${secret_hits}" | grep -vE '(^|:)\.env\.local\.example:|\.example:' || true)"

if [[ -n "${secret_hits}" ]]; then
  echo "[guard] Push blocked: possible secrets detected in tracked files."
  printf "%s\n" "${secret_hits}"
  exit 1
fi

echo "[guard] OK: no blocked files or obvious secrets detected."
