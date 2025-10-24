# ===== Base =====
from datetime import date, time

# ===== PySide6 =====
from PySide6.QtCore import QDate, QTime, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QLineEdit, QMessageBox, QSpinBox,
    QDateEdit, QComboBox, QTableView,
    QTimeEdit, QHeaderView
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
        self.table = "flights"

        self.model = SATableModel(engine, self.tables["flights"], self)

        self.add_record_btn.clicked.connect(self.add_flight)
        self.clear_form_btn.clicked.connect(self.clear_form)
        self.delete_record_btn.clicked.connect(self.delete_selected)

        self.load_table_structure()

        self.add_table.setModel(self.model)
        self.add_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.add_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        apply_compact_table_view(self.add_table)

        self.read_table.setModel(self.model)
        self.read_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.read_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        apply_compact_table_view(self.read_table)

        self.read_table.setModel(self.model)
        self.read_table.setSortingEnabled(True)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.add_table.setModel(self.proxy_model)
        self.add_table.setSortingEnabled(True)

        def on_header_clicked(self, logical_index):
            current_order = self.proxy_model.sortOrder()
            new_order = Qt.SortOrder.DescendingOrder if current_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
            self.proxy_model.sort(logical_index, new_order)

        header = self.add_table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.proxy_model.sort(0, Qt.SortOrder.AscendingOrder)

        self.on_header_clicked = on_header_clicked.__get__(self)

    def load_table_structure(self):
        """Загружает структуру таблицы - столбцы как строки"""
        try:
            from PySide6.QtGui import QStandardItemModel, QStandardItem

            # Создаем модель для отображения структуры
            structure_model = QStandardItemModel()
            structure_model.setHorizontalHeaderLabels(["Название столбца", "Тип данных", "Ограничения"])

            # Получаем информацию о столбцах таблицы
            table = self.tables["flights"]
            for i, column in enumerate(table.columns):
                # Добавляем строку с информацией о столбце
                row_items = [
                    QStandardItem(column.name),  # Название столбца
                    QStandardItem(str(column.type)),  # Тип данных
                    QStandardItem(self._get_column_constraints(column))  # Ограничения
                ]

                # Сохраняем имя столбца в данных для последующего использования
                for item in row_items:
                    item.setData(column.name, Qt.UserRole)

                structure_model.appendRow(row_items)

            self.structure_table.setModel(structure_model)
            self.structure_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            apply_compact_table_view(self.structure_table)

            self.delete_column_btn.setEnabled(False)
            self.edit_column_btn.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка загрузки структуры", str(e))

    def add_form_rows(self):
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

        self.add_form_layout.addRow("Самолет:", self.aircraft_combo)
        self.add_form_layout.addRow("Дата вылета:", self.departure_date_edit)
        self.add_form_layout.addRow("Время вылета:", self.departure_time_edit)
        self.add_form_layout.addRow("Аэропорт вылета:", self.departure_airport_edit)
        self.add_form_layout.addRow("Аэропорт прибытия:", self.arrival_airport_edit)
        self.add_form_layout.addRow("Время полета:", self.flight_time_edit)

    def refresh_aircraft_combo(self):
        self.aircraft_combo.clear()
        try:
            with self.engine.connect() as conn:
                result = conn.execute(self.tables["aircraft"].select().order_by(self.tables["aircraft"].c.model))
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
                conn.execute(insert(self.tables["flights"]).values(
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

        idx = self.add_table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите рейс")
            return

        flight_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.tables["flights"]).where(
                    self.tables["flights"].c.flight_id == flight_id
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
