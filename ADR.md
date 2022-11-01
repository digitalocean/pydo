# Architecture Decision Record for Pydo

## Title: Client to be Regenerated on digitalocean/openapi Commit instead of Release
## Date: 10/31/2022
## Description
The python-client-gen workflow will be triggered with an digitalocean/openapi commit instead of an digitalocean/openapi tagged release.
## Additional Context
We decided to not support releases in digitalocean/openapi repo because it would be too much of a maintenance for that repo. Therefore, to keep Pydo and our DO spec up to date with eachother, we will trigger the workflow on a commit to digitalocean/openapi main's branch.

## Title: Remove Third-Party Create PR Github Actions Step 
## Date: 10/31/2022
## Description
We will be removing the use of peter-evans/create-pull-request@v4 from our workflow because it caused our actions PR chekcs to choke. 
## Additional Context
The peter-evans/create-pull-request@v4 doc [here](https://github.com/peter-evans/create-pull-request/blob/main/docs/concepts-guidelines.md#triggering-further-workflow-runs) mentions that pull requests created by the action using the default GITHUB_TOKEN cannot trigger other workflows.