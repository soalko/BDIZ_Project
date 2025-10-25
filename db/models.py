# ===== Base =====
from typing import List, Dict, Any


# ===== PySide6 =====
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex


# ===== SQLAlchemy =====
from sqlalchemy import (
    MetaData, Table, Column, Integer, String, Date, Time, Boolean,
    ForeignKey, UniqueConstraint, CheckConstraint, select, inspect
)

from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError



# -------------------------------
# QAbstractTableModel для SQLAlchemy
# -------------------------------
class SATableModel(QAbstractTableModel):
    """Универсальная модель для QTableView (SQLAlchemy)."""

    def __init__(self, engine: Engine, table: Table, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.table = table
        self.columns: List[str] = [c.name for c in self.table.columns]
        self.pk_col = list(self.table.primary_key.columns)[0]
        self._rows: List[Dict[str, Any]] = []
        self.refresh()

    def refresh(self):
        self.beginResetModel()
        try:
            with self.engine.connect() as conn:
                # Получаем актуальные столбцы из базы данных
                table_name = self.table.name
                inspector = inspect(self.engine)
                actual_columns = inspector.get_columns(table_name)
                actual_column_names = [col['name'] for col in actual_columns]

                # Обновляем список столбцов модели, если они изменились
                if self.columns != actual_column_names:
                    self.columns = actual_column_names

                # Обновляем первичный ключ
                pk_columns = inspector.get_pk_constraint(table_name)['constrained_columns']
                if pk_columns:
                    self.pk_col = self.table.c[pk_columns[0]]

                # Создаем запрос только с существующими столбцами
                columns_to_select = [getattr(self.table.c, col_name) for col_name in actual_column_names
                                     if hasattr(self.table.c, col_name)]

                self._rows = []  # Очищаем текущие данные

                if columns_to_select:
                    res = conn.execute(select(*columns_to_select).order_by(self.pk_col.asc()))
                    for r in res:
                        # Безопасно создаем словарь из mapping
                        row_dict = {}
                        for key, value in r._mapping.items():
                            row_dict[key] = value
                        self._rows.append(row_dict)
                else:
                    self._rows = []
        except SQLAlchemyError as e:
            print(f"Ошибка при обновлении данных: {e}")
            self._rows = []
        finally:
            self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.columns)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        row = self._rows[index.row()]
        col_name = self.columns[index.column()]
        val = row.get(col_name)
        return "" if val is None else str(val)

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        return self.columns[section] if orientation == Qt.Horizontal else section + 1

    def pk_value_at(self, row: int):
        return self._rows[row].get(self.pk_col.name) if 0 <= row < len(self._rows) else None


def build_metadata() -> (MetaData, Dict[str, Table]):
    md = MetaData()

    # Таблица Aircraft
    aircraft = Table(
        "aircraft", md,
        Column("aircraft_id", Integer, primary_key=True, autoincrement=True),
        Column("model", String(100), nullable=False),
        Column("year", Integer, nullable=False),
        Column("seats_amount", Integer, nullable=False),
        Column("baggage_capacity", Integer, nullable=False),
        CheckConstraint("year >= 1900 AND year <= EXTRACT(YEAR FROM CURRENT_DATE)", name="chk_aircraft_year"),
        CheckConstraint("seats_amount > 0", name="chk_aircraft_seats"),
        CheckConstraint("baggage_capacity >= 0", name="chk_aircraft_baggage")
    )

    # Таблица Flights
    flights = Table(
        "flights", md,
        Column("flight_id", Integer, primary_key=True, autoincrement=True),
        Column("aircraft_id", Integer, ForeignKey("aircraft.aircraft_id",
                                                  onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        Column("departure_date", Date, nullable=False),
        Column("departure_time", Time, nullable=False),
        Column("departure_airport", String(10), nullable=False),
        Column("arrival_airport", String(10), nullable=False),
        Column("flight_time", Integer, nullable=False),  # в минутах
        CheckConstraint("char_length(departure_airport) = 3", name="chk_flights_dep_airport"),
        CheckConstraint("char_length(arrival_airport) = 3", name="chk_flights_arr_airport"),
        CheckConstraint("flight_time > 0", name="chk_flights_time"),
        CheckConstraint("departure_date >= DATE '2000-01-01'", name="chk_flights_date")
    )

    # Таблица Passengers
    passengers = Table(
        "passengers", md,
        Column("passenger_id", Integer, primary_key=True, autoincrement=True),
        Column("is_dependent", Boolean, nullable=False, default=False)
    )

    # Таблица Tickets
    tickets = Table(
        "tickets", md,
        Column("ticket_id", Integer, primary_key=True, autoincrement=True),
        Column("flight_id", Integer, ForeignKey("flights.flight_id",
                                                onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
        Column("passenger_id", Integer, ForeignKey("passengers.passenger_id",
                                                   onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
        Column("seat_number", String(4), nullable=False),
        Column("has_baggage", Boolean, nullable=False, default=False),
        UniqueConstraint("flight_id", "seat_number", name="uq_tickets_flight_seat"),
        UniqueConstraint("flight_id", "passenger_id", name="uq_tickets_flight_passenger"),
        CheckConstraint("seat_number ~ '^[0-9]{1,2}[A-K]$'", name="chk_tickets_seat_format")
    )

    # Таблица Crew
    crew = Table(
        "crew", md,
        Column("crew_id", Integer, primary_key=True, autoincrement=True),
        Column("aircraft_id", Integer, ForeignKey("aircraft.aircraft_id",
                                                  onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
        UniqueConstraint("aircraft_id", name="uq_crew_aircraft")
    )

    # Таблица Crew_member
    crew_member = Table(
        "crew_member", md,
        Column("member_id", Integer, primary_key=True, autoincrement=True),
        Column("job_position", String(50), nullable=False),
        Column("crew_id", Integer, ForeignKey("crew.crew_id",
                                              onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
        CheckConstraint("char_length(job_position) >= 2", name="chk_crew_member_position")
    )

    return md, {
        "aircraft": aircraft,
        "flights": flights,
        "passengers": passengers,
        "tickets": tickets,
        "crew": crew,
        "crew_member": crew_member
    }


def drop_and_create_schema_sa(engine: Engine, md: MetaData) -> bool:
    try:
        md.drop_all(engine)
        md.create_all(engine)
        return True
    except SQLAlchemyError as e:
        print("SA schema error:", e)
        return False


def insert_demo_data_sa(engine, t) -> bool:
    try:
        with engine.begin() as conn:
            # Данные для таблицы Aircraft
            conn.execute(t["aircraft"].insert(), [
                {"model": "Boeing 737-800", "year": 2018, "seats_amount": 189, "baggage_capacity": 2500},
                {"model": "Airbus A320", "year": 2020, "seats_amount": 180, "baggage_capacity": 2300},
                {"model": "Boeing 777-300", "year": 2019, "seats_amount": 365, "baggage_capacity": 4500},
                {"model": "Airbus A321", "year": 2021, "seats_amount": 220, "baggage_capacity": 2800},
            ])

            # Данные для таблицы Passengers
            conn.execute(t["passengers"].insert(), [
                {"is_dependent": False},
                {"is_dependent": False},
                {"is_dependent": True},
                {"is_dependent": False},
                {"is_dependent": True},
                {"is_dependent": False},
            ])

            # Данные для таблицы Flights
            conn.execute(t["flights"].insert(), [
                {"aircraft_id": 1, "departure_date": "2024-01-15", "departure_time": "08:30",
                 "departure_airport": "SVO", "arrival_airport": "LED", "flight_time": 90},
                {"aircraft_id": 2, "departure_date": "2024-01-15", "departure_time": "14:45",
                 "departure_airport": "DME", "arrival_airport": "AER", "flight_time": 150},
                {"aircraft_id": 3, "departure_date": "2024-01-16", "departure_time": "10:00",
                 "departure_airport": "VKO", "arrival_airport": "KRR", "flight_time": 120},
                {"aircraft_id": 1, "departure_date": "2024-01-16", "departure_time": "18:20",
                 "departure_airport": "LED", "arrival_airport": "SVO", "flight_time": 85},
            ])

            # Данные для таблицы Crew
            conn.execute(t["crew"].insert(), [
                {"aircraft_id": 1},
                {"aircraft_id": 2},
                {"aircraft_id": 3},
                {"aircraft_id": 4},
            ])

            # Данные для таблицы Crew_member
            conn.execute(t["crew_member"].insert(), [
                {"crew_id": 1, "job_position": "Пилот"},
                {"crew_id": 1, "job_position": "Второй пилот"},
                {"crew_id": 1, "job_position": "Стюардесса"},
                {"crew_id": 2, "job_position": "Пилот"},
                {"crew_id": 2, "job_position": "Стюардесса"},
                {"crew_id": 3, "job_position": "Пилот"},
                {"crew_id": 3, "job_position": "Второй пилот"},
                {"crew_id": 3, "job_position": "Стюардесса"},
                {"crew_id": 4, "job_position": "Пилот"},
            ])

            # Данные для таблицы Tickets
            conn.execute(t["tickets"].insert(), [
                {"flight_id": 1, "passenger_id": 1, "seat_number": "12A", "has_baggage": True},
                {"flight_id": 1, "passenger_id": 2, "seat_number": "12B", "has_baggage": False},
                {"flight_id": 1, "passenger_id": 3, "seat_number": "13A", "has_baggage": True},
                {"flight_id": 2, "passenger_id": 4, "seat_number": "8C", "has_baggage": True},
                {"flight_id": 2, "passenger_id": 5, "seat_number": "8D", "has_baggage": False},
                {"flight_id": 3, "passenger_id": 6, "seat_number": "21F", "has_baggage": True},
                {"flight_id": 4, "passenger_id": 1, "seat_number": "15C", "has_baggage": True},
                {"flight_id": 4, "passenger_id": 3, "seat_number": "15D", "has_baggage": False},
            ])

        return True
    except SQLAlchemyError as e:
        print("SA seed error:", e)
        return False