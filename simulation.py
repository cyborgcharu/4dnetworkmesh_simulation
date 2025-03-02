# Main simulation engine.
# 
# Its role is only to apply the properties of nodes, and render the graph,
# but not to implement any particular strategy or protocol, which is going
# to be implmeneted on top of it.

import numpy as np
import random
import math
import networkx as nx
import matplotlib.pyplot as plt

from simulation_types import *
from node import *
from node_beacon import BeaconNode

class NetworkMesh:
    def __init__(self, bounds: Tuple[float, float, float] = (1000.0, 1000.0, 100.0)):
        self.nodes: List[Node] = []
        self.time_seconds: float = 0.0
        self.packets: List[NetworkPacket] = []
        self.bounds = bounds

    def add_node(self, node: Node):
        # Initialize with random velocity
        max_speed_meters_per_second = 2.0  # meters per second
        node.velocity_meters_per_second = (
            random.uniform(-max_speed_meters_per_second, max_speed_meters_per_second),
            random.uniform(-max_speed_meters_per_second, max_speed_meters_per_second),
            random.uniform(-max_speed_meters_per_second/10, max_speed_meters_per_second/10)
        )
        self.nodes.append(node)

    def simulate_step(self, dt_seconds: float):
        self.time_seconds += dt_seconds
        active_nodes = 0
        connections = []

        for node in self.nodes:
            # Update position
            node.update_position(dt_seconds)

            # Boundary checking
            if node.position_meters.x < 0 or node.position_meters.x > self.bounds[0]:
                node.velocity_meters_per_second = (
                    -node.velocity_meters_per_second[0],
                    node.velocity_meters_per_second[1],
                    node.velocity_meters_per_second[2]
                )
            if node.position_meters.y < 0 or node.position_meters.y > self.bounds[1]:
                node.velocity_meters_per_second = (
                    node.velocity_meters_per_second[0],
                    -node.velocity_meters_per_second[1],
                    node.velocity_meters_per_second[2]
                )
            if node.position_meters.z < 0 or node.position_meters.z > self.bounds[2]:
                node.velocity_meters_per_second = (
                    node.velocity_meters_per_second[0],
                    node.velocity_meters_per_second[1],
                    -node.velocity_meters_per_second[2]
                )

            if isinstance(node, BeaconNode):
                node.update_state(self.time_seconds)

            if (node.state != NodeState.OFFLINE and
                node.state != NodeState.SLEEP):
                # Drain battery based on active protocols
                total_drain = sum(Node.BATTERY_DRAIN_RATES[p] for p in node.protocols)
                node.drain_battery(total_drain * dt_seconds)

        for node in self.nodes:
            if (node.state != NodeState.OFFLINE and
                node.state != NodeState.SLEEP):
                # Check for connections
                if (node.state == NodeState.ACTIVE or
                    node.state == NodeState.INTERMITTENT):
                    active_nodes += 1
                    for other_node in self.nodes:
                        if node.id != other_node.id:
                            for protocol in CommunicationType:
                                if node.can_communicate_with(other_node, protocol):
                                    connections.append((node.id, other_node.id, protocol))
                                    node.store_encounter(other_node, self.time_seconds)
                                    break

        print(f"Step {int(self.time_seconds)}: Time={self.time_seconds:.1f}, Active nodes={active_nodes}, "
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
            CommunicationType.WIFI: '#9467bd',   # Purple
            CommunicationType.UPLINK: '#2ca02c', # Green
        }

        # Node state colors
        self.state_colors = {
            NodeState.ACTIVE: '#2ecc71',         # Green
            NodeState.SLEEP: '#9abddc',          # Light Blue
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

            self.pos[node.id] = (node.position_meters.x, node.position_meters.y)

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

        plt.title(f'Network Mesh State (t={self.mesh.time_seconds:.1f}s)')
        plt.axis('off')
        plt.tight_layout()

        plt.draw()
        plt.pause(0.1)

class Simulation:
    def __init__(self, size_meters: Tuple[float, float, float] = (100.0, 100.0, 10.0)):
        self.mesh = NetworkMesh(bounds=size_meters)
        self.size_meters = size_meters
        self.visualizer = None

    def generate_random_nodes(self, count: int):
        for i in range(count):
            position_meters = Position(
                x=random.uniform(0, self.size_meters[0]),
                y=random.uniform(0, self.size_meters[1]),
                z=random.uniform(0, self.size_meters[2]),
                t=0.0
            )

            # Assign protocols with different probabilities
            protocols = {CommunicationType.BLE}  # All nodes have BLE
            if random.random() < 0.7:  # 70% chance of having WiFi
                protocols.add(CommunicationType.WIFI)
            if random.random() < 0.3:  # 30% chance of having an up-link to Internet or local network
                protocols.add(CommunicationType.UPLINK)

            # 60% chance of being a Low-Power node
            if random.random() < 0.6:
                wakeup_interval = math.floor(random.uniform(2, 6))
                node = BeaconNode(
                    id=i,
                    position_meters=position_meters,
                    protocols=protocols,
                    state=NodeState.ACTIVE,
                    wakeup_interval=wakeup_interval
                )
            else:
                node = Node(
                    id=i,
                    position_meters=position_meters,
                    protocols=protocols,
                    state=NodeState.ACTIVE
                )
            self.mesh.add_node(node)

    def run(self, steps: int, dt_seconds: float = 1.0, visualize: bool = True):
        if visualize:
            self.visualizer = NetworkVisualizer(self.mesh)
            plt.ion()

        for step in range(steps):
            connections = self.mesh.simulate_step(dt_seconds)

            if visualize and step % 1 == 0:  # Update visualization every step
                self.visualizer.update_graph(connections)
                self.visualizer.draw()

        if visualize:
            plt.ioff()
            plt.show()
