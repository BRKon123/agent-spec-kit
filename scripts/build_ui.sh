#!/usr/bin/env bash
# Build the agent-spec-kit UI bundle into src/agent_spec_kit/web/dist/.
# CI should run this before `uv build` so the wheel ships built JS.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}/frontend"

if [[ "${CI:-}" == "true" || "${1:-}" == "--ci" ]]; then
  npm ci --no-audit --no-fund
else
  if [[ ! -d node_modules ]]; then
    npm install --no-audit --no-fund
  fi
fi

npm run build

dist="${repo_root}/src/agent_spec_kit/web/dist"
if [[ ! -f "${dist}/index.html" ]]; then
  echo "build_ui: expected ${dist}/index.html after build" >&2
  exit 1
fi
echo "build_ui: wrote ${dist}"
