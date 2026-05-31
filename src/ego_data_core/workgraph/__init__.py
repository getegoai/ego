"""Work graph module."""

from ego_data_core.workgraph.project_discovery import (
    ProjectDiscoveryService,
    ProjectRecord,
    project_to_dict,
)

__all__ = ["ProjectDiscoveryService", "ProjectRecord", "project_to_dict"]
