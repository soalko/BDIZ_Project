# ===== PySide6 =====
from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QPushButton, QMessageBox,
    QComboBox, QCheckBox, QTableView, QHeaderView
)


# ===== SQLAlchemy =====
from sqlalchemy import (
    insert, delete
)

from sqlalchemy.exc import IntegrityError, SQLAlchemyError


# ===== Files =====
from db.models import SATableModel



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

        # Добавляем прокси-модель для фильтрации и сортировки
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.table.setModel(self.proxy_model)
        self.table.setSortingEnabled(True)

        def on_header_clicked(self, logical_index):
            # Получаем и меняем текущее направление сортировки
            current_order = self.proxy_model.sortOrder()
            new_order = Qt.SortOrder.DescendingOrder if current_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
            self.proxy_model.sort(logical_index, new_order)

        # Дополнительные настройки для лучшего отображения
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.proxy_model.sort(0, Qt.SortOrder.AscendingOrder)

        # Привязываем метод к классу
        self.on_header_clicked = on_header_clicked.__get__(self)

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