# ===== Base =====
from typing import Optional, Dict


# ===== PySide6 =====
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget
)


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

        self.tabs = QTabWidget()
        self.setup_tab = SetupTab(self.tabs)
        self.tabs.addTab(self.setup_tab, "Подключение и схема БД")

        self.aircraft_tab: Optional[AircraftTab] = None
        self.flights_tab: Optional[FlightsTab] = None
        self.passengers_tab: Optional[PassengersTab] = None
        self.tickets_tab: Optional[TicketsTab] = None
        self.crew_tab: Optional[CrewTab] = None
        self.crew_members_tab: Optional[CrewMembersTab] = None

        self.setCentralWidget(self.tabs)

    def attach_engine(self, engine: Engine, md: MetaData, tables: Dict[str, Table]):
        self.engine = engine
        self.md = md
        self.tables = tables

    def ensure_data_tabs(self):
        if self.engine is None or self.tables is None:
            return

        if self.aircraft_tab is None:
            self.aircraft_tab = AircraftTab(self.engine, self.tables, self.tabs)
            self.tabs.addTab(self.aircraft_tab, "Самолеты")
        if self.flights_tab is None:
            self.flights_tab = FlightsTab(self.engine, self.tables, self.tabs)
            self.tabs.addTab(self.flights_tab, "Рейсы")
        if self.passengers_tab is None:
            self.passengers_tab = PassengersTab(self.engine, self.tables, self.tabs)
            self.tabs.addTab(self.passengers_tab, "Пассажиры")
        if self.tickets_tab is None:
            self.tickets_tab = TicketsTab(self.engine, self.tables, self.tabs)
            self.tabs.addTab(self.tickets_tab, "Билеты")
        if self.crew_tab is None:
            self.crew_tab = CrewTab(self.engine, self.tables, self.tabs)
            self.tabs.addTab(self.crew_tab, "Экипажи")
        if self.crew_members_tab is None:
            self.crew_members_tab = CrewMembersTab(self.engine, self.tables, self.tabs)
            self.tabs.addTab(self.crew_members_tab, "Члены экипажа")

        self.refresh_combos()

    def refresh_all_models(self):
        if self.aircraft_tab:
            self.aircraft_tab.model.refresh()
        if self.flights_tab:
            self.flights_tab.model.refresh()
        if self.passengers_tab:
            self.passengers_tab.model.refresh()
        if self.tickets_tab:
            self.tickets_tab.model.refresh()
        if self.crew_tab:
            self.crew_tab.model.refresh()
        if self.crew_members_tab:
            self.crew_members_tab.model.refresh()

    def refresh_combos(self):
        if self.flights_tab:
            self.flights_tab.refresh_aircraft_combo()
        if self.tickets_tab:
            self.tickets_tab.refresh_flights_combo()
            self.tickets_tab.refresh_passengers_combo()
        if self.crew_tab:
            self.crew_tab.refresh_aircraft_combo()
        if self.crew_members_tab:
            self.crew_members_tab.refresh_crew_combo()

    def disconnect_db(self):
        # убрать вкладки (уничтожит модели)
        tabs_to_remove = [
            "aircraft_tab", "flights_tab", "passengers_tab",
            "tickets_tab", "crew_tab", "crew_members_tab"
        ]

        for attr in tabs_to_remove:
            tab = getattr(self, attr)
            if tab is not None:
                idx = self.tabs.indexOf(tab)
                if idx != -1:
                    self.tabs.removeTab(idx)
                tab.deleteLater()
                setattr(self, attr, None)

        QApplication.processEvents()

        # закрыть engine
        if self.engine is not None:
            self.engine.dispose()
        self.engine = None;
        self.md = None;
        self.tables = None

        # кнопки в состояние "нет подключения"
        self.setup_tab.connect_btn.setEnabled(True)
        self.setup_tab.disconnect_btn.setEnabled(False)
        self.setup_tab.create_btn.setEnabled(False)
        self.setup_tab.demo_btn.setEnabled(False)