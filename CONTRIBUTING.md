# Keeping the repository authoritative

## Before a change

Read the repository instructions and canonical requirements. Check the current branch, head, dirty files, open items, and current implementation status. Use the owner's latest explicit decisions; ask about unresolved business semantics rather than guessing.

## Change record

- Record a requirement change in docs/DECISIONS.md with its date and confirmed/proposed/open status.
- Update docs/REQUIREMENTS.md and affected acceptance checks in the same commit.
- Remove a resolved open item only after recording its resolution; retain superseded decisions for traceability.
- Update docs/STATUS.md with what actually exists and the evidence obtained.
- Use a branch and pull request for subsequent implementation work so its scope and verification can be reviewed. The initial documentation baseline may be committed directly to the new empty main branch.

## Publication review

Review the exact staged file list and content. Keep private runtime data, attachments, secrets, and real guest examples out of commits, issues, screenshots, CI output, and artifacts. Do not upload the original workbook.

## Evidence

For code changes, state the exact source revision, checks run, result, environment, and remaining limitations. Do not equate documentation checks, image builds, synthetic tests, deployment, or owner acceptance.

No licence has been selected. Do not add one automatically.
