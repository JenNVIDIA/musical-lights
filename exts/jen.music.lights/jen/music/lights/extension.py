import omni.ext
from .window import LightSyncWindow

class MyExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._window = LightSyncWindow("Spotify Sync with Lights", width=250, height=250)

    def on_shutdown(self):
        self._window.destroy()
