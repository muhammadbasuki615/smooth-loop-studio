"""Lightweight plugin system.

Plugins are Python files placed in ``app/plugins/`` that define a subclass of
``BasePlugin``. They can register custom effects, overlay packs, or transitions.
"""

from __future__ import annotations

import importlib.util
import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .logger import get_logger

logger = get_logger(__name__)


class BasePlugin:
    """Base class all plugins must subclass."""

    name: str = "Unnamed Plugin"
    version: str = "0.1.0"
    author: str = "Unknown"
    description: str = ""

    def __init__(self, manager: "PluginManager") -> None:
        self.manager = manager

    def register(self) -> None:
        """Override to register effects, overlays, transitions, etc."""

    def unregister(self) -> None:
        """Override to clean up registrations."""


@dataclass
class PluginInfo:
    name: str
    path: Path
    instance: BasePlugin
    enabled: bool = True


class PluginManager:
    def __init__(self, plugin_dir: str | Path = "plugins") -> None:
        self.plugin_dir = Path(plugin_dir)
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.plugins: List[PluginInfo] = []
        self.custom_effects: Dict[str, Callable] = {}
        self.custom_overlays: Dict[str, Path] = {}
        self.custom_transitions: Dict[str, Callable] = {}

    def discover(self) -> List[Path]:
        return sorted(self.plugin_dir.glob("*.py"))

    def load_all(self) -> None:
        for p in self.discover():
            try:
                self.load(p)
            except Exception as e:
                logger.exception(f"Failed to load plugin {p}: {e}")

    def load(self, plugin_path: str | Path) -> Optional[PluginInfo]:
        path = Path(plugin_path)
        if not path.exists():
            return None
        spec = importlib.util.spec_from_file_location(path.stem, str(path))
        if not spec or not spec.loader:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        plugin_class = None
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BasePlugin) and obj is not BasePlugin:
                plugin_class = obj
                break
        if plugin_class is None:
            logger.warning(f"No BasePlugin subclass in {path}")
            return None
        instance = plugin_class(self)
        try:
            instance.register()
        except Exception as e:
            logger.exception(f"Plugin {plugin_class.__name__} register() failed: {e}")
        info = PluginInfo(name=instance.name, path=path, instance=instance)
        self.plugins.append(info)
        logger.info(f"Loaded plugin: {instance.name} v{instance.version}")
        return info

    def unload(self, name: str) -> None:
        for info in list(self.plugins):
            if info.name == name:
                try:
                    info.instance.unregister()
                except Exception as e:
                    logger.exception(f"Plugin unregister failed: {e}")
                self.plugins.remove(info)
                return

    # registration helpers ------------------------------------------------

    def register_effect(self, key: str, fn: Callable) -> None:
        self.custom_effects[key] = fn

    def register_overlay(self, key: str, path: str | Path) -> None:
        self.custom_overlays[key] = Path(path)

    def register_transition(self, key: str, fn: Callable) -> None:
        self.custom_transitions[key] = fn
