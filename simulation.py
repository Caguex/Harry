from __future__ import annotations

import math
import random
from PySide6.QtCore import QObject, Signal

from aircraft import Aircraft, AircraftStatus
from airport import Airport
from stats import GameStats

class SimulationManager(QObject):
    changed = Signal()
    message = Signal(str)
    aircraft_added = Signal(object)
    aircraft_removed = Signal(str)
    selection_changed = Signal(object)

    WORLD_MIN = 0.0
    WORLD_MAX = 100.0
    DANGER_DISTANCE = 6.0
    COLLISION_DISTANCE = 2.2

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.airport = Airport()
        self.aircraft: list[Aircraft] = []
        self.stats = GameStats()
        self.selected: Aircraft | None = None
        self.paused = False
        self._spawn_accumulator = 0.0
        self._event_accumulator = 0.0
        self._danger_pairs: set[tuple[str, str]] = set()
        self.reset()

    def reset(self) -> None:
        self.aircraft.clear()
        self.stats = GameStats()
        self.selected = None
        self._spawn_accumulator = 0.0
        self._event_accumulator = 0.0
        self._danger_pairs.clear()
        for _ in range(4):
            self.spawn_aircraft()
        self.changed.emit()

    @property
    def level(self) -> int:
        return 1 + int(self.stats.elapsed_seconds // 55)

    @property
    def spawn_interval(self) -> float:
        return max(9.0, 25.0 - self.level * 2.0)

    def spawn_aircraft(self) -> Aircraft:
        side = random.choice(["top", "bottom", "left", "right"])
        margin = 4.0
        if side == "top":
            x, y = random.uniform(10, 90), margin
        elif side == "bottom":
            x, y = random.uniform(10, 90), 100 - margin
        elif side == "left":
            x, y = margin, random.uniform(10, 90)
        else:
            x, y = 100 - margin, random.uniform(10, 90)

        to_center = math.degrees(math.atan2(50 - y, 50 - x)) + 90
        heading = (to_center + random.uniform(-35, 35)) % 360
        prefix = random.choice(["AF", "BA", "LH", "EK", "IB", "KL", "QR"])
        callsign = f"{prefix}{random.randint(100, 9999):04d}"
        existing = {a.callsign for a in self.aircraft}
        while callsign in existing:
            callsign = f"{prefix}{random.randint(100, 9999):04d}"

        aircraft = Aircraft(
            callsign=callsign,
            x=x,
            y=y,
            altitude=random.choice([2200, 2800, 3500, 4200, 5000]),
            speed=random.randint(330, 520),
            heading=heading,
            fuel=random.uniform(45, 100),
        )
        self.aircraft.append(aircraft)
        self.stats.spawned += 1
        self.aircraft_added.emit(aircraft)
        self.changed.emit()
        return aircraft

    def select_aircraft(self, aircraft: Aircraft | None) -> None:
        for item in self.aircraft:
            item.selected = item is aircraft
        self.selected = aircraft
        self.selection_changed.emit(aircraft)
        self.changed.emit()

    def select_by_callsign(self, callsign: str) -> None:
        self.select_aircraft(next((a for a in self.aircraft if a.callsign == callsign), None))

    def update(self, dt: float) -> None:
        if self.paused:
            return
        self.stats.elapsed_seconds += dt
        self._spawn_accumulator += dt
        self._event_accumulator += dt

        for aircraft in list(self.aircraft):
            aircraft.update(dt)
            self._guide_landing(aircraft)

        self._handle_separation()
        self._remove_outside_aircraft()

        if self._spawn_accumulator >= self.spawn_interval:
            self._spawn_accumulator = 0.0
            self.spawn_aircraft()

        if self._event_accumulator >= max(16.0, 32.0 - self.level):
            self._event_accumulator = 0.0
            self._maybe_random_event()

        self.changed.emit()

    def _guide_landing(self, aircraft: Aircraft) -> None:
        if not aircraft.landing_requested:
            return

        dx = self.airport.x - aircraft.x
        dy = self.airport.y - aircraft.y

        desired_heading = (
                                  math.degrees(math.atan2(dy, dx)) + 90
                          ) % 360

        aircraft.set_heading(desired_heading)

        distance = self.airport.distance(
            aircraft.x,
            aircraft.y
        )

        aircraft.set_speed(220.0)

        approach_altitude = distance * 100.0

        # Limite maximale de l'altitude d'approche
        approach_altitude = min(
            approach_altitude,
            5000.0
        )
        # L'altitude ne peut jamais être négative
        approach_altitude = max(
            approach_altitude,
            0.0
        )
        aircraft.set_altitude(approach_altitude)

        if distance < self.airport.landing_radius * 2:
            # Dernière approche :
            # altitude cible = 0 m
            aircraft.set_altitude(0.0)

            # vitesse cible = 220 km/h
            aircraft.set_speed(220.0)

        if (
                distance <= self.airport.landing_radius
                and aircraft.altitude <= 50.0
                and aircraft.speed <= 230.0
        ):
            aircraft.altitude = 0.0
            aircraft.speed = 220.0

            self._successful_landing(aircraft)

    def _successful_landing(self, aircraft: Aircraft) -> None:
        self.stats.landed += 1
        self.stats.score += 100 + int(max(0.0, aircraft.fuel))
        self.stats.total_management_time += aircraft.age_seconds
        self.message.emit(f"✅ {aircraft.callsign} a atterri avec succès (+100).")
        self._remove_aircraft(aircraft)

    def _remove_aircraft(self, aircraft: Aircraft) -> None:
        if aircraft in self.aircraft:
            self.aircraft.remove(aircraft)
            self.aircraft_removed.emit(aircraft.callsign)
            if self.selected is aircraft:
                self.select_aircraft(None)

    def _remove_outside_aircraft(self) -> None:
        for aircraft in list(self.aircraft):
            if not (-8 <= aircraft.x <= 108 and -8 <= aircraft.y <= 108):
                if aircraft.landing_requested:
                    self.stats.score = max(0, self.stats.score - 25)
                    self.message.emit(f"⚠ {aircraft.callsign} a quitté la zone avant l'atterrissage.")
                self._remove_aircraft(aircraft)

    def _handle_separation(self) -> None:
        current_danger: set[tuple[str, str]] = set()
        crashed: set[str] = set()
        for i, a in enumerate(self.aircraft):
            for b in self.aircraft[i + 1:]:
                pair = tuple(sorted((a.callsign, b.callsign)))
                distance = a.distance_to(b)
                altitude_gap = abs(a.altitude - b.altitude)
                same_level = altitude_gap < 450
                if distance < self.COLLISION_DISTANCE and same_level:
                    crashed.update(pair)
                    continue
                if distance < self.DANGER_DISTANCE and same_level:
                    current_danger.add(pair)
                    if pair not in self._danger_pairs:
                        self.stats.danger_events += 1
                        self.stats.score = max(0, self.stats.score - 5)
                        self.message.emit(f"⚠ Proximité dangereuse : {a.callsign} / {b.callsign}")
                    if a.status == AircraftStatus.NORMAL:
                        a.status = AircraftStatus.WARNING
                    if b.status == AircraftStatus.NORMAL:
                        b.status = AircraftStatus.WARNING

        if crashed:
            self.stats.collisions += 1
            self.stats.score = max(0, self.stats.score - 250)
            self.message.emit("💥 Collision détectée ! Pénalité -250.")
            for aircraft in list(self.aircraft):
                if aircraft.callsign in crashed:
                    self._remove_aircraft(aircraft)
        self._danger_pairs = current_danger

    def _maybe_random_event(self) -> None:
        candidates = [a for a in self.aircraft if a.status != AircraftStatus.LANDING]
        if not candidates or random.random() > 0.62:
            return
        aircraft = random.choice(candidates)
        event = random.choice(["fuel", "technical", "weather"])
        if event == "fuel":
            aircraft.fuel = min(aircraft.fuel, random.uniform(8, 18))
            aircraft.status = AircraftStatus.EMERGENCY
            aircraft.event_message = "Fuite carburant"
            self.message.emit(f"🚨 {aircraft.callsign} : urgence carburant.")
        elif event == "technical":
            aircraft.technical_failure = True
            aircraft.status = AircraftStatus.EMERGENCY
            aircraft.event_message = "Panne technique"
            aircraft.set_speed(min(aircraft.target_speed, 300))
            self.message.emit(f"🚨 {aircraft.callsign} : panne technique.")
        else:
            delta = random.choice([-30, 30])
            aircraft.set_heading(aircraft.target_heading + delta)
            aircraft.status = AircraftStatus.WARNING
            aircraft.event_message = "Déviation météo"
            self.message.emit(f"🌧 {aircraft.callsign} : cellule météo, cap modifié de {delta:+d}°.")
