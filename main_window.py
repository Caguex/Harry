from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from aircraft import AircraftStatus
from simulation import SimulationManager
from radar_widget import RadarWidget


APP_STYLE = """
QMainWindow, QWidget { background: #07131c; color: #e8f7fa; font-family: Arial; }
QGroupBox { border: 1px solid #1d6b80; border-radius: 8px; margin-top: 12px; padding: 10px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #37d5f4; }
QPushButton { background: #0d8fa8; border: none; border-radius: 6px; padding: 8px; font-weight: bold; }
QPushButton:hover { background: #12aecb; }
QPushButton#landing { background: #259f70; }
QPushButton#pause { background: #d18d16; }
QPushButton#danger { background: #c93a55; }
QListWidget { background: #0a202c; border: 1px solid #1d6b80; border-radius: 5px; }
QListWidget::item { padding: 8px; border-bottom: 1px solid #153845; }
QListWidget::item:selected { background: #12495c; }
QSpinBox, QDoubleSpinBox, QComboBox { background: #0d2532; border: 1px solid #28778a; border-radius: 4px; padding: 5px; }
QLabel#bigValue { font-size: 22px; font-weight: bold; color: #37d5f4; }
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ATC Simulator - IPSA / PySide6")
        self.resize(1420, 820)
        self.setStyleSheet(APP_STYLE)

        self.simulation = SimulationManager(self)
        self._build_menu()
        self._build_ui()
        self._connect_signals()

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(lambda: self.simulation.update(0.1))
        self.timer.start()
        self.refresh_ui()

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("Simulation")
        reset_action = QAction("Nouvelle partie", self)
        reset_action.setShortcut("Ctrl+N")
        reset_action.triggered.connect(self.simulation.reset)
        menu.addAction(reset_action)
        quit_action = QAction("Quitter", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)

        help_menu = self.menuBar().addMenu("Aide")
        about = QAction("À propos", self)
        about.triggered.connect(self._show_about)
        help_menu.addAction(about)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        left = self._build_left_panel()
        self.radar = RadarWidget(self.simulation)
        right = self._build_right_panel()
        root.addWidget(left, 1)
        root.addWidget(self.radar, 3)
        root.addWidget(right, 1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Simulation prête")

    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        layout = QVBoxLayout(panel)
        title = QLabel("✈ ATC SIMULATOR")
        title.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        title.setStyleSheet("color:#37d5f4")
        layout.addWidget(title)

        stats_box = QGroupBox("STATISTIQUES")
        stats = QGridLayout(stats_box)
        self.score_label = QLabel("0"); self.score_label.setObjectName("bigValue")
        self.level_label = QLabel("1"); self.level_label.setObjectName("bigValue")
        self.aircraft_count = QLabel("0"); self.aircraft_count.setObjectName("bigValue")
        self.landed_label = QLabel("0")
        self.collision_label = QLabel("0")
        self.avg_time_label = QLabel("0 s")
        stats.addWidget(QLabel("Score"), 0, 0); stats.addWidget(self.score_label, 0, 1)
        stats.addWidget(QLabel("Niveau"), 1, 0); stats.addWidget(self.level_label, 1, 1)
        stats.addWidget(QLabel("Avions actifs"), 2, 0); stats.addWidget(self.aircraft_count, 2, 1)
        stats.addWidget(QLabel("Atterrissages"), 3, 0); stats.addWidget(self.landed_label, 3, 1)
        stats.addWidget(QLabel("Collisions"), 4, 0); stats.addWidget(self.collision_label, 4, 1)
        stats.addWidget(QLabel("Temps moyen"), 5, 0); stats.addWidget(self.avg_time_label, 5, 1)
        layout.addWidget(stats_box)

        aircraft_box = QGroupBox("AVIONS")
        aircraft_layout = QVBoxLayout(aircraft_box)
        self.aircraft_list = QListWidget()
        aircraft_layout.addWidget(self.aircraft_list)
        layout.addWidget(aircraft_box, 1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QFrame()
        layout = QVBoxLayout(panel)
        selected_box = QGroupBox("AVION SÉLECTIONNÉ")
        form = QFormLayout(selected_box)
        self.sel_callsign = QLabel("Aucun")
        self.sel_status = QLabel("-")
        self.sel_alt = QLabel("-")
        self.sel_speed = QLabel("-")
        self.sel_heading = QLabel("-")
        self.sel_fuel = QLabel("-")
        self.sel_event = QLabel("-")
        self.sel_event.setWordWrap(True)
        form.addRow("Indicatif", self.sel_callsign)
        form.addRow("Statut", self.sel_status)
        form.addRow("Altitude", self.sel_alt)
        form.addRow("Vitesse", self.sel_speed)
        form.addRow("Cap", self.sel_heading)
        form.addRow("Carburant", self.sel_fuel)
        form.addRow("Événement", self.sel_event)
        layout.addWidget(selected_box)

        controls = QGroupBox("INSTRUCTIONS")
        controls_layout = QVBoxLayout(controls)

        heading_row = QHBoxLayout()
        self.heading_spin = QSpinBox(); self.heading_spin.setRange(0, 359); self.heading_spin.setSuffix("°")
        heading_btn = QPushButton("Changer le cap")
        heading_btn.clicked.connect(self._apply_heading)
        heading_row.addWidget(self.heading_spin); heading_row.addWidget(heading_btn)
        controls_layout.addLayout(heading_row)

        alt_row = QHBoxLayout()
        climb_btn = QPushButton("▲ Monter +500 m")
        descend_btn = QPushButton("▼ Descendre -500 m")
        climb_btn.clicked.connect(lambda: self._change_altitude(500))
        descend_btn.clicked.connect(lambda: self._change_altitude(-500))
        alt_row.addWidget(climb_btn); alt_row.addWidget(descend_btn)
        controls_layout.addLayout(alt_row)

        speed_row = QHBoxLayout()
        self.speed_spin = QSpinBox(); self.speed_spin.setRange(140, 950); self.speed_spin.setSuffix(" km/h")
        speed_btn = QPushButton("Régler vitesse")
        speed_btn.clicked.connect(self._apply_speed)
        speed_row.addWidget(self.speed_spin); speed_row.addWidget(speed_btn)
        controls_layout.addLayout(speed_row)

        self.land_btn = QPushButton("✓ Autoriser l'atterrissage")
        self.land_btn.setObjectName("landing")
        self.land_btn.clicked.connect(self._request_landing)
        controls_layout.addWidget(self.land_btn)

        self.pause_btn = QPushButton("⏸ Mettre en pause")
        self.pause_btn.setObjectName("pause")
        self.pause_btn.clicked.connect(self._toggle_pause)
        controls_layout.addWidget(self.pause_btn)

        spawn_btn = QPushButton("＋ Ajouter un avion")
        spawn_btn.clicked.connect(self.simulation.spawn_aircraft)
        controls_layout.addWidget(spawn_btn)
        layout.addWidget(controls)

        legend = QGroupBox("LÉGENDE")
        legend_layout = QVBoxLayout(legend)
        legend_layout.addWidget(QLabel("🔵 Normal   🟠 Attention"))
        legend_layout.addWidget(QLabel("🔴 Urgence  🟢 Approche"))
        layout.addWidget(legend)
        layout.addStretch(1)
        return panel

    def _connect_signals(self) -> None:
        self.simulation.changed.connect(self.refresh_ui)
        self.simulation.message.connect(self.statusBar().showMessage)

        self.radar.aircraft_clicked.connect(self._radar_aircraft_selected)

        self.aircraft_list.itemSelectionChanged.connect(
            self._list_selection_changed
        )

    def _radar_aircraft_selected(self, aircraft) -> None:
        self.simulation.select_aircraft(aircraft)

        if aircraft:
            self.heading_spin.setValue(
                int(aircraft.target_heading) % 360
            )

            self.speed_spin.setValue(
                int(aircraft.target_speed)
            )
    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "À propos",
            "ATC Simulator - projet pédagogique PySide6\n"
            "Simulation POO de contrôle aérien avec radar, collisions, score et événements aléatoires.",
        )

    def _selected(self):
        return self.simulation.selected

    def _apply_heading(self) -> None:
        aircraft = self._selected()

        if not aircraft:
            self.statusBar().showMessage("Sélectionnez d'abord un avion.")
            return

        new_heading = self.heading_spin.value()

        aircraft.set_heading(new_heading)

        self.statusBar().showMessage(
            f"✈ {aircraft.callsign} : cap demandé {new_heading}°"
        )

        self.refresh_ui()

    def _change_altitude(self, delta: int) -> None:
        if self._selected():
            if delta > 0:
                self._selected().climb(delta)
            else:
                self._selected().descend(abs(delta))

    def _apply_speed(self) -> None:
        aircraft = self._selected()

        if not aircraft:
            self.statusBar().showMessage("Sélectionnez d'abord un avion.")
            return

        new_speed = self.speed_spin.value()

        aircraft.set_speed(new_speed)

        self.statusBar().showMessage(
            f"✈ {aircraft.callsign} : vitesse demandée {new_speed} km/h"
        )

        self.refresh_ui()
    def _request_landing(self) -> None:
        aircraft = self._selected()
        if not aircraft:
            self.statusBar().showMessage("Sélectionnez d'abord un avion.")
            return
        aircraft.request_landing()
        self.statusBar().showMessage(f"{aircraft.callsign} autorisé à l'atterrissage.")

    def _toggle_pause(self) -> None:
        self.simulation.paused = not self.simulation.paused
        self.pause_btn.setText("▶ Reprendre" if self.simulation.paused else "⏸ Mettre en pause")

    def _list_selection_changed(self) -> None:
        items = self.aircraft_list.selectedItems()

        if not items:
            return

        callsign = items[0].data(Qt.ItemDataRole.UserRole)

        if (
                not self.simulation.selected
                or self.simulation.selected.callsign != callsign
        ):
            self.simulation.select_by_callsign(callsign)

            aircraft = self.simulation.selected

            if aircraft:
                self.heading_spin.setValue(
                    int(aircraft.target_heading) % 360
                )

                self.speed_spin.setValue(
                    int(aircraft.target_speed)
                )

    def refresh_ui(self) -> None:
        s = self.simulation.stats
        self.score_label.setText(str(s.score))
        self.level_label.setText(str(self.simulation.level))
        self.aircraft_count.setText(str(len(self.simulation.aircraft)))
        self.landed_label.setText(str(s.landed))
        self.collision_label.setText(str(s.collisions))
        self.avg_time_label.setText(f"{s.average_management_time:.1f} s")

        selected_callsign = self.simulation.selected.callsign if self.simulation.selected else None
        self.aircraft_list.blockSignals(True)
        self.aircraft_list.clear()
        selected_row = -1
        for row, aircraft in enumerate(self.simulation.aircraft):
            marker = {
                AircraftStatus.NORMAL: "🔵",
                AircraftStatus.WARNING: "🟠",
                AircraftStatus.EMERGENCY: "🔴",
                AircraftStatus.LANDING: "🟢",
            }[aircraft.status]
            item = QListWidgetItem(f"{marker} {aircraft.callsign}\n{aircraft.short_info}")
            item.setData(Qt.ItemDataRole.UserRole, aircraft.callsign)
            self.aircraft_list.addItem(item)
            if aircraft.callsign == selected_callsign:
                selected_row = row
        if selected_row >= 0:
            self.aircraft_list.setCurrentRow(selected_row)
        self.aircraft_list.blockSignals(False)

        a = self.simulation.selected
        if not a:
            for label, value in [
                (self.sel_callsign, "Aucun"), (self.sel_status, "-"), (self.sel_alt, "-"),
                (self.sel_speed, "-"), (self.sel_heading, "-"), (self.sel_fuel, "-"), (self.sel_event, "-")
            ]:
                label.setText(value)
            return
        self.sel_callsign.setText(a.callsign)
        self.sel_status.setText(a.status.value)
        self.sel_alt.setText(f"{a.altitude:.0f} m → {a.target_altitude:.0f} m")
        self.sel_speed.setText(f"{a.speed:.0f} km/h → {a.target_speed:.0f}")
        self.sel_heading.setText(f"{a.heading:.0f}° → {a.target_heading:.0f}°")
        self.sel_fuel.setText(f"{a.fuel:.1f}%")
        self.sel_event.setText(a.event_message or "Aucun")
