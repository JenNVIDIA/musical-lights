from .spotify import *
import omni.ui as ui
from datetime import datetime


class LightSyncWindow(ui.Window):
    def __init__(self, title, **kwargs) -> None:
        super().__init__(title, **kwargs)

        # Define Models
        self._auth_token_model = ui.SimpleStringModel("")
        self._access_code_model = ui.SimpleStringModel("")
        self._track_model = ui.SimpleStringModel("")

        # Build UI
        self._build()

    def _build(self):
        with self.frame:
            with ui.VStack(spacing=5,height=0, style={'background_color': ui.color('#000E3AFF')}):
                with ui.HStack():
                    self._build_labels()
                    self._build_stringfields()
                self._build_buttons()
                self._build_expire_labels()
    
    # Build Labels that tell user when their Authentication Expires
    def _build_expire_labels(self):
        with ui.HStack():
            self.expire_label = ui.Label("Auth Token will expire in: ", visible=False)
            self.expire_time = ui.Label("", visible=False)

    # Build Fields where user inputs track id
    def _build_stringfields(self):
        with ui.VStack(spacing=5):
            ui.StringField(model=self._access_code_model)
            ui.StringField(model=self._auth_token_model)
            ui.StringField(model=self._track_model)

    # Builds Labels for each String Field
    def _build_labels(self):
        with ui.VStack(width=0,spacing=5):
            ui.Label("Auth Code: ")
            ui.Label("Auth Token: ")
            ui.Label("Track: ")

    # Builds buttons 
    def _build_buttons(self):
        with ui.VStack():
            ui.Button("Get Access Code", clicked_fn=self.get_access_code)
            ui.Button("Get Auth Token", clicked_fn=self.get_auth_token)
            ui.Button("Play", clicked_fn=self.run_webhook_spotify)

    def run_webhook_spotify(self):
        track = self._track_model.get_value_as_string()
        # auth_token = self._auth_token_model.get_value_as_string()
        startup_spotify_sync(track, self._web_data._auth_token)

    def get_access_code(self):
        self._web_data = WebData()
        code = self._web_data.get_access_code()
        if not code:
            self._access_code_model.set_value("Clear")

    def get_auth_token(self):
        token = self._web_data.get_access_token()
        if not token:
            self._auth_token_model.set_value("Clear")
        self.set_expire_time()

    # TODO: Can we set an alarm?
    def set_expire_time(self):
        curr_time = datetime.now()
        expire_time = str(curr_time.hour + 1) + ":" + str(curr_time.minute) + ":" + str(curr_time.second)
        self.expire_time.text = expire_time
        self.expire_label.visible = True
        self.expire_time.visible = True

