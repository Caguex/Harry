from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math


class AircraftStatus(str, Enum):
    NORMAL = "Normal"
    WARNING = "Attention"
    EMERGENCY = "Urgence"
    LANDING = "Approche"


def _normalize_heading(value: float) -> float:
    return value % 360.0


def _shortest_angle_delta(current: float, target: float) -> float:
    return (target - current + 180.0) % 360.0 - 180.0


@dataclass
class Aircraft:
    callsign: str
    x: float
    y: float
    altitude: float
    speed: float
    heading: float
    fuel: float
    target_altitude: float | None = None
    target_speed: float | None = None
    target_heading: float | None = None
    status: AircraftStatus = AircraftStatus.NORMAL
    event_message: str = ""
    age_seconds: float = 0.0
    selected: bool = False
    landing_requested: bool = False
    technical_failure: bool = False
    history: list[tuple[float, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.heading = _normalize_heading(self.heading)
        self.target_altitude = self.altitude if self.target_altitude is None else self.target_altitude
        self.target_speed = self.speed if self.target_speed is None else self.target_speed
        self.target_heading = self.heading if self.target_heading is None else _normalize_heading(self.target_heading)

    def set_heading(self, heading: float) -> None:
        self.target_heading = _normalize_heading(heading)

    def set_altitude(self, altitude: float) -> None:
        self.target_altitude = max(0.0, min(12000.0, altitude))

    def climb(self, meters: float = 500.0) -> None:
        self.set_altitude(self.target_altitude + meters)

    def descend(self, meters: float = 500.0) -> None:
        self.set_altitude(self.target_altitude - meters)

    def set_speed(self, speed: float) -> None:
        self.target_speed = max(140.0, min(950.0, speed))

    def request_landing(self) -> None:
        self.landing_requested = True
        self.status = AircraftStatus.LANDING

        # Vitesse d'approche souhaitée
        self.target_speed = 220.0

        # L'altitude sera calculée progressivement
        # par la simulation en fonction de la distance à la piste.
    def update(self, dt: float) -> None:
        self.age_seconds += dt
        self.history.append((self.x, self.y))
        if len(self.history) > 30:
            self.history.pop(0)

        heading_delta = _shortest_angle_delta(self.heading, self.target_heading)
        max_turn = 14.0 * dt
        if abs(heading_delta) <= max_turn:
            self.heading = self.target_heading
        else:
            self.heading = _normalize_heading(self.heading + math.copysign(max_turn, heading_delta))

        climb_rate = 2000.0 / 60.0
        altitude_delta = self.target_altitude - self.altitude
        step_alt = climb_rate * dt
        if abs(altitude_delta) <= step_alt:
            self.altitude = self.target_altitude
        else:
            self.altitude += math.copysign(step_alt, altitude_delta)

        # Accélération
        accel = 12.0  # km/h/s

        speed_delta = self.target_speed - self.speed
        step_speed = accel * dt

        if abs(speed_delta) <= step_speed:
            self.speed = self.target_speed
        else:
            self.speed += math.copysign(step_speed, speed_delta)

        # Déplacement sur le radar
        screen_speed = self.speed / 3600.0 * 2.5

        angle = math.radians(self.heading - 90.0)

        self.x += math.cos(angle) * screen_speed * dt
        self.y += math.sin(angle) * screen_speed * dt

        self.fuel = max(0.0, self.fuel - (0.020 + self.speed / 45000.0) * dt)
        if self.fuel < 12.0 and self.status != AircraftStatus.LANDING:
            self.status = AircraftStatus.EMERGENCY
            self.event_message = "Carburant critique"
        elif self.fuel < 25.0 and self.status == AircraftStatus.NORMAL:
            self.status = AircraftStatus.WARNING
            self.event_message = "Carburant faible"

    def distance_to(self, other: "Aircraft") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    @property
    def short_info(self) -> str:
        return f"Alt {self.altitude:.0f} m | V {self.speed:.0f} km/h | Fuel {self.fuel:.0f}%"
