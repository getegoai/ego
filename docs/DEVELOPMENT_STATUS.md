# Ego Data Core Development Status

**Last updated**: 2026-05-29  
**Branch**: `main`  
**Current phase**: repository bootstrap  
**Active issue**: none; next recommended issue is `EDC-000`

## Collaboration Model

We will treat `docs/Ego_Data_Core_v0.1_Codex_Development_Taskbook.md` as the execution source of truth. Product and architecture docs define intent and constraints; the taskbook defines implementation order.

Working agreement:

1. Work on one EDC issue at a time.
2. Before coding, state the issue, acceptance criteria, expected files, and test plan.
3. Keep each commit atomic: one coherent change, one reason.
4. Update this status file when an issue starts, completes, blocks, or changes scope.
5. After each issue, report commit hash, changed areas, tests run, and remaining risks.
6. If docs conflict, prefer the taskbook for v0.1 delivery and record the decision here.

## Git Rules

Commit style:

- `chore: ...` for repo, docs, tooling, and maintenance.
- `EDC-000: ...` for issue implementation commits.
- `test: ...` only when the commit is test-only.
- `fix: ...` for narrow corrections after a completed issue.

Atomic commit examples:

- `EDC-000: add FastAPI health skeleton`
- `EDC-001: add SQLite migration runner`
- `EDC-006: scan files into raw object records`

Each implementation commit should include the relevant tests unless splitting is clearer.

## Progress Snapshot

| Area | Status | Notes |
|---|---|---|
| Git repository | Done | Initialized on `main`; design baseline committed. |
| Design docs | Done | Existing v0.1 docs committed unchanged. |
| Project skeleton | Not started | Next: `EDC-000`. |
| Database and migrations | Not started | `EDC-001`; schema already validates in SQLite memory check. |
| ID/config/test foundation | Not started | `EDC-002`, `EDC-003`, `EDC-029`. |
| Audit/source/vault scan | Not started | M1 chain after DB foundation. |
| Document parsing | Not started | `EDC-008`. |
| Model/router/enhancement | Not started | RuleBasedAdapter first; Ollama optional. |
| Work graph and brief | Not started | Needed for demo value chain. |
| CLI/demo | Not started | CLI before UI for early demo speed. |

## Near-Term Execution Order

```text
EDC-000 -> EDC-001 -> EDC-002 -> EDC-003 -> EDC-029 -> EDC-028
  -> EDC-004 -> EDC-005 -> EDC-006 -> EDC-007
  -> EDC-008 -> EDC-010 -> EDC-011 -> EDC-013
  -> EDC-014/EDC-015 minimal -> EDC-017 -> EDC-018 -> EDC-025 -> EDC-026
```

## Current Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-05-29 | Use taskbook priority when product and task docs differ. | The taskbook is already issue-shaped and better for incremental delivery. |
| 2026-05-29 | CLI and Markdown brief come before polished UI. | Fastest path to a reliable evidence-backed demo. |
| 2026-05-29 | RuleBasedAdapter is required before optional model adapters. | Demo must run without Ollama or cloud APIs. |

## Status Report Format

At the end of each work unit, Codex should report:

- Current issue and status.
- Commit hash and message.
- Files changed.
- Tests run and result.
- Any risks, blockers, or doc conflicts.
- Recommended next issue.
