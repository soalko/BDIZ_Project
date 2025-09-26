# ===== Base =====
from datetime import date, time

# ===== PySide6 =====
from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QPushButton, QMessageBox, QSpinBox,
    QDateEdit, QComboBox, QTableView, QTimeEdit
)
from styles.styles import apply_compact_table_view


# ===== SQLAlchemy =====
from sqlalchemy import (
    insert, delete
)

from sqlalchemy.exc import IntegrityError, SQLAlchemyError


# ===== Files =====
from db.models import SATableModel



# -------------------------------
# Вкладка «Рейсы»
# --------------------------------
class FlightsTab(QWidget):
    def __init__(self, engine, tables, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.t = tables
        self.model = SATableModel(engine, self.t["flights"], self)

        # Создание виджетов для ввода данных
        self.aircraft_combo = QComboBox()
        self.departure_date_edit = QDateEdit()
        self.departure_date_edit.setCalendarPopup(False)
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
        apply_compact_table_view(self.table)

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