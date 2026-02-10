"""Supabase client singleton."""

from supabase import create_client, Client
from loguru import logger

_client: Client | None = None


def get_supabase() -> Client:
    """Get the Supabase client singleton. Must call init_supabase first."""
    if _client is None:
        raise RuntimeError("Supabase not initialized. Call init_supabase() first.")
    return _client


def init_supabase(url: str, key: str) -> Client:
    """Initialize the Supabase client."""
    global _client
    if _client is not None:
        return _client
    _client = create_client(url, key)
    logger.info("Supabase client initialized")
    return _client
