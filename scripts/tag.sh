#!/usr/bin/env bash

set -eo pipefail

ORIGIN=${ORIGIN:-origin}

if [[ $(git status --porcelain) != "" ]]; then
  echo "Error: repo is dirty. Run git status, clean repo and try again."
  exit 1
elif [[ $(git status --porcelain -b | grep -e "ahead" -e "behind") != "" ]]; then
  echo "Error: repo has unpushed commits. Push commits to remote and try again."
  exit 1
fi  

poetry_version=$(poetry version)
tag="v${poetry_version:5}"

git tag -m "release $tag" -a "$tag" $COMMIT && git push "$ORIGIN" tag "$tag"

echo ""