"""
Configuration management for PDF Research Assistant.

This module handles environment variables, API keys, and application settings.
"""

from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings"] 