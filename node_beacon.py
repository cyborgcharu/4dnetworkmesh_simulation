# Low-power Bluetooth beacon node

from node import *

@dataclass
class BeaconNode(Node):
    wakeup_interval: float = 0

    def update_state(self, time_seconds: float):
        if (time_seconds % self.wakeup_interval) == 0:
            self.state = NodeState.ACTIVE
        elif self.state != NodeState.OFFLINE:
            self.state = NodeState.SLEEP
