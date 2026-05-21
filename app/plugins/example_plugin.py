"""Example plugin - shows how to extend Smooth Loop Studio.

Drop this file into app/plugins/ and reload via the Plugin Manager panel.
"""

from app.core.plugin_api import BasePlugin


class HelloPlugin(BasePlugin):
    name = "Hello Plugin"
    version = "0.1.0"
    author = "Smooth Loop Studio"
    description = "Demo plugin that registers a custom 'sepia' effect filter."

    def register(self) -> None:
        def sepia_filter() -> str:
            # Return an ffmpeg filter chain fragment that any future
            # rendering pipeline can splice in.
            return (
                "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131"
            )
        self.manager.register_effect("sepia", sepia_filter)

    def unregister(self) -> None:
        self.manager.custom_effects.pop("sepia", None)
