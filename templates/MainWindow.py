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
        self.setWindowTitle("PySide6 + SQLAlchemy: CREATE/INSERT/CHECK/UNIQUE/PK/FK")
        self.resize(1100, 740)

        self.engine: Optional[Engine] = None
        self.md: Optional[MetaData] = None
        self.tables: Optional[Dict[str, Table]] = None

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

        self.setCentralWidget(self.tabs)

    def attach_engine(self, engine: Engine, md: MetaData, tables: Dict[str, Table]):
        self.engine = engine
        self.md = md
        self.tables = tables
        print(f"Engine attached: {engine}")  # Debug

    def ensure_data_tabs(self):
        if self.engine is None or self.tables is None:
            print("No engine or tables available")  # Debug
            return

        print("Creating data tabs...")  # Debug

        if self.aircraft_tab is None:
            self.aircraft_tab = AircraftTab(self.engine, self.tables)
            self.tabs.addTab(self.aircraft_tab, "Самолеты")
            print("Aircraft tab created")  # Debug

        if self.flights_tab is None:
            self.flights_tab = FlightsTab(self.engine, self.tables)
            self.tabs.addTab(self.flights_tab, "Рейсы")
            print("Flights tab created")  # Debug

        if self.passengers_tab is None:
            self.passengers_tab = PassengersTab(self.engine, self.tables)
            self.tabs.addTab(self.passengers_tab, "Пассажиры")
            print("Passengers tab created")  # Debug

        if self.tickets_tab is None:
            self.tickets_tab = TicketsTab(self.engine, self.tables)
            self.tabs.addTab(self.tickets_tab, "Билеты")
            print("Tickets tab created")  # Debug

        if self.crew_tab is None:
            self.crew_tab = CrewTab(self.engine, self.tables)
            self.tabs.addTab(self.crew_tab, "Экипажи")
            print("Crew tab created")  # Debug

        if self.crew_members_tab is None:
            self.crew_members_tab = CrewMembersTab(self.engine, self.tables)
            self.tabs.addTab(self.crew_members_tab, "Члены экипажа")
            print("Crew members tab created")  # Debug

        self.refresh_combos()

    def refresh_all_models(self):
        tabs = [
            self.aircraft_tab, self.flights_tab, self.passengers_tab,
            self.tickets_tab, self.crew_tab, self.crew_members_tab
        ]

        for tab in tabs:
            if tab and hasattr(tab, 'model'):
                tab.model.refresh()
                print(f"Refreshed model for {tab.__class__.__name__}")  # Debug

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
        # убрать вкладки
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

        # обнуляем ссылки
        self.aircraft_tab = None
        self.flights_tab = None
        self.passengers_tab = None
        self.tickets_tab = None
        self.crew_tab = None
        self.crew_members_tab = None

        # закрыть engine
        if self.engine is not None:
            self.engine.dispose()
        self.engine = None
        self.md = None
        self.tables = None

        QApplication.processEvents()