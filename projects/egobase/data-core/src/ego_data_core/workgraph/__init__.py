"""Work graph module."""

from ego_data_core.workgraph.automation_opportunities import (
    AutomationOpportunityRecord,
    AutomationOpportunityService,
    automation_opportunity_to_dict,
)
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
    "AutomationOpportunityRecord",
    "AutomationOpportunityService",
    "ProjectDiscoveryService",
    "ProjectRecord",
    "WorkItemExtractor",
    "WorkItemRecord",
    "automation_opportunity_to_dict",
    "project_to_dict",
    "work_item_to_dict",
]
