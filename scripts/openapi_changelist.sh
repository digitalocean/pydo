#!/usr/bin/env bash

# set -x # Uncomment to debug
set -e

if [ "$#" -ne 2 ]; then
    printf "Exactly two arguments are required.\n\n$(basename "$0") <current_sha> <target_sha>\n"
    exit 1
fi

current_sha=$1
target_sha=$2

# get_commit_date <sha>
# Returns the date the given sha was merged.
function get_commit_date(){
   
    if [ -z $1 ]; then
        echo "get_commit_date() requires 1 argument: <sha>"
        exit 1
    fi

    gh pr --repo digitalocean/openapi list \
        -s merged --json number,title,mergedAt,labels,mergeCommit | \
            jq -r --arg sha $1 \
            '.[] | select(.mergeCommit.oid | startswith($sha)) | .mergedAt'
}

current_commit_date=$(get_commit_date $1)
test ${#current_commit_date} -eq 20 || (echo "$LINENO: Unexpected value for current_commit_date: $current_commit_date" && exit 1) 

target_commit_date=$(get_commit_date $2)
test ${#target_commit_date} -eq 20 || (echo "$LINENO: Unexpected value for target_commit_date: $target_commit_date" && exit 1) 

echo "## Changelist"
echo 
echo "Current commit: digitalocean/openapi@$current_sha ($current_commit_date)"
echo "Target commit: digitalocean/openapi@$target_sha ($target_commit_date)"
echo
gh pr --repo digitalocean/openapi list \
    -s merged --json number,title,mergedAt,labels \
    --jq '[.[] |  {"number": .number, "title": .title, "mergedAt": .mergedAt, "labels": ([.labels[] | .name] | join("|"))}]' | \
    jq --arg prev $current_commit_date --arg current $target_commit_date \
        '[.[] | select(.mergedAt > $prev) | select(.mergedAt <= $current)]' | \
        jq -r '.[] | select(.labels | contains("ignore-for-changelog") | not) | "* digitalocean/openapi#\(.number): \( .title) - \(.mergedAt) [\(.labels)]"'