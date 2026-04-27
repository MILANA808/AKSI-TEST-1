#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage:
  $(basename "$0") --source OWNER/REPO [--dest DIR] [--fork-name NAME]

Creates a GitHub fork for safe testing (without modifying original repo),
clones the fork locally, and configures remotes:
  - origin   => your fork (push here)
  - upstream => original repository (read-only)

Environment:
  - Uses GH_TOKEN or GITHUB_TOKEN if set
  - Falls back to: gh auth token (if GitHub CLI is installed and logged in)
USAGE
}

SOURCE_REPO=""
DEST_DIR=""
FORK_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      SOURCE_REPO="${2:-}"
      shift 2
      ;;
    --dest)
      DEST_DIR="${2:-}"
      shift 2
      ;;
    --fork-name)
      FORK_NAME="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$SOURCE_REPO" ]]; then
  echo "Error: --source is required" >&2
  usage
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required" >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required" >&2
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  echo "Error: git is required" >&2
  exit 1
fi

TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
if [[ -z "$TOKEN" ]] && command -v gh >/dev/null 2>&1; then
  TOKEN="$(gh auth token 2>/dev/null || true)"
fi
if [[ -z "$TOKEN" ]]; then
  echo "Error: set GH_TOKEN (or GITHUB_TOKEN), or login with GitHub CLI (gh auth login)." >&2
  exit 1
fi

API="https://api.github.com"
AUTH_HEADER="Authorization: token $TOKEN"
ACCEPT_HEADER="Accept: application/vnd.github+json"

VIEWER_JSON="$(curl -fsSL -H "$AUTH_HEADER" -H "$ACCEPT_HEADER" "$API/user")"
LOGIN="$(echo "$VIEWER_JSON" | jq -r '.login')"
if [[ -z "$LOGIN" || "$LOGIN" == "null" ]]; then
  echo "Error: unable to resolve authenticated GitHub user" >&2
  exit 1
fi

SOURCE_OWNER="${SOURCE_REPO%%/*}"
SOURCE_NAME="${SOURCE_REPO##*/}"
if [[ -z "$FORK_NAME" ]]; then
  FORK_NAME="$SOURCE_NAME-test"
fi

FORK_REPO="$LOGIN/$FORK_NAME"
FORK_URL="https://github.com/$FORK_REPO.git"

if [[ -z "$DEST_DIR" ]]; then
  DEST_DIR="./apps/$FORK_NAME"
fi

echo "[1/4] Creating fork: $FORK_REPO (source: $SOURCE_REPO)"
create_payload="{\"name\":\"$FORK_NAME\",\"default_branch_only\":false}"
set +e
fork_resp="$(curl -sS -X POST -H "$AUTH_HEADER" -H "$ACCEPT_HEADER" "$API/repos/$SOURCE_REPO/forks" -d "$create_payload")"
status=$?
set -e
if [[ $status -ne 0 ]]; then
  echo "Error: fork creation API call failed" >&2
  exit 1
fi

if echo "$fork_resp" | jq -e '.message? // empty' >/dev/null 2>&1; then
  msg="$(echo "$fork_resp" | jq -r '.message')"
  if [[ "$msg" != "null" && "$msg" != "" && "$msg" != "name already exists on this account" ]]; then
    echo "GitHub API response: $msg" >&2
  fi
fi

echo "[2/4] Waiting for fork to be available"
for _ in {1..30}; do
  if curl -fsSL -H "$AUTH_HEADER" -H "$ACCEPT_HEADER" "$API/repos/$FORK_REPO" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -fsSL -H "$AUTH_HEADER" -H "$ACCEPT_HEADER" "$API/repos/$FORK_REPO" >/dev/null 2>&1; then
  echo "Error: fork was not ready in time: $FORK_REPO" >&2
  exit 1
fi

if [[ -e "$DEST_DIR" ]]; then
  echo "Error: destination already exists: $DEST_DIR" >&2
  exit 1
fi

echo "[3/4] Cloning fork to $DEST_DIR"
git clone "$FORK_URL" "$DEST_DIR"

pushd "$DEST_DIR" >/dev/null

if git remote get-url upstream >/dev/null 2>&1; then
  git remote remove upstream
fi

git remote add upstream "https://github.com/$SOURCE_REPO.git"
git remote set-url --push upstream "DISABLED"

echo "[4/4] Remotes configured"
git remote -v

popd >/dev/null

cat <<DONE

Done.
- Original repo is untouched: https://github.com/$SOURCE_REPO
- Work/push only to fork:       https://github.com/$FORK_REPO
- Local clone path:             $DEST_DIR

Recommended next steps:
  cd "$DEST_DIR"
  # then deploy this fork on Render (Blueprint or manual settings).
DONE
