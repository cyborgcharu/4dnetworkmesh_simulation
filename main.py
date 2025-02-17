import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum
import random
import math

class CommunicationType(Enum):
    BLE = "BLE"          # Short range (<10m)
    WIFI = "WIFI"        # Mid range (10-100m)
    GPS = "GPS"          # Long range (>100m)
    CUSTOM = "CUSTOM"    # Custom protocol (i.e. audio-based)

class NodeState(Enum):
    ACTIVE = "ACTIVE"
    OFFLINE = "OFFLINE"
    INTERMITTENT = "INTERMITTENT"

@dataclass
class Position:
    x: float
    y: float
    z: float = 0
    t: float = 0

    def distance_to(self, other: 'Position') -> float:
        return math.sqrt(
            (self.x - other.x)**2 +
            (self.y - other.y)**2 +
            (self.z - other.z)**2
        )

@dataclass
class NetworkPacket:
    source_id: int
    target_id: Optional[int]
    timestamp: float
    data: Dict
    hop_count: int = 0
    ttl: int = 10

@dataclass
class Node:
    id: int
    position: Position
    state: NodeState = NodeState.ACTIVE
    battery_level: float = 100.0
    protocols: Set[CommunicationType] = field(default_factory=lambda: {CommunicationType.BLE})
    memory: Dict = field(default_factory=dict)
    velocity: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))

    # ranges of distance for Communication Type protocols
    PROTOCOL_RANGES = {
        CommunicationType.BLE: 10.0,
        CommunicationType.WIFI: 100.0,
        CommunicationType.GPS: float('inf'),
        CommunicationType.CUSTOM: 50.0
    }

    # rates of battery consumption for Communication Type protocols
    BATTERY_DRAIN_RATES = {
        CommunicationType.BLE: 0.01,
        CommunicationType.WIFI: 0.05,
        CommunicationType.GPS: 0.1,
        CommunicationType.CUSTOM: 0.03
    }

    def update_position(self, dt: float):
        self.position.x += self.velocity[0] * dt
        self.position.y += self.velocity[1] * dt
        self.position.z += self.velocity[2] * dt
        self.position.t += dt

    def drain_battery(self, amount: float):
        actual_drain = amount * (0.8 + random.random() * 0.4)  # 20% variance
        self.battery_level = max(0.0, self.battery_level - actual_drain)

        # Probabilistic state changes based on battery level
        if self.battery_level == 0:
            self.state = NodeState.OFFLINE
        elif self.battery_level < 20:
            if random.random() < 0.3:  # 30% chance of going intermittent when low battery
                self.state = NodeState.INTERMITTENT

    def store_encounter(self, other_node: 'Node', timestamp: float):
        """Records when this node encounters another node"""
        if 'encounters' not in self.memory:
            self.memory['encounters'] = []
        self.memory['encounters'].append({
            'node_id': other_node.id,
            'timestamp': timestamp,
            'position': (other_node.position.x, other_node.position.y, other_node.position.z),
            'protocol': [p for p in self.protocols & other_node.protocols][0].value
        })

    def can_communicate_with(self, other: 'Node', protocol: CommunicationType) -> bool:
        if (protocol not in self.protocols or
            protocol not in other.protocols or
            self.state == NodeState.OFFLINE or
            other.state == NodeState.OFFLINE):
            return False

        # Intermittent nodes have sporadic connectivity
        if self.state == NodeState.INTERMITTENT or other.state == NodeState.INTERMITTENT:
            if random.random() > 0.3:  # 70% chance of failed communication
                return False

        distance = self.position.distance_to(other.position)

        # Add noise to effective range based on environmental factors
        effective_range = self.PROTOCOL_RANGES[protocol] * (0.9 + random.random() * 0.2)
        return distance <= effective_range

class NetworkMesh:
    def __init__(self, bounds: Tuple[float, float, float] = (1000.0, 1000.0, 100.0)):
        self.nodes: List[Node] = []
        self.time: float = 0.0
        self.packets: List[NetworkPacket] = []
        self.bounds = bounds

    def add_node(self, node: Node):
        # Initialize with random velocity
        max_speed = 5.0  # units per second
        node.velocity = (
            random.uniform(-max_speed, max_speed),
            random.uniform(-max_speed, max_speed),
            random.uniform(-max_speed/10, max_speed/10)  # Less vertical movement
        )
        self.nodes.append(node)

    def simulate_step(self, dt: float):
        self.time += dt
        active_nodes = 0
        connections = []

        for node in self.nodes:
            if node.state != NodeState.OFFLINE:
                # Update position
                node.update_position(dt)

                # Boundary checking - bounce off walls
                for i in range(3):
                    if node.position.x < 0 or node.position.x > self.bounds[0]:
                        node.velocity = (-node.velocity[0], node.velocity[1], node.velocity[2])
                    if node.position.y < 0 or node.position.y > self.bounds[1]:
                        node.velocity = (node.velocity[0], -node.velocity[1], node.velocity[2])
                    if node.position.z < 0 or node.position.z > self.bounds[2]:
                        node.velocity = (node.velocity[0], node.velocity[1], -node.velocity[2])

                # Drain battery based on active protocols
                total_drain = sum(Node.BATTERY_DRAIN_RATES[p] for p in node.protocols)
                node.drain_battery(total_drain * dt)

                # Check for connections
                if node.state == NodeState.ACTIVE:
                    active_nodes += 1
                    for other_node in self.nodes:
                        if node.id != other_node.id:
                            for protocol in CommunicationType:
                                if node.can_communicate_with(other_node, protocol):
                                    connections.append((node.id, other_node.id, protocol))
                                    node.store_encounter(other_node, self.time)
                                    break

        print(f"Step {int(self.time)}: Time={self.time:.1f}, Active nodes={active_nodes}, "
              f"Connections={len(connections)}, Battery levels: "
              f"min={min(n.battery_level for n in self.nodes):.1f}, "
              f"avg={sum(n.battery_level for n in self.nodes)/len(self.nodes):.1f}")

class Simulation:
    def __init__(self, size: Tuple[float, float, float] = (1000.0, 1000.0, 100.0)):
        self.mesh = NetworkMesh(bounds=size)
        self.size = size

    def generate_random_nodes(self, count: int):
        for i in range(count):
            position = Position(
                x=random.uniform(0, self.size[0]),
                y=random.uniform(0, self.size[1]),
                z=random.uniform(0, self.size[2]),
                t=0.0
            )

            # Assign protocols with different probabilities
            protocols = {CommunicationType.BLE}  # All nodes have BLE
            if random.random() < 0.7:  # 70% chance of having WiFi
                protocols.add(CommunicationType.WIFI)
            if random.random() < 0.3:  # 30% chance of having GPS
                protocols.add(CommunicationType.GPS)
            if random.random() < 0.2:  # 20% chance of having custom protocol
                protocols.add(CommunicationType.CUSTOM)

            node = Node(
                id=i,
                position=position,
                protocols=protocols,
                state=NodeState.ACTIVE
            )
            self.mesh.add_node(node)

    def run(self, steps: int, dt: float = 1.0):
        for step in range(steps):
            self.mesh.simulate_step(dt)

if __name__ == '__main__':
    sim = Simulation(size=(200.0, 200.0, 50.0))
    sim.generate_random_nodes(20)
    sim.run(steps=100)
