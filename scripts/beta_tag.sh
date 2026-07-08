#!/usr/bin/env bash

set -eo pipefail

# beta_tag.sh
#
# Creates and pushes a pre-release beta tag for the current version defined in
# pyproject.toml (the target GA version).
# When the base version in pyproject.toml is bumped to a new GA (e.g. 0.38.0)
# the beta counter naturally resets because there are no v0.38.0-beta.* tags yet.

ORIGIN=${ORIGIN:-origin}
COMMIT=${COMMIT:-HEAD}

if [[ $(git status --porcelain) != "" ]]; then
  echo "Error: repo is dirty. Run git status, clean repo and try again."
  exit 1
elif [[ $(git status --porcelain -b | grep -e "ahead" -e "behind") != "" ]]; then
  echo "Error: repo has unpushed commits. Push commits to remote and try again."
  exit 1
fi

# Check if user has push access
if ! git ls-remote --exit-code "$ORIGIN" >/dev/null 2>&1; then
  echo "Error: Cannot access remote repository. Ensure you have push permissions."
  exit 1
fi

# Get base version from pyproject.toml (the current/target GA version).
# `poetry version` prints "pydo X.Y.Z"; strip the leading "pydo ".
poetry_version=$(poetry version)
base_version="${poetry_version:5}"
if [ -z "$base_version" ]; then
  echo "Error: Could not determine version from pyproject.toml"
  exit 1
fi

# Beta tags should be cut against a plain GA base version (e.g. 0.37.0), not a
# version that already carries a pre-release suffix.
if ! echo "$base_version" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "Error: version in pyproject.toml ('$base_version') is not a plain GA version (X.Y.Z)."
  echo "Set the target GA version before tagging a beta."
  exit 1
fi

# Make sure we know about every existing beta tag before deciding the next number
git fetch "$ORIGIN" --tags --quiet >/dev/null 2>&1 || true

prefix="v${base_version}-beta."

# Find the highest existing beta number for the current base version.
latest=$(git tag --list "${prefix}*" \
  | sed "s|^${prefix}||" \
  | grep -E '^[0-9]+$' \
  | sort -n \
  | tail -n 1 || true)

if [ -z "$latest" ]; then
  next=1
else
  next=$((latest + 1))
fi

new_tag="${prefix}${next}"

# Double-check the tag does not already exist locally or remotely
if git rev-parse -q --verify "refs/tags/${new_tag}" >/dev/null; then
  echo "Error: tag ${new_tag} already exists locally."
  exit 1
fi
if git ls-remote --exit-code --tags "$ORIGIN" "refs/tags/${new_tag}" >/dev/null 2>&1; then
  echo "Error: tag ${new_tag} already exists on ${ORIGIN}."
  exit 1
fi

message="Beta pre-release ${new_tag} (base version ${base_version})"

git tag -a "$new_tag" -m "$message" "$COMMIT"
git push "$ORIGIN" tag "$new_tag"

echo ""
echo "Created and pushed beta tag: $new_tag"
echo "Base version (pyproject.toml): $base_version"
