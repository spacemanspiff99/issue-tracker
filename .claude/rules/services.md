---
paths:
  - "src/issue_tracker/services/**"
  - "src/issue_tracker/repositories/**"
  - "src/issue_tracker/domain/**"
---

# Service, repository, and domain invariants (IT-1, IT-2)

- Services own business rules; repositories own persistence; routes/MCP only adapt I/O.
- Issues and sprints share one project-local sequence, displayed as 4-digit `NNNN` (`display_id`).
- Dependencies reject self-edges and cycles (`_path_exists`); keep that check in the service.
- Closing requires `originating_llm`; once `done` + `closed_at`, close metadata is immutable
  and `SprintService.add_issue` rejects the issue.
- Acceptance criteria are required on create; category checklists are project data.
- New issue mutations call `record_event(...)` (immutable `issue_events` history), then
  `_commit(message)`, which turns `IntegrityError` into `DomainError`.
- New behavior gets a test in `tests/unit/test_services.py` before web/MCP wiring.
- Procedure and checklist: `tracker-invariants` skill.
