# ===== PySide6 =====
from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QPushButton, QMessageBox,
    QComboBox, QCheckBox, QTableView, QHeaderView
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



# --------------------------------
# Вкладка «Билеты»
# -------------------------------
class TicketsTab(BaseTab):
    def __init__(self, engine, tables, parent=None):
        super().__init__(engine, tables, parent)

        self.model = SATableModel(engine, self.t["tickets"], self)

        self.form_widget = QWidget()
        self.buttons_widget = QWidget()

        self.flight_combo = QComboBox()
        self.passenger_combo = QComboBox()
        self.seat_number_edit = QLineEdit()
        self.seat_number_edit.setMaxLength(4)
        self.has_baggage_checkbox = QCheckBox("Есть багаж")
        self.has_baggage_checkbox.setChecked(False)

        self.form = QFormLayout(self.form_widget)
        self.form.addRow("Рейс:", self.flight_combo)
        self.form.addRow("Пассажир:", self.passenger_combo)
        self.form.addRow("Номер места:", self.seat_number_edit)
        self.form.addRow("Багаж:", self.has_baggage_checkbox)

        self.add_btn = QPushButton("Добавить билет (INSERT)")
        self.add_btn.clicked.connect(self.add_ticket)
        self.del_btn = QPushButton("Удалить выбранный билет")
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

        self.add_record_btn.clicked.connect(self.add_ticket)
        self.clear_form_btn.clicked.connect(self.clear_form)
        self.delete_record_btn.clicked.connect(self.delete_selected)

        self.main_layout.addWidget(self.form_widget)
        self.main_layout.addWidget(self.buttons_widget)
        self.main_layout.addWidget(self.table)

        self.refresh_flights_combo()
        self.refresh_passengers_combo()

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

    def refresh_flights_combo(self):
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
        if self.current_mode != AppMode.ADD:
            return

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
        if self.current_mode != AppMode.ADD:
            return

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