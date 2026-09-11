from dataclasses import dataclass


@dataclass
class GameStats:
    score: int = 0
    landed: int = 0
    collisions: int = 0
    danger_events: int = 0
    spawned: int = 0
    elapsed_seconds: float = 0.0
    total_management_time: float = 0.0

    @property
    def average_management_time(self) -> float:
        if self.landed == 0:
            return 0.0
        return self.total_management_time / self.landed