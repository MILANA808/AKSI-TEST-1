#!/usr/bin/env bash
set -euo pipefail

if [[ ${1:-} == "-h" || ${1:-} == "--help" || $# -lt 1 ]]; then
  cat <<'USAGE'
Usage:
  ./scripts/merge_repos.sh <repo_url_or_path> [<repo_url_or_path> ...]

Description:
  Clones/copies multiple repositories into ./apps/<repo_name>, removes nested .git folders,
  and creates an aggregate apps.manifest file to run all apps from one mono-repo.
USAGE
  exit 0
fi

mkdir -p apps
: > apps.manifest

normalize_name() {
  local src="$1"
  local base
  base="$(basename "$src")"
  base="${base%.git}"
  echo "$base"
}

copy_local_repo() {
  local src="$1"
  local dest="$2"
  if [[ ! -d "$src" ]]; then
    echo "[ERROR] Local path not found: $src" >&2
    return 1
  fi
  rsync -a --exclude='.git' "$src/" "$dest/"
}

clone_remote_repo() {
  local src="$1"
  local dest="$2"
  git clone --depth 1 "$src" "$dest"
  rm -rf "$dest/.git"
}

for repo in "$@"; do
  name="$(normalize_name "$repo")"
  target="apps/$name"

  if [[ -e "$target" ]]; then
    echo "[WARN] $target already exists, skipping"
    continue
  fi

  echo "[INFO] Importing: $repo -> $target"
  mkdir -p "$target"

  if [[ "$repo" =~ ^https?:// ]] || [[ "$repo" =~ ^git@ ]]; then
    clone_remote_repo "$repo" "$target"
  else
    copy_local_repo "$repo" "$target"
  fi

  echo "$name|$repo" >> apps.manifest
done

echo "[DONE] Imported repositories:"
cat apps.manifest
