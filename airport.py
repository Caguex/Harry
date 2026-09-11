from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Airport:
    x: float = 50.0
    y: float = 50.0
    runway_heading: float = 90.0
    landing_radius: float = 6.5

    def distance(self, x: float, y: float) -> float:
        return math.hypot(x - self.x, y - self.y)
