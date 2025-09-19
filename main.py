# -*- coding: utf-8 -*-
"""
PySide6 + SQLAlchemy (PostgreSQL) — стабильная версия:
- Без QtSql / PyQt.
- QAbstractTableModel с beginResetModel/endResetModel.
- Кнопки: Подключиться/Отключиться, CREATE schema, INSERT demo.
- Переключатель драйвера: psycopg2 / psycopg (v3) / pg8000 (pure Python).
- Вместо parent().parent() используем self.window() для доступа к MainWindow.
"""

import sys
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import date, time
import faulthandler

faulthandler.enable()

from PySide6.QtCore import Qt, QDate, QAbstractTableModel, QModelIndex, QTime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QSpinBox,
    QDateEdit, QComboBox, QCheckBox, QTextEdit, QTableView, QGroupBox, QTimeEdit
)

# ===== SQLAlchemy =====
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, Date, Time, Boolean,
    ForeignKey, UniqueConstraint, CheckConstraint, select, insert, delete
)

from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


# -------------------------------
# Конфигурация подключения
# -------------------------------
@dataclass
class PgConfig:
    host: str = "localhost"
    port: int = 5432
    dbname: str = "airport"
    user: str = "postgres"
    password: str = "root"
    sslmode: str = "prefer"  # для psycopg2/psycopg
    connect_timeout: int = 5  # секунды
    driver: str = "psycopg2"  # psycopg2 | psycopg | pg8000


# -------------------------------
# Создание Engine и схемы
# -------------------------------
def make_engine(cfg: PgConfig) -> Engine:
    drivername_map = {
        "psycopg2": "postgresql+psycopg2",
        "psycopg": "postgresql+psycopg",
        "pg8000": "postgresql+pg8000",
    }
    drivername = drivername_map.get(cfg.driver, "postgresql+psycopg2")

    if cfg.driver in ("psycopg2", "psycopg"):
        query = {
            "sslmode": cfg.sslmode,
            "application_name": "QtEduDemo",
            "connect_timeout": str(cfg.connect_timeout),
        }
    else:  # pg8000 — только app_name
        query = {"application_name": "QtEduDemo"}

    url = URL.create(
        drivername=drivername,
        username=cfg.user,
        password=cfg.password,
        host=cfg.host,
        port=cfg.port,
        database=cfg.dbname,
        query=query,
    )

    engine = create_engine(url, future=True, pool_pre_ping=True)
    # sanity ping
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    return engine


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
                res = conn.execute(select(self.table).order_by(self.pk_col.asc()))
                self._rows = [dict(r._mapping) for r in res]
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


# -------------------------------
# Вкладка «Самолеты»
# -------------------------------
class AircraftTab(QWidget):
    def __init__(self, engine, tables, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.t = tables
        self.model = SATableModel(engine, self.t["aircraft"], self)

        # Создание виджетов для ввода данных
        self.model_edit = QLineEdit()
        self.year_edit = QSpinBox()
        self.year_edit.setRange(1900, QDate.currentDate().year())
        self.year_edit.setValue(2000)

        self.seats_edit = QSpinBox()
        self.seats_edit.setRange(1, 1000)
        self.seats_edit.setValue(150)

        self.baggage_edit = QSpinBox()
        self.baggage_edit.setRange(0, 10000)
        self.baggage_edit.setValue(1000)

        # Форма для ввода данных
        form = QFormLayout()
        form.addRow("Модель:", self.model_edit)
        form.addRow("Год выпуска:", self.year_edit)
        form.addRow("Количество мест:", self.seats_edit)
        form.addRow("Вместимость багажа:", self.baggage_edit)

        # Кнопки
        self.add_btn = QPushButton("Добавить самолет (INSERT)")
        self.add_btn.clicked.connect(self.add_aircraft)
        self.del_btn = QPushButton("Удалить выбранный самолет")
        self.del_btn.clicked.connect(self.delete_selected)

        btns = QHBoxLayout()
        btns.addWidget(self.add_btn)
        btns.addWidget(self.del_btn)

        # Таблица
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        # Основной layout
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btns)
        layout.addWidget(self.table)

    def add_aircraft(self):
        model = self.model_edit.text().strip()
        year = self.year_edit.value()
        seats = self.seats_edit.value()
        baggage = self.baggage_edit.value()

        if not model:
            QMessageBox.warning(self, "Ввод", "Модель самолета обязательна (NOT NULL)")
            return

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.t["aircraft"]).values(
                    model=model, year=year, seats_amount=seats, baggage_capacity=baggage
                ))
            self.model.refresh()
            self.clear_form()
            self.window().refresh_combos()
        except IntegrityError as e:
            QMessageBox.critical(self, "Ошибка INSERT (CHECK constraint)", str(e.orig))
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка INSERT", str(e))

    def delete_selected(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите самолет")
            return

        aircraft_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.t["aircraft"]).where(
                    self.t["aircraft"].c.aircraft_id == aircraft_id
                ))
            self.model.refresh()
            self.window().refresh_combos()
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def clear_form(self):
        """Очистка формы после успешного добавления"""
        self.model_edit.clear()
        self.year_edit.setValue(2000)
        self.seats_edit.setValue(150)
        self.baggage_edit.setValue(1000)


# -------------------------------
# Вкладка «Рейсы»
# -------------------------------
class FlightsTab(QWidget):
    def __init__(self, engine, tables, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.t = tables
        self.model = SATableModel(engine, self.t["flights"], self)

        # Создание виджетов для ввода данных
        self.aircraft_combo = QComboBox()
        self.departure_date_edit = QDateEdit()
        self.departure_date_edit.setCalendarPopup(True)
        self.departure_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.departure_date_edit.setDate(QDate.currentDate())

        self.departure_time_edit = QTimeEdit()
        self.departure_time_edit.setDisplayFormat("HH:mm")
        self.departure_time_edit.setTime(QTime(12, 0))

        self.departure_airport_edit = QLineEdit()
        self.departure_airport_edit.setMaxLength(3)

        self.arrival_airport_edit = QLineEdit()
        self.arrival_airport_edit.setMaxLength(3)

        self.flight_time_edit = QSpinBox()
        self.flight_time_edit.setRange(1, 1440)  # от 1 минуты до 24 часов
        self.flight_time_edit.setValue(120)
        self.flight_time_edit.setSuffix(" минут")

        # Форма для ввода данных
        form = QFormLayout()
        form.addRow("Самолет:", self.aircraft_combo)
        form.addRow("Дата вылета:", self.departure_date_edit)
        form.addRow("Время вылета:", self.departure_time_edit)
        form.addRow("Аэропорт вылета:", self.departure_airport_edit)
        form.addRow("Аэропорт прибытия:", self.arrival_airport_edit)
        form.addRow("Время полета:", self.flight_time_edit)

        # Кнопки
        self.add_btn = QPushButton("Добавить рейс (INSERT)")
        self.add_btn.clicked.connect(self.add_flight)
        self.del_btn = QPushButton("Удалить выбранный рейс")
        self.del_btn.clicked.connect(self.delete_selected)

        btns = QHBoxLayout()
        btns.addWidget(self.add_btn)
        btns.addWidget(self.del_btn)

        # Таблица
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        # Основной layout
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btns)
        layout.addWidget(self.table)

        # Загрузка данных в комбобокс
        self.refresh_aircraft_combo()

    def refresh_aircraft_combo(self):
        """Обновление списка самолетов в комбобоксе"""
        self.aircraft_combo.clear()
        try:
            with self.engine.connect() as conn:
                result = conn.execute(self.t["aircraft"].select().order_by(self.t["aircraft"].c.model))
                for row in result:
                    self.aircraft_combo.addItem(f"{row.model} (ID: {row.aircraft_id})", row.aircraft_id)
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка загрузки самолетов", str(e))

    def _qdate_to_pydate(self, qd: QDate) -> date:
        return date(qd.year(), qd.month(), qd.day())

    def _qtime_to_pytime(self, qt: QTime) -> time:
        return time(qt.hour(), qt.minute())

    def add_flight(self):
        if self.aircraft_combo.currentIndex() == -1:
            QMessageBox.warning(self, "Ввод", "Необходимо выбрать самолет")
            return

        aircraft_id = self.aircraft_combo.currentData()
        departure_date = self._qdate_to_pydate(self.departure_date_edit.date())
        departure_time = self._qtime_to_pytime(self.departure_time_edit.time())
        departure_airport = self.departure_airport_edit.text().strip().upper()
        arrival_airport = self.arrival_airport_edit.text().strip().upper()
        flight_time = self.flight_time_edit.value()

        if not departure_airport or not arrival_airport:
            QMessageBox.warning(self, "Ввод", "Аэропорты вылета и прибытия обязательны")
            return

        if len(departure_airport) != 3 or len(arrival_airport) != 3:
            QMessageBox.warning(self, "Ввод", "Коды аэроподов должны состоять из 3 символов")
            return

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.t["flights"]).values(
                    aircraft_id=aircraft_id,
                    departure_date=departure_date,
                    departure_time=departure_time,
                    departure_airport=departure_airport,
                    arrival_airport=arrival_airport,
                    flight_time=flight_time
                ))
            self.model.refresh()
            self.clear_form()
            self.window().refresh_combos()
        except IntegrityError as e:
            QMessageBox.critical(self, "Ошибка INSERT (CHECK/FOREIGN KEY constraint)", str(e.orig))
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка INSERT", str(e))

    def delete_selected(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите рейс")
            return

        flight_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.t["flights"]).where(
                    self.t["flights"].c.flight_id == flight_id
                ))
            self.model.refresh()
            self.window().refresh_combos()
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def clear_form(self):
        """Очистка формы после успешного добавления"""
        self.departure_airport_edit.clear()
        self.arrival_airport_edit.clear()
        self.flight_time_edit.setValue(120)
        self.departure_date_edit.setDate(QDate.currentDate())
        self.departure_time_edit.setTime(QTime(12, 0))


# -------------------------------
# Вкладка «Пассажиры»
# -------------------------------
class PassengersTab(QWidget):
    def __init__(self, engine, tables, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.t = tables
        self.model = SATableModel(engine, self.t["passengers"], self)

        # Создание виджетов для ввода данных
        self.is_dependent_checkbox = QCheckBox("Зависимый пассажир")
        self.is_dependent_checkbox.setChecked(False)

        # Форма для ввода данных
        form = QFormLayout()
        form.addRow("Тип пассажира:", self.is_dependent_checkbox)

        # Кнопки
        self.add_btn = QPushButton("Добавить пассажира (INSERT)")
        self.add_btn.clicked.connect(self.add_passenger)
        self.del_btn = QPushButton("Удалить выбранного пассажира")
        self.del_btn.clicked.connect(self.delete_selected)

        btns = QHBoxLayout()
        btns.addWidget(self.add_btn)
        btns.addWidget(self.del_btn)

        # Таблица
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        # Основной layout
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btns)
        layout.addWidget(self.table)

    def add_passenger(self):
        is_dependent = self.is_dependent_checkbox.isChecked()

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.t["passengers"]).values(
                    is_dependent=is_dependent
                ))
            self.model.refresh()
            self.clear_form()
            self.window().refresh_combos()
        except IntegrityError as e:
            QMessageBox.critical(self, "Ошибка INSERT (CHECK constraint)", str(e.orig))
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка INSERT", str(e))

    def delete_selected(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите пассажира")
            return

        passenger_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.t["passengers"]).where(
                    self.t["passengers"].c.passenger_id == passenger_id
                ))
            self.model.refresh()
            self.window().refresh_combos()
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def clear_form(self):
        """Очистка формы после успешного добавления"""
        self.is_dependent_checkbox.setChecked(False)


# -------------------------------
# Вкладка «Билеты»
# -------------------------------
class TicketsTab(QWidget):
    def __init__(self, engine, tables, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.t = tables
        self.model = SATableModel(engine, self.t["tickets"], self)

        # Создание виджетов для ввода данных
        self.flight_combo = QComboBox()
        self.passenger_combo = QComboBox()
        self.seat_number_edit = QLineEdit()
        self.seat_number_edit.setMaxLength(4)
        self.has_baggage_checkbox = QCheckBox("Есть багаж")
        self.has_baggage_checkbox.setChecked(False)

        # Форма для ввода данных
        form = QFormLayout()
        form.addRow("Рейс:", self.flight_combo)
        form.addRow("Пассажир:", self.passenger_combo)
        form.addRow("Номер места:", self.seat_number_edit)
        form.addRow("Багаж:", self.has_baggage_checkbox)

        # Кнопки
        self.add_btn = QPushButton("Добавить билет (INSERT)")
        self.add_btn.clicked.connect(self.add_ticket)
        self.del_btn = QPushButton("Удалить выбранный билет")
        self.del_btn.clicked.connect(self.delete_selected)

        btns = QHBoxLayout()
        btns.addWidget(self.add_btn)
        btns.addWidget(self.del_btn)

        # Таблица
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        # Основной layout
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btns)
        layout.addWidget(self.table)

        # Загрузка данных в комбобоксы
        self.refresh_flights_combo()
        self.refresh_passengers_combo()

    def refresh_flights_combo(self):
        """Обновление списка рейсов в комбобоксе"""
        self.flight_combo.clear()
        try:
            with self.engine.connect() as conn:
                result = conn.execute(self.t["flights"].select().order_by(self.t["flights"].c.flight_id))
                for row in result:
                    self.flight_combo.addItem(
                        f"Рейс {row.flight_id}: {row.departure_airport}-{row.arrival_airport}",
                        row.flight_id
                    )
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка загрузки рейсов", str(e))

    def refresh_passengers_combo(self):
        """Обновление списка пассажиров в комбобоксе"""
        self.passenger_combo.clear()
        try:
            with self.engine.connect() as conn:
                result = conn.execute(self.t["passengers"].select().order_by(self.t["passengers"].c.passenger_id))
                for row in result:
                    passenger_type = "Зависимый" if row.is_dependent else "Независимый"
                    self.passenger_combo.addItem(
                        f"Пассажир {row.passenger_id} ({passenger_type})",
                        row.passenger_id
                    )
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка загрузки пассажиров", str(e))

    def add_ticket(self):
        if self.flight_combo.currentIndex() == -1:
            QMessageBox.warning(self, "Ввод", "Необходимо выбрать рейс")
            return

        if self.passenger_combo.currentIndex() == -1:
            QMessageBox.warning(self, "Ввод", "Необходимо выбрать пассажира")
            return

        flight_id = self.flight_combo.currentData()
        passenger_id = self.passenger_combo.currentData()
        seat_number = self.seat_number_edit.text().strip().upper()
        has_baggage = self.has_baggage_checkbox.isChecked()

        if not seat_number:
            QMessageBox.warning(self, "Ввод", "Номер места обязателен")
            return

        # Проверка формата места (например, 12A, 1B и т.д.)
        if not (len(seat_number) >= 2 and len(seat_number) <= 4 and
                seat_number[:-1].isdigit() and seat_number[-1].isalpha()):
            QMessageBox.warning(self, "Ввод", "Номер места должен быть в формате: число + буква (например: 12A)")
            return

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.t["tickets"]).values(
                    flight_id=flight_id,
                    passenger_id=passenger_id,
                    seat_number=seat_number,
                    has_baggage=has_baggage
                ))
            self.model.refresh()
            self.clear_form()
            self.window().refresh_combos()
        except IntegrityError as e:
            QMessageBox.critical(self, "Ошибка INSERT (UNIQUE/FOREIGN KEY/CHECK constraint)", str(e.orig))
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка INSERT", str(e))

    def delete_selected(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите билет")
            return

        ticket_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.t["tickets"]).where(
                    self.t["tickets"].c.ticket_id == ticket_id
                ))
            self.model.refresh()
            self.window().refresh_combos()
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def clear_form(self):
        """Очистка формы после успешного добавления"""
        self.seat_number_edit.clear()
        self.has_baggage_checkbox.setChecked(False)
        # Не очищаем комбобоксы, чтобы можно было быстро добавить несколько билетов на один рейс


# -------------------------------
# Вкладка «Экипаж»
# -------------------------------
class CrewTab(QWidget):
    def __init__(self, engine, tables, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.t = tables
        self.model = SATableModel(engine, self.t["crew"], self)

        # Создание виджетов для ввода данных
        self.aircraft_combo = QComboBox()

        # Форма для ввода данных
        form = QFormLayout()
        form.addRow("Самолет:", self.aircraft_combo)

        # Кнопки
        self.add_btn = QPushButton("Добавить экипаж (INSERT)")
        self.add_btn.clicked.connect(self.add_crew)
        self.del_btn = QPushButton("Удалить выбранный экипаж")
        self.del_btn.clicked.connect(self.delete_selected)

        btns = QHBoxLayout()
        btns.addWidget(self.add_btn)
        btns.addWidget(self.del_btn)

        # Таблица
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        # Основной layout
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btns)
        layout.addWidget(self.table)

        # Загрузка данных в комбобокс
        self.refresh_aircraft_combo()

    def refresh_aircraft_combo(self):
        """Обновление списка самолетов в комбобоксе"""
        self.aircraft_combo.clear()
        try:
            with self.engine.connect() as conn:
                result = conn.execute(self.t["aircraft"].select().order_by(self.t["aircraft"].c.model))
                for row in result:
                    self.aircraft_combo.addItem(
                        f"{row.model} (ID: {row.aircraft_id}, Мест: {row.seats_amount})",
                        row.aircraft_id
                    )
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка загрузки самолетов", str(e))

    def add_crew(self):
        if self.aircraft_combo.currentIndex() == -1:
            QMessageBox.warning(self, "Ввод", "Необходимо выбрать самолет")
            return

        aircraft_id = self.aircraft_combo.currentData()

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.t["crew"]).values(
                    aircraft_id=aircraft_id
                ))
            self.model.refresh()
            self.clear_form()
            self.window().refresh_combos()
        except IntegrityError as e:
            if "uq_crew_aircraft" in str(e.orig):
                QMessageBox.critical(self, "Ошибка INSERT", "У этого самолета уже есть экипаж (UNIQUE constraint)")
            else:
                QMessageBox.critical(self, "Ошибка INSERT (FOREIGN KEY constraint)", str(e.orig))
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка INSERT", str(e))

    def delete_selected(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите экипаж")
            return

        crew_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
                # Сначала проверяем, есть ли члены экипажа
                result = conn.execute(
                    self.t["crew_member"].select().where(
                        self.t["crew_member"].c.crew_id == crew_id
                    )
                )
                if result.fetchone():
                    QMessageBox.warning(
                        self,
                        "Ошибка удаления",
                        "Нельзя удалить экипаж, так как в нем есть члены экипажа. "
                        "Сначала удалите всех членов экипажа."
                    )
                    return

                conn.execute(delete(self.t["crew"]).where(
                    self.t["crew"].c.crew_id == crew_id
                ))
            self.model.refresh()
            self.window().refresh_combos()
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def clear_form(self):
        """Очистка формы после успешного добавления"""
        # Не очищаем комбобокс, чтобы можно было быстро добавить несколько экипажей
        pass


# -------------------------------
# Вкладка «Члены Экипажа»
# -------------------------------
class CrewMembersTab(QWidget):
    def __init__(self, engine, tables, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.t = tables
        self.model = SATableModel(engine, self.t["crew_member"], self)

        # Создание виджетов для ввода данных
        self.crew_combo = QComboBox()
        self.job_position_edit = QLineEdit()
        self.job_position_edit.setMaxLength(50)

        # Форма для ввода данных
        form = QFormLayout()
        form.addRow("Экипаж:", self.crew_combo)
        form.addRow("Должность:", self.job_position_edit)

        # Кнопки
        self.add_btn = QPushButton("Добавить члена экипажа (INSERT)")
        self.add_btn.clicked.connect(self.add_crew_member)
        self.del_btn = QPushButton("Удалить выбранного члена экипажа")
        self.del_btn.clicked.connect(self.delete_selected)

        btns = QHBoxLayout()
        btns.addWidget(self.add_btn)
        btns.addWidget(self.del_btn)

        # Таблица
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        # Основной layout
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btns)
        layout.addWidget(self.table)

        # Загрузка данных в комбобокс
        self.refresh_crew_combo()

    def refresh_crew_combo(self):
        """Обновление списка экипажей в комбобоксе"""
        self.crew_combo.clear()
        try:
            with self.engine.connect() as conn:
                # Join с aircraft, чтобы показать информацию о самолете
                query = self.t["crew"].join(
                    self.t["aircraft"],
                    self.t["crew"].c.aircraft_id == self.t["aircraft"].c.aircraft_id
                ).select().order_by(self.t["crew"].c.crew_id)

                result = conn.execute(query)
                for row in result:
                    self.crew_combo.addItem(
                        f"Экипаж {row.crew_id} (Самолет: {row.model}, ID: {row.aircraft_id})",
                        row.crew_id
                    )
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка загрузки экипажей", str(e))

    def add_crew_member(self):
        if self.crew_combo.currentIndex() == -1:
            QMessageBox.warning(self, "Ввод", "Необходимо выбрать экипаж")
            return

        crew_id = self.crew_combo.currentData()
        job_position = self.job_position_edit.text().strip()

        if not job_position:
            QMessageBox.warning(self, "Ввод", "Должность обязательна")
            return

        if len(job_position) < 2:
            QMessageBox.warning(self, "Ввод", "Должность должна содержать минимум 2 символа")
            return

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.t["crew_member"]).values(
                    crew_id=crew_id,
                    job_position=job_position
                ))
            self.model.refresh()
            self.clear_form()
            self.window().refresh_combos()
        except IntegrityError as e:
            if "foreign key constraint" in str(e.orig).lower():
                QMessageBox.critical(self, "Ошибка INSERT", "Ошибка внешнего ключа (неверный ID экипажа)")
            else:
                QMessageBox.critical(self, "Ошибка INSERT (CHECK constraint)", str(e.orig))
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка INSERT", str(e))

    def delete_selected(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите члена экипажа")
            return

        member_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.t["crew_member"]).where(
                    self.t["crew_member"].c.member_id == member_id
                ))
            self.model.refresh()
            self.window().refresh_combos()
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def clear_form(self):
        """Очистка формы после успешного добавления"""
        self.job_position_edit.clear()
        # Не очищаем комбобокс, чтобы можно было быстро добавить несколько членов в один экипаж


# -------------------------------
# Вкладка «Подключение и схема БД»
# -------------------------------
class SetupTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log = QTextEdit();
        self.log.setReadOnly(True)

        self.driver_cb = QComboBox()
        self.driver_cb.addItem("psycopg2 (binary)", "psycopg2")
        self.driver_cb.addItem("psycopg (v3, binary)", "psycopg")
        self.driver_cb.addItem("pg8000 (pure Python)", "pg8000")

        self.host_edit = QLineEdit("localhost")
        self.port_edit = QLineEdit("5432")
        self.db_edit = QLineEdit("airport")
        self.user_edit = QLineEdit("postgres")
        self.pw_edit = QLineEdit("");
        self.pw_edit.setEchoMode(QLineEdit.Password)
        self.ssl_edit = QLineEdit("prefer")

        conn_form = QFormLayout()
        conn_form.addRow("Driver:", self.driver_cb)
        conn_form.addRow("Host:", self.host_edit)
        conn_form.addRow("Port:", self.port_edit)
        conn_form.addRow("DB name:", self.db_edit)
        conn_form.addRow("User:", self.user_edit)
        conn_form.addRow("Password:", self.pw_edit)
        conn_form.addRow("sslmode:", self.ssl_edit)

        conn_box = QGroupBox("Параметры подключения (SQLAlchemy)")
        conn_box.setLayout(conn_form)

        self.connect_btn = QPushButton("Подключиться")
        self.connect_btn.clicked.connect(self.do_connect)
        self.disconnect_btn = QPushButton("Отключиться")
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.clicked.connect(self.do_disconnect)

        self.create_btn = QPushButton("Сбросить и создать БД (CREATE)")
        self.create_btn.setEnabled(False)
        self.create_btn.clicked.connect(self.reset_db)

        self.demo_btn = QPushButton("Добавить демо-данные (INSERT)")
        self.demo_btn.setEnabled(False)
        self.demo_btn.clicked.connect(self.add_demo)

        top_btns = QHBoxLayout()
        top_btns.addWidget(self.connect_btn)
        top_btns.addWidget(self.disconnect_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(conn_box)
        layout.addLayout(top_btns)
        layout.addWidget(self.create_btn)
        layout.addWidget(self.demo_btn)
        layout.addWidget(QLabel("Лог:"))
        layout.addWidget(self.log)

    def current_cfg(self) -> PgConfig:
        try:
            port = int(self.port_edit.text().strip())
        except ValueError:
            port = 5432
        return PgConfig(
            host=self.host_edit.text().strip() or "localhost",
            port=port,
            dbname=self.db_edit.text().strip() or "airport",
            user=self.user_edit.text().strip() or "postgres",
            password=self.pw_edit.text(),
            sslmode=self.ssl_edit.text().strip() or "prefer",
            driver=self.driver_cb.currentData(),
        )

    def do_connect(self):
        main = self.window()  # <-- было parent().parent()
        # если уже подключены — просим отключиться
        if getattr(main, "engine", None) is not None:
            self.log.append("Уже подключено. Нажмите «Отключиться» для переподключения.")
            return
        cfg = self.current_cfg()
        try:
            engine = make_engine(cfg)
            md, tables = build_metadata()
            main.attach_engine(engine, md, tables)
            self.log.append(
                f"Успешное подключение: {cfg.driver} → {cfg.host}:{cfg.port}/{cfg.dbname} (user={cfg.user})"
            )
            self.create_btn.setEnabled(True)
            self.demo_btn.setEnabled(True)
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            main.ensure_data_tabs()
        except SQLAlchemyError as e:
            self.log.append(f"Ошибка подключения: {e}")

    def do_disconnect(self):
        main = self.window()  # <-- было parent().parent()
        main.disconnect_db()
        self.log.append("Соединение закрыто.")

    def reset_db(self):
        main = self.window()  # <-- было parent().parent()
        if getattr(main, "engine", None) is None:
            QMessageBox.warning(self, "Схема", "Нет подключения к БД.")
            return
        if drop_and_create_schema_sa(main.engine, main.md):
            self.log.append("Схема БД создана: aircraft, flights, passengers, crew, crew_member.")
            main.refresh_all_models()
            main.refresh_combos()
        else:
            QMessageBox.critical(self, "Схема", "Ошибка при создании схемы. См. консоль/лог.")

    def add_demo(self):
        main = self.window()  # <-- было parent().parent()
        if getattr(main, "engine", None) is None:
            QMessageBox.warning(self, "Демо", "Нет подключения к БД.")
            return
        if insert_demo_data_sa(main.engine, main.tables):
            self.log.append("Добавлены демонстрационные данные (INSERT).")
            main.refresh_all_models()
            main.refresh_combos()
        else:
            QMessageBox.warning(self, "Демо", "Часть данных не добавлена. См. консоль.")


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


# -------------------------------
# Точка входа
# -------------------------------
def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
