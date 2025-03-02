# Main class of nodes to allow defining sub-classes
# that implement a particular type of node.

import random

from simulation_types import *

@dataclass
class Node:
    id: int
    # Meters
    position_meters: Position
    state: NodeState = NodeState.ACTIVE
    battery_level: float = 100.0
    protocols: Set[CommunicationType] = field(default_factory=lambda: {CommunicationType.BLE})
    memory: Dict = field(default_factory=dict)
    # Meter per second
    velocity_meters_per_second: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))

    # ranges of distance for protocols
    PROTOCOL_RANGES = {
        CommunicationType.BLE: 10.0,
        CommunicationType.WIFI: 100.0,
        CommunicationType.UPLINK: float('inf'),
    }

    # rates of battery consumption for protocols
    BATTERY_DRAIN_RATES = {
        CommunicationType.BLE: 0.01,
        CommunicationType.WIFI: 0.05,
        CommunicationType.UPLINK: 0.0,
    }

    def update_position(self, dt_seconds: float):
        self.position_meters.x += self.velocity_meters_per_second[0] * dt_seconds
        self.position_meters.y += self.velocity_meters_per_second[1] * dt_seconds
        self.position_meters.z += self.velocity_meters_per_second[2] * dt_seconds
        self.position_meters.t += dt_seconds

    def drain_battery(self, amount: float):
        actual_drain = amount * (0.8 + random.random() * 0.4)  # 20% variance
        self.battery_level = max(0.0, self.battery_level - actual_drain)

        # Probabilistic state changes based on battery level
        if self.battery_level == 0:
            self.state = NodeState.OFFLINE
        elif self.battery_level < 20:
            if random.random() < 0.3:  # 30% chance of going intermittent when low battery
                self.state = NodeState.INTERMITTENT

    def store_encounter(self, other_node: 'Node', timestamp_seconds: float):
        """Records when this node encounters another node"""
        if 'encounters' not in self.memory:
            self.memory['encounters'] = []
        self.memory['encounters'].append({
            'node_id': other_node.id,
            'timestamp_seconds': timestamp_seconds,
            'position_meters': (other_node.position_meters.x, other_node.position_meters.y, other_node.position_meters.z),
            'protocol': [p for p in self.protocols & other_node.protocols][0].value
        })

    def can_communicate_with(self, other: 'Node', protocol: CommunicationType) -> bool:
        if (protocol not in self.protocols or
            protocol not in other.protocols or
            self.state == NodeState.OFFLINE or
            other.state == NodeState.OFFLINE or
            self.state == NodeState.SLEEP or
            other.state == NodeState.SLEEP):
            return False

        # Intermittent nodes have sporadic connectivity
        if self.state == NodeState.INTERMITTENT or other.state == NodeState.INTERMITTENT:
            if random.random() > 0.3:  # 70% chance of failed communication
                return False

        distance = self.position_meters.distance_to(other.position_meters)

        # Add noise to effective range based on environmental factors
        effective_range = self.PROTOCOL_RANGES[protocol] * (0.9 + random.random() * 0.2)
        return distance <= effective_range
