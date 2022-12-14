from omni.kit.scripting import BehaviorScript
from pxr import Sdf, UsdLux
import omni.kit.commands
import carb
import numpy
import math

class Light(BehaviorScript):
    def on_init(self):
        # Timeline Subscription
        timeline_stream = self.timeline.get_timeline_event_stream()
        self._timeline_sub = timeline_stream.create_subscription_to_pop(self._on_timeline_event)
        
        # Parameters
        self.recieved_data = False
        self.pitch = []
        self.total_duration = 0.0
        self.start_times = []
        self.curr_index = 1
        self.new_radius = 0
        self.prim = self._stage.GetPrimAtPath(self._prim_path)
        self._change_light_size(0)
        self.pitch_pos = int(self.prim.GetAttribute('Pitch').Get()) - 1

    def on_destroy(self):
        self._timeline_sub = None

    def on_update(self, current_time: float, delta_time: float):
        carb.log_info(f"Current Time: {current_time}")
        if not self.recieved_data:
            world = self._stage.GetPrimAtPath('/World')
            attr_name = 'pitch' + str(self.pitch_pos)
            self.pitch = world.GetAttribute(attr_name).Get()
            self.total_duration = world.GetAttribute('duration').Get()
            self.start_times = world.GetAttribute('beat_start_time').Get()
            self.recieved_data = True

        if self._is_time_close(current_time, self.start_times[self.curr_index]):
            self.new_radius = self._get_light_value()
            self.curr_index += 1

        light = self._lerp(self.new_radius, 0, self._get_time_diff(current_time))
        self._change_light_size(light)

    # Are we close between the current time and the next start time?
    def _is_time_close(self, a, b) -> bool:
        if a > b:
            return True
        return math.isclose(a, b, abs_tol=1e-2)

    def _lerp(self, a, b, c) -> float:
        c = numpy.clip(c, 0, 1)
        return (c * a) + ((1 - c) * b)

    def _get_time_diff(self, curr_time):
        top = self.start_times[self.curr_index] - curr_time
        bottom = (self.start_times[self.curr_index] - self.start_times[self.curr_index - 1])
        x = top / bottom
        return x

    def _get_light_value(self):
        pitch_value = self.pitch[self.curr_index] * 35
        return pitch_value 

    def _change_light_size(self, light_size):
        if not self.prim.IsValid():
            return
        if self.prim.IsA(UsdLux.DiskLight):
            omni.kit.commands.execute('ChangeProperty',
                prop_path=Sdf.Path(str(self._prim_path) + '.radius'),
                value=light_size,
                prev=0)
        elif self.prim.IsA(UsdLux.RectLight):
            omni.kit.commands.execute('ChangeProperty',
                prop_path=Sdf.Path(str(self._prim_path) + '.intensity'),
                value=light_size*10,
                prev=0)
            
    def _on_timeline_event(self, e: carb.events.IEvent):
        if e.type == int(omni.timeline.TimelineEventType.STOP):
            self._change_light_size(0)
            self.pitch = []
            self.total_duration = 0.0
            self.start_times = []
            self.curr_index = 1
            self.recieved_data = False
            
