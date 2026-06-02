"""Evidence vault module."""

from ego_data_core.vault.search import LocalSearchService, SearchResult, search_to_dict
from ego_data_core.vault.storage import InvalidVaultUriError, VaultStorage, build_vault_uri

__all__ = [
    "InvalidVaultUriError",
    "LocalSearchService",
    "SearchResult",
    "VaultStorage",
    "build_vault_uri",
    "search_to_dict",
]
