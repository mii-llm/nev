"""Compatibility imports for the original Qwen3 backend module."""
from .decoder import cast_parameters, default_attn, load_backbone, replicate_cache, save_backbone

__all__ = ["cast_parameters", "default_attn", "load_backbone", "replicate_cache", "save_backbone"]
