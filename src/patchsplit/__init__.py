"""Structured, filter-driven decomposition of an applied Git patch."""

from .categories import Category, MatchStrength
from .inventory import build_inventory

__all__ = ["Category", "MatchStrength", "build_inventory"]
