"""Structured, filter-driven decomposition of Git patch files."""

from .categories import Category, MatchStrength
from .inventory import build_inventory

__all__ = ["Category", "MatchStrength", "build_inventory"]
