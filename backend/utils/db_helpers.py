"""Utility to detect Supabase table-not-found errors and return graceful defaults."""


def is_table_missing(error_str: str) -> bool:
    """Check if an error is caused by a missing table (PGRST205)."""
    return "PGRST205" in str(error_str) or "Could not find the table" in str(error_str)
