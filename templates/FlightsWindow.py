# ===== Base =====
from datetime import date, time

# ===== PySide6 =====
from PySide6.QtCore import QDate, QTime, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QPushButton, QMessageBox, QSpinBox,
    QDateEdit, QComboBox, QTableView, QTimeEdit, QHeaderView
)
from styles.styles import apply_compact_table_view


# ===== SQLAlchemy =====
from sqlalchemy import (
    insert, delete
)

from sqlalchemy.exc import IntegrityError, SQLAlchemyError


# ===== Files =====
from db.models import SATableModel
from templates.BaseTab import BaseTab
from templates.modes import AppMode



# -------------------------------
# Вкладка «Рейсы»
# --------------------------------
class FlightsTab(BaseTab):
    def __init__(self, engine, tables, parent=None):
        super().__init__(engine, tables, parent)

        self.model = SATableModel(engine, self.t["flights"], self)

        self.form_widget = QWidget()
        self.buttons_widget = QWidget()

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
        self.flight_time_edit.setRange(1, 1440)
        self.flight_time_edit.setValue(120)
        self.flight_time_edit.setSuffix(" минут")

        self.form = QFormLayout(self.form_widget)
        self.form.addRow("Самолет:", self.aircraft_combo)
        self.form.addRow("Дата вылета:", self.departure_date_edit)
        self.form.addRow("Время вылета:", self.departure_time_edit)
        self.form.addRow("Аэропорт вылета:", self.departure_airport_edit)
        self.form.addRow("Аэропорт прибытия:", self.arrival_airport_edit)
        self.form.addRow("Время полета:", self.flight_time_edit)

        self.add_btn = QPushButton("Добавить рейс (INSERT)")
        self.add_btn.clicked.connect(self.add_flight)
        self.del_btn = QPushButton("Удалить выбранный рейс")
        self.del_btn.clicked.connect(self.delete_selected)

        self.btns = QHBoxLayout(self.buttons_widget)
        self.btns.addWidget(self.add_btn)
        self.btns.addWidget(self.del_btn)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        apply_compact_table_view(self.table)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.table.setModel(self.proxy_model)
        self.table.setSortingEnabled(True)

        def on_header_clicked(self, logical_index):
            current_order = self.proxy_model.sortOrder()
            new_order = Qt.SortOrder.DescendingOrder if current_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
            self.proxy_model.sort(logical_index, new_order)

        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.proxy_model.sort(0, Qt.SortOrder.AscendingOrder)

        self.on_header_clicked = on_header_clicked.__get__(self)

        self.add_record_btn.clicked.connect(self.add_flight)
        self.clear_form_btn.clicked.connect(self.clear_form)
        self.delete_record_btn.clicked.connect(self.delete_selected)

        self.main_layout.addWidget(self.form_widget)
        self.main_layout.addWidget(self.buttons_widget)
        self.main_layout.addWidget(self.table)

        self.refresh_aircraft_combo()

        self.update_ui_for_mode()

    def set_mode(self, mode: AppMode):
        super().set_mode(mode)
        self.update_ui_for_mode()

    def update_ui_for_mode(self):
        super().update_ui_for_mode()

        if self.current_mode == AppMode.ADD:
            self.form_widget.setVisible(True)
            self.buttons_widget.setVisible(True)
        elif self.current_mode == AppMode.READ:
            self.form_widget.setVisible(False)
            self.buttons_widget.setVisible(False)
        elif self.current_mode == AppMode.EDIT:
            self.form_widget.setVisible(False)
            self.buttons_widget.setVisible(False)

    def refresh_aircraft_combo(self):
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
        if self.current_mode != AppMode.ADD:
            return

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
        if self.current_mode != AppMode.ADD:
            return

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
        self.departure_airport_edit.clear()
        self.arrival_airport_edit.clear()
        self.flight_time_edit.setValue(120)
        self.departure_date_edit.setDate(QDate.currentDate())
        self.departure_time_edit.setTime(QTime(12, 0))