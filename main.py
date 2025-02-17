import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum
import random
import math
import networkx as nx
import matplotlib.pyplot as plt

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

    # ranges of distance for protocols
    PROTOCOL_RANGES = {
        CommunicationType.BLE: 10.0,
        CommunicationType.WIFI: 100.0,
        CommunicationType.GPS: float('inf'),
        CommunicationType.CUSTOM: 50.0
    }

    # rates of battery consumption for protocols
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
            random.uniform(-max_speed/10, max_speed/10)
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

                # Boundary checking
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
                elif active_nodes > 0:
                    active_nodes -= 1

        print(f"Step {int(self.time)}: Time={self.time:.1f}, Active nodes={active_nodes}, "
              f"Connections={len(connections)}, Battery levels: "
              f"min={min(n.battery_level for n in self.nodes):.1f}, "
              f"avg={sum(n.battery_level for n in self.nodes)/len(self.nodes):.1f}")
        
        return connections

class NetworkVisualizer:
    def __init__(self, mesh: NetworkMesh):
        self.mesh = mesh
        self.G = nx.Graph()
        self.pos = {}
        self.node_colors = []
        self.edge_colors = []
        
        self.fig = plt.figure(figsize=(12, 8))
        
        # Color mapping for different protocols
        self.protocol_colors = {
            CommunicationType.BLE: '#1f77b4',    # Blue
            CommunicationType.WIFI: '#2ca02c',   # Green
            CommunicationType.GPS: '#ff7f0e',    # Orange
            CommunicationType.CUSTOM: '#9467bd'  # Purple
        }
        
        # Node state colors
        self.state_colors = {
            NodeState.ACTIVE: '#2ecc71',         # Green
            NodeState.OFFLINE: '#e74c3c',        # Red
            NodeState.INTERMITTENT: '#f1c40f'    # Yellow
        }

    def update_graph(self, connections):
        """Updates the graph based on current mesh state"""
        self.G.clear()
        self.node_colors = []
        self.edge_colors = []
        

        for node in self.mesh.nodes:
            self.G.add_node(node.id)

            self.pos[node.id] = (node.position.x, node.position.y)
            
            self.node_colors.append(self.state_colors[node.state])
            
            self.G.nodes[node.id]['battery'] = node.battery_level
            self.G.nodes[node.id]['protocols'] = [p.value for p in node.protocols]
            self.G.nodes[node.id]['state'] = node.state.value


        for source_id, target_id, protocol in connections:
            self.G.add_edge(source_id, target_id)
            self.edge_colors.append(self.protocol_colors[protocol])

    def draw(self):
        """Draws the current state of the network"""
        plt.clf()
        

        nx.draw_networkx_nodes(self.G, self.pos, 
                             node_color=self.node_colors,
                             node_size=300)
        
        if self.edge_colors:  
            nx.draw_networkx_edges(self.G, self.pos,
                                 edge_color=self.edge_colors,
                                 width=2, alpha=0.5)
        
        labels = {node: f"Node {node}\n{self.G.nodes[node]['battery']:.0f}%" 
                 for node in self.G.nodes()}
        nx.draw_networkx_labels(self.G, self.pos, labels, font_size=8)
        
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', 
                      markerfacecolor=color, label=state.value, markersize=10)
            for state, color in self.state_colors.items()
        ] + [
            plt.Line2D([0], [0], color=color, label=proto.value)
            for proto, color in self.protocol_colors.items()
        ]
        plt.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1))
        
        plt.title(f'Network Mesh State (t={self.mesh.time:.1f}s)')
        plt.axis('off')
        plt.tight_layout()
        
        plt.draw()
        plt.pause(0.1) 

class Simulation:
    def __init__(self, size: Tuple[float, float, float] = (1000.0, 1000.0, 100.0)):
        self.mesh = NetworkMesh(bounds=size)
        self.size = size
        self.visualizer = None

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

    def run(self, steps: int, dt: float = 1.0, visualize: bool = True):
        if visualize:
            self.visualizer = NetworkVisualizer(self.mesh)
            plt.ion()
        
        for step in range(steps):
            connections = self.mesh.simulate_step(dt)
            
            if visualize and step % 10 == 0:  # Update visualization every 10 steps
                self.visualizer.update_graph(connections)
                self.visualizer.draw()
        
        if visualize:
            plt.ioff()  
            plt.show() 

if __name__ == '__main__':
    sim = Simulation(size=(25.0, 25.0, 10.0))
    
    sim.generate_random_nodes(20)
    
    sim.run(steps=100, dt=1.0, visualize=True)