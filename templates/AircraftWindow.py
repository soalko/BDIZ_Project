# ===== PySide6 =====
from PySide6.QtCore import QDate, QSortFilterProxyModel
from PySide6.QtGui import Qt
from PySide6.QtWidgets import (
    QLineEdit, QMessageBox,
    QSpinBox, QTableView, QHeaderView,
)

# ===== SQLAlchemy =====
from sqlalchemy import insert, delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# ===== Files =====
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.models import SATableModel
from templates.BaseTab import BaseTab
from templates.modes import AppMode

try:
    from styles import apply_compact_table_view
except ImportError:
    def apply_compact_table_view(table_widget):
        try:
            table_widget.setAlternatingRowColors(True)
            if hasattr(table_widget, "setShowGrid"):
                table_widget.setShowGrid(False)
            header = table_widget.horizontalHeader()
            header.setStretchLastSection(True)
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        except Exception:
            pass


# -------------------------------
# Вкладка «Самолеты»
# -------------------------------
class AircraftTab(BaseTab):
    def __init__(self, engine, tables, parent=None):
        super().__init__(engine, tables, parent)

        self.model = SATableModel(engine, self.tables["aircraft"], self)

        self.add_record_btn.clicked.connect(self.add_aircraft)
        self.clear_form_btn.clicked.connect(self.clear_form)
        self.delete_record_btn.clicked.connect(self.delete_selected)

        self.load_table_structure()

        self.add_table.setModel(self.model)
        self.add_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.add_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        apply_compact_table_view(self.add_table)

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


        self.update_ui_for_mode()

    def load_table_structure(self):
        """Загружает структуру таблицы - столбцы как строки"""
        try:
            from PySide6.QtGui import QStandardItemModel, QStandardItem

            # Создаем модель для отображения структуры
            structure_model = QStandardItemModel()
            structure_model.setHorizontalHeaderLabels(["Название столбца", "Тип данных", "Ограничения"])

            # Получаем информацию о столбцах таблицы
            table = self.tables["aircraft"]
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

        self.add_form_layout.addRow("Модель:", self.model_edit)
        self.add_form_layout.addRow("Год выпуска:", self.year_edit)
        self.add_form_layout.addRow("Количество мест:", self.seats_edit)
        self.add_form_layout.addRow("Вместимость багажа:", self.baggage_edit)

    def add_aircraft(self):
        if self.current_mode != AppMode.ADD:
            return

        model = self.model_edit.text().strip()
        year = self.year_edit.value()
        seats = self.seats_edit.value()
        baggage = self.baggage_edit.value()

        if not model:
            QMessageBox.warning(self, "Ввод", "Модель самолета обязательна (NOT NULL)")
            return

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.tables["aircraft"]).values(
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
        if self.current_mode != AppMode.ADD:
            return

        idx = self.add_table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите самолет")
            return

        aircraft_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.tables["aircraft"]).where(
                    self.tables["aircraft"].c.aircraft_id == aircraft_id
                ))
            self.model.refresh()
            self.window().refresh_combos()
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def clear_form(self):
        self.model_edit.clear()
        self.year_edit.setValue(2000)
        self.seats_edit.setValue(150)
        self.baggage_edit.setValue(1000)