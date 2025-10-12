# ===== Base =====
from typing import Optional, Dict
import os
from typing import Optional, Dict

# ===== PySide6 =====
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QHBoxLayout, QWidget, QPushButton, QVBoxLayout
)
from PySide6.QtGui import QPalette, QBrush, QPixmap
from PySide6.QtCore import Qt

# ===== SQLAlchemy =====
from sqlalchemy import (
    MetaData, Table
)

from sqlalchemy.engine import Engine

# ===== Files =====
from templates.AircraftWindow import AircraftTab
from templates.CrewMemberWindow import CrewMembersTab
from templates.CrewWindow import CrewTab
from templates.FlightsWindow import FlightsTab
from templates.PassangersWindow import PassengersTab
from templates.SetupWindow import SetupTab
from templates.TicketsWindow import TicketsTab
from templates.modes import AppMode
from styles import switch_theme, get_current_theme


# -------------------------------
# Главное окно
# -------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Airport Database Management System")
        self.resize(1100, 740)

        self.engine: Optional[Engine] = None
        self.md: Optional[MetaData] = None
        self.tables: Optional[Dict[str, Table]] = None
        self.current_mode: AppMode = AppMode.SETUP

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.tabs = QTabWidget()
        try:
            self.tabs.setMovable(True)
        except Exception:
            try:
                self.tabs.tabBar().setMovable(True)
            except Exception:
                pass

        self.setup_tab = SetupTab()
        self.tabs.addTab(self.setup_tab, "Подключение и схема БД")

        self.aircraft_tab: Optional[AircraftTab] = None
        self.flights_tab: Optional[FlightsTab] = None
        self.passengers_tab: Optional[PassengersTab] = None
        self.tickets_tab: Optional[TicketsTab] = None
        self.crew_tab: Optional[CrewTab] = None
        self.crew_members_tab: Optional[CrewMembersTab] = None

        self.mode_panel = self.create_mode_panel()
        main_layout.addWidget(self.mode_panel)

        main_layout.addWidget(self.tabs)

        self.update_mode_buttons_state()
        self.update_theme_button_text()

    def create_mode_panel(self):
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 5, 10, 5)

        self.read_btn = QPushButton("Читать данные")
        self.edit_btn = QPushButton("Редактировать данные")
        self.add_btn = QPushButton("Добавить данные")
        self.theme_btn = QPushButton("Светлая тема")

        layout.addWidget(self.read_btn)
        layout.addWidget(self.edit_btn)
        layout.addWidget(self.add_btn)

        layout.addStretch()

        layout.addWidget(self.theme_btn)

        self.read_btn.clicked.connect(lambda: self.set_mode(AppMode.READ))
        self.edit_btn.clicked.connect(lambda: self.set_mode(AppMode.EDIT))
        self.add_btn.clicked.connect(lambda: self.set_mode(AppMode.ADD))
        self.theme_btn.clicked.connect(self.toggle_theme)

        return panel

    def toggle_theme(self):
        current = get_current_theme()
        new_theme = "light" if current == "dark" else "dark"
        switch_theme(new_theme)
        self.update_theme_button_text()

    def update_theme_button_text(self):
        current = get_current_theme()
        self.theme_btn.setText("Светлая тема" if current == "dark" else "Темная тема")

    def set_mode(self, mode: AppMode):
        self.current_mode = mode
        self.update_window_title()
        self.refresh_all_tabs()

    def update_window_title(self):
        mode_text = {
            AppMode.READ: "Режим чтения",
            AppMode.EDIT: "Режим редактирования",
            AppMode.ADD: "Режим добавления",
            AppMode.SETUP: "Режим настройки"
        }
        base_title = "Airport Database Management System"
        self.setWindowTitle(f"{base_title} - {mode_text[self.current_mode]}")

    def update_mode_buttons_state(self):
        is_connected = self.engine is not None

        self.read_btn.setEnabled(is_connected)
        self.edit_btn.setEnabled(is_connected)
        self.add_btn.setEnabled(is_connected)

    def attach_engine(self, engine: Engine, md: MetaData, tables: Dict[str, Table]):
        self.engine = engine
        self.md = md
        self.tables = tables
        print(f"Engine attached: {engine}")
        self.update_mode_buttons_state()
        self.ensure_data_tabs()

    def ensure_data_tabs(self):
        if self.engine is None or self.tables is None:
            print("No engine or tables available")
            return

        print("Creating data tabs...")

        if self.aircraft_tab is None:
            self.aircraft_tab = AircraftTab(self.engine, self.tables)
            self.tabs.addTab(self.aircraft_tab, "Самолеты")
            print("Aircraft tab created")

        if self.flights_tab is None:
            self.flights_tab = FlightsTab(self.engine, self.tables)
            self.tabs.addTab(self.flights_tab, "Рейсы")
            print("Flights tab created")

        if self.passengers_tab is None:
            self.passengers_tab = PassengersTab(self.engine, self.tables)
            self.tabs.addTab(self.passengers_tab, "Пассажиры")
            print("Passengers tab created")

        if self.tickets_tab is None:
            self.tickets_tab = TicketsTab(self.engine, self.tables)
            self.tabs.addTab(self.tickets_tab, "Билеты")
            print("Tickets tab created")

        if self.crew_tab is None:
            self.crew_tab = CrewTab(self.engine, self.tables)
            self.tabs.addTab(self.crew_tab, "Экипажи")
            print("Crew tab created")

        if self.crew_members_tab is None:
            self.crew_members_tab = CrewMembersTab(self.engine, self.tables)
            self.tabs.addTab(self.crew_members_tab, "Члены экипажа")
            print("Crew members tab created")

        self.refresh_combos()
        self.refresh_all_tabs()

    def refresh_all_models(self):
        tabs = [
            self.aircraft_tab, self.flights_tab, self.passengers_tab,
            self.tickets_tab, self.crew_tab, self.crew_members_tab
        ]

        for tab in tabs:
            if tab and hasattr(tab, 'model'):
                tab.model.refresh()
                print(f"Refreshed model for {tab.__class__.__name__}")

    def refresh_all_tabs(self):
        tabs = [
            self.aircraft_tab, self.flights_tab, self.passengers_tab,
            self.tickets_tab, self.crew_tab, self.crew_members_tab
        ]

        for tab in tabs:
            if tab and hasattr(tab, 'set_mode'):
                tab.set_mode(self.current_mode)

    def refresh_combos(self):
        if self.flights_tab and hasattr(self.flights_tab, 'refresh_aircraft_combo'):
            self.flights_tab.refresh_aircraft_combo()
        if self.tickets_tab and hasattr(self.tickets_tab, 'refresh_flights_combo'):
            self.tickets_tab.refresh_flights_combo()
        if self.tickets_tab and hasattr(self.tickets_tab, 'refresh_passengers_combo'):
            self.tickets_tab.refresh_passengers_combo()
        if self.crew_tab and hasattr(self.crew_tab, 'refresh_aircraft_combo'):
            self.crew_tab.refresh_aircraft_combo()
        if self.crew_members_tab and hasattr(self.crew_members_tab, 'refresh_crew_combo'):
            self.crew_members_tab.refresh_crew_combo()

    def disconnect_db(self):
        tabs_to_remove = [
            self.aircraft_tab, self.flights_tab, self.passengers_tab,
            self.tickets_tab, self.crew_tab, self.crew_members_tab
        ]

        for tab in tabs_to_remove:
            if tab is not None:
                idx = self.tabs.indexOf(tab)
                if idx != -1:
                    self.tabs.removeTab(idx)
                tab.deleteLater()

        self.aircraft_tab = None
        self.flights_tab = None
        self.passengers_tab = None
        self.tickets_tab = None
        self.crew_tab = None
        self.crew_members_tab = None

        if self.engine is not None:
            self.engine.dispose()
        self.engine = None
        self.md = None
        self.tables = None
        self.set_mode(AppMode.SETUP)
        self.update_mode_buttons_state()

        QApplication.processEvents()