from __future__ import annotations

from enum import StrEnum


class IssueStatus(StrEnum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in-progress"
    DONE = "done"
    CANCELLED = "cancelled"


class SprintStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    CLOSED = "closed"


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in-progress"
    DONE = "done"
