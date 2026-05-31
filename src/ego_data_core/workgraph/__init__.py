"""Work graph module."""

from ego_data_core.workgraph.extractors import (
    WorkItemExtractor,
    WorkItemRecord,
    work_item_to_dict,
)
from ego_data_core.workgraph.project_discovery import (
    ProjectDiscoveryService,
    ProjectRecord,
    project_to_dict,
)

__all__ = [
    "ProjectDiscoveryService",
    "ProjectRecord",
    "WorkItemExtractor",
    "WorkItemRecord",
    "project_to_dict",
    "work_item_to_dict",
]
