# Development history and source map

This import preserves the original **34 commits**, from 2026-05-29 to 2026-07-12,
without squashing, changing their contents, or inventing earlier public activity.
The project existed before its public launch. Original commit dates describe
development; they are not claims about when those commits became public.

## Two histories, one continuing mainline

| Input | Exact source commit | Treatment |
|---|---|---|
| Existing Ego implementation | `070ca1ea75cb43967286c3b86e9ac924584eb93d` | All 34 reachable commits retained |
| Existing public main | `cedb380906ac88c27ac1613485169a3a09c52aa1` | Both public commits retained; public README wording used as the base |

The histories are joined by a merge rather than replacing the public branch.
`website/` is retained byte-for-byte from the public-main input and is not updated
by the product-source migration. Normal development continues on `main` after
the merge. The independent EgoLink repository retains its own development history.

The working tree of the old local checkout was not copied wholesale. One local
registration-document edit and nine untracked control/research files were left
in their original workspace; they are not silently included in this import.
Runtime databases, vaults, credentials, virtual environments, and local logs
are not migration inputs.

## Historical milestones

The `history/` tags identify real old commits. They are navigation points, not
new product releases or a claim that each historical version has been rerun
with current dependencies. These tags are created during the public migration;
their names retain the dates of the original development milestones.

| Tag | Original commit | Original date | Meaning |
|---|---|---|---|
| `history/design-baseline-20260529` | [`ecb63c2`](https://github.com/getegoai/ego/commit/ecb63c2ec944bfbd5928f8b7d230d89bc82fecac) | 2026-05-29 | Initial design baseline |
| `history/data-core-ui-20260602` | [`f8583b3`](https://github.com/getegoai/ego/commit/f8583b31ce512f0bb4784e0f832cabde01529371) | 2026-06-02 | Local Web UI and the preceding evidence/brief foundation |
| `history/data-core-ocr-20260609` | [`53f3691`](https://github.com/getegoai/ego/commit/53f36919c34c767fc9a4ffe7e0885ffb66a2bcc6) | 2026-06-09 | Screenshot OCR enhancement, after manual capture and action dry-run |
| `history/portfolio-reset-20260712` | [`070ca1e`](https://github.com/getegoai/ego/commit/070ca1ea75cb43967286c3b86e9ac924584eb93d) | 2026-07-12 | Current local source baseline, after the multi-project workspace move |

The workspace move is commit `18f9d89` (2026-07-12). It moved the Data Core from
the repository root into `projects/egobase/data-core/`; most moved files kept
their contents. Use `git log --follow -- <file>` when examining a file across
that change. The complete chronology remains available in Git.

## Review and verification scope

- The retained source/public histories contain 36 commits and 259 unique blobs;
  all 259 blobs were text, totaling about 2.06 MB, with the largest about 57 KB.
- Gitleaks scanned all 36 commits with text-conversion and external diff drivers
  disabled and reported no leaks. A separate blob review checked credential,
  private-key, phone, email, local-path, network-address, and large-file candidates.
- One historical project-registration entry contains a former internal Git
  hostname without credentials. The current registration points to GitHub;
  the historical entry is retained as non-secret provenance. Original commit
  authorship metadata is preserved, including its original contact fields.
- Sample fixtures and dependency boundaries were reviewed. Pattern scans are
  limited evidence, not a guarantee that all possible privacy or rights issues
  have been excluded. No specific item requiring whole-history rewriting was found.

Current Data Core test and run results are recorded in the component's
[migration verification](../projects/egobase/data-core/docs/MIGRATION_VERIFICATION.md).
Historical versions have not been individually retested. Software checks do not
validate the complete EgoLink-to-EgoBase product loop or dedicated hardware.
