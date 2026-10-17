# DR-0001: spec structure and how ratification happens

**Status**: accepted by the merge of the pull request for issue #2.
**Rows**: all.

## Context

`spec/README.md` was a stub and the README table was DRAFT. Items 1-8 and 11 of
issue #3 grade against spec rows, and the CI structure check of issue #5 must be
able to follow the layout.

## Decision

One file per concern under `spec/` (`target-spec.md`, `channel-model.md`,
`test-configuration.md`, `dll-interface.md`), with row IDs `T-nn` in the target
table and one record per choice in `spec/decisions/NNNN-<slug>.md`. A row cites
the AIB 1.2 section it derives from, or says it is not defined there and why the
value was chosen. Every row carries a scope tag (CH / TC / BOTH). Ratification is
the review and merge of the pull request that closes issue #2; after it a row
changes only by a new decision record naming the row and the evidence.

## Alternatives rejected

- **One monolithic spec file.** A decision record could not be cited per row, and
  the file would be rewritten for every change.
- **Ratification by a separate sign-off step.** The repo's process is the
  review-and-merge flow; a second gate would be a mechanism with no owner here.
- **Copying AIB 1.2 tables into the spec.** The spec is a reference, not a
  claim, and copies no text or figures (CLAUDE.md). Numbers are used with a
  section citation.

## Consequences

The README DRAFT table and status line are replaced with a pointer to the ratified
spec in a follow-up edit after the merge, not in the pull request that ratifies it.
