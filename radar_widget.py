from __future__ import annotations

import math
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPolygonF
from PySide6.QtWidgets import QWidget

from aircraft import AircraftStatus
from simulation import SimulationManager


class RadarWidget(QWidget):
    aircraft_clicked = Signal(object)

    def __init__(self, simulation: SimulationManager, parent=None) -> None:
        super().__init__(parent)
        self.simulation = simulation
        self.setMinimumSize(620, 620)
        self.setMouseTracking(True)
        self.setToolTip("Cliquez sur un avion pour le sélectionner")
        simulation.changed.connect(self.update)

    def _world_to_screen(self, x: float, y: float) -> QPointF:
        pad = 30.0
        usable_w = max(1.0, self.width() - 2 * pad)
        usable_h = max(1.0, self.height() - 2 * pad)
        return QPointF(pad + x / 100.0 * usable_w, pad + y / 100.0 * usable_h)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#071923"))

        center = self._world_to_screen(50, 50)
        radius = min(self.width(), self.height()) * 0.42
        grid_pen = QPen(QColor(55, 130, 145, 120), 1)
        painter.setPen(grid_pen)
        for factor in (0.25, 0.5, 0.75, 1.0):
            r = radius * factor
            painter.drawEllipse(center, r, r)
        painter.drawLine(QPointF(center.x() - radius, center.y()), QPointF(center.x() + radius, center.y()))
        painter.drawLine(QPointF(center.x(), center.y() - radius), QPointF(center.x(), center.y() + radius))
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            end = QPointF(center.x() + math.cos(rad) * radius, center.y() + math.sin(rad) * radius)
            painter.drawLine(center, end)

        # Airport / runway
        airport = self._world_to_screen(self.simulation.airport.x, self.simulation.airport.y)
        painter.setPen(QPen(QColor("#f4f5f7"), 4))
        runway_len = 42
        painter.drawLine(airport.x() - runway_len, airport.y(), airport.x() + runway_len, airport.y())
        painter.setPen(QPen(QColor("#32d296"), 2))
        painter.drawEllipse(airport, 18, 18)
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        painter.drawText(airport + QPointF(12, -14), "PISTE")

        # Trajectoires
        for aircraft in self.simulation.aircraft:
            if len(aircraft.history) > 1:
                painter.setPen(QPen(QColor(80, 200, 220, 70), 1))
                points = [self._world_to_screen(x, y) for x, y in aircraft.history]
                painter.drawPolyline(QPolygonF(points))

        for aircraft in self.simulation.aircraft:
            self._draw_aircraft(painter, aircraft)

    def _draw_aircraft(self, painter: QPainter, aircraft) -> None:
        point = self._world_to_screen(aircraft.x, aircraft.y)
        if aircraft.status == AircraftStatus.EMERGENCY:
            color = QColor("#ff4d67")
        elif aircraft.status == AircraftStatus.WARNING:
            color = QColor("#ffb020")
        elif aircraft.status == AircraftStatus.LANDING:
            color = QColor("#32d296")
        else:
            color = QColor("#37d5f4")

        painter.save()
        painter.translate(point)
        painter.rotate(aircraft.heading)
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color))
        shape = QPolygonF([
            QPointF(0, -10), QPointF(4, -1), QPointF(11, 2), QPointF(11, 5),
            QPointF(3, 3), QPointF(3, 10), QPointF(-3, 10), QPointF(-3, 3),
            QPointF(-11, 5), QPointF(-11, 2), QPointF(-4, -1)
        ])
        painter.drawPolygon(shape)
        painter.restore()

        if aircraft.selected:
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(point, 16, 16)

        painter.setPen(QColor("#eafcff"))
        painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        painter.drawText(point + QPointF(15, -5), aircraft.callsign)
        painter.setFont(QFont("Consolas", 8))
        painter.drawText(point + QPointF(15, 8), f"{aircraft.altitude:.0f}m {aircraft.speed:.0f}km/h")

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        click = event.position()
        closest = None
        closest_dist = 24.0
        for aircraft in self.simulation.aircraft:
            point = self._world_to_screen(aircraft.x, aircraft.y)
            dist = math.hypot(point.x() - click.x(), point.y() - click.y())
            if dist < closest_dist:
                closest = aircraft
                closest_dist = dist
        self.aircraft_clicked.emit(closest)
