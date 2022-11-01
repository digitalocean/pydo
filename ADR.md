# Architecture Decision Record for Pydo

## Title: Remove Third-Party Create PR Github Actions Step 
## Date: 10/31/2022
## Description
We will be removing the use of peter-evans/create-pull-request@v4 from our workflow because it caused our actions PR chekcs to choke. 
## Additional Context
The peter-evans/create-pull-request@v4 doc (here)[https://github.com/peter-evans/create-pull-request/blob/main/docs/concepts-guidelines.md#triggering-further-workflow-runs] mentions that pull requests created by the action using the default GITHUB_TOKEN cannot trigger other workflows.