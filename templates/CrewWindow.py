# ===== PySide6 =====
from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QMessageBox, QComboBox, QTableView, QHeaderView
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
# Вкладка «Экипаж»
# --------------------------------
class CrewTab(BaseTab):
    def __init__(self, engine, tables, parent=None):
        super().__init__(engine, tables, parent)

        self.model = SATableModel(engine, self.tables["crew"], self)

        self.add_record_btn.clicked.connect(self.add_crew)
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

    def load_table_structure(self):
        """Загружает структуру таблицы - столбцы как строки"""
        try:
            from PySide6.QtGui import QStandardItemModel, QStandardItem

            # Создаем модель для отображения структуры
            structure_model = QStandardItemModel()
            structure_model.setHorizontalHeaderLabels(["Название столбца", "Тип данных", "Ограничения"])

            # Получаем информацию о столбцах таблицы
            table = self.tables["crew_member"]
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

        self.add_form_layout.addRow("Самолет:", self.aircraft_combo)

    def refresh_aircraft_combo(self):
        self.aircraft_combo.clear()
        try:
            with self.engine.connect() as conn:
                result = conn.execute(self.tables["aircraft"].select().order_by(self.tables["aircraft"].c.model))
                for row in result:
                    self.aircraft_combo.addItem(
                        f"{row.model} (ID: {row.aircraft_id}, Мест: {row.seats_amount})",
                        row.aircraft_id
                    )
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка загрузки самолетов", str(e))

    def add_crew(self):
        if self.current_mode != AppMode.ADD:
            return

        if self.aircraft_combo.currentIndex() == -1:
            QMessageBox.warning(self, "Ввод", "Необходимо выбрать самолет")
            return

        aircraft_id = self.aircraft_combo.currentData()

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.tables["crew"]).values(
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
        if self.current_mode != AppMode.ADD:
            return

        idx = self.add_table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите экипаж")
            return

        crew_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
                result = conn.execute(
                    self.tables["crew_member"].select().where(
                        self.tables["crew_member"].c.crew_id == crew_id
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

                conn.execute(delete(self.tables["crew"]).where(
                    self.tables["crew"].c.crew_id == crew_id
                ))
            self.model.refresh()
            self.window().refresh_combos()
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def clear_form(self):
        pass