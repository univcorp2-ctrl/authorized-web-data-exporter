# GitHub Actions workflow creation permission note

The automation successfully committed the application, tests, docs, and workflow templates, but creating files under `.github/workflows/` can be rejected by GitHub when the automation token does not have workflow-file write permission.

The intended workflow files are preserved here:

- `docs/workflows/ci.yml`
- `docs/workflows/export.yml`

They are exact templates for:

- lint and test CI
- manual authorized export with artifact upload

When the GitHub token or GitHub App installation has permission to write workflow files, these files should be placed under `.github/workflows/` with the same filenames.
