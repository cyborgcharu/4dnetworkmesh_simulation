# Definition of all the types all across the simulatoin

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math

class CommunicationType(Enum):
    BLE = "BLE"          # Short range (<10m)
    WIFI = "WIFI"        # Mid range (10-100m)
    UPLINK = "UPLINK"    # Communication to a wired network, not subject to limitations

class NodeState(Enum):
    ACTIVE = "ACTIVE"
    SLEEP = "SLEEP"
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
    timestamp_seconds: float
    data: Dict
    hop_count: int = 0
    ttl: int = 10
