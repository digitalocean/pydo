#!/usr/bin/env bash

set -euo pipefail

ORIGIN=${ORIGIN:-origin}

# Bump defaults to patch. We provide friendly aliases
# for patch, minor and major
BUMP=${BUMP:-patch}
case "$BUMP" in
  feature | minor)
    BUMP="minor"
    ;;
  breaking | major)
    BUMP="major"
    ;;
  *)
    BUMP="patch"
    ;;
esac

# if [[ $(git status --porcelain) != "" ]]; then
#   echo "Error: repo is dirty. Run git status, clean repo and try again."
#   exit 1
# elif [[ $(git status --porcelain -b | grep -e "ahead" -e "behind") != "" ]]; then
#   echo "Error: repo has unpushed commits. Push commits to remote and try again."
#   exit 1
# fi  

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

poetry_version=$(poetry version)
version="${poetry_version:5}"
new_version="$(sembump --kind "$BUMP" "$version")"

poetry version "${new_version#v}"

echo ""