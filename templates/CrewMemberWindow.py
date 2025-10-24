# ===== PySide6 =====
from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QLineEdit, QMessageBox,
    QComboBox, QTableView, QHeaderView
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
# Вкладка «Члены Экипажа»
# -------------------------------
class CrewMembersTab(BaseTab):
    def __init__(self, engine, tables, parent=None):
        super().__init__(engine, tables, parent)

        self.table = "crew_members"

        self.model = SATableModel(engine, self.tables["crew_member"], self)

        self.add_record_btn.clicked.connect(self.add_crew_member)
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

        self.refresh_crew_combo()

        self.update_ui_for_mode()

    def load_table_structure(self):
        """Загружает структуру таблицы - столбцы как строки"""
        try:
            from PySide6.QtGui import QStandardItemModel, QStandardItem

            # Создаем модель для отображения структуры
            structure_model = QStandardItemModel()
            structure_model.setHorizontalHeaderLabels(["Название столбца", "Тип данных", "Ограничения"])

            # Получаем информацию о столбцах таблицы
            table = self.tables["crew"]
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
        self.crew_combo = QComboBox()
        self.job_position_edit = QLineEdit()
        self.job_position_edit.setMaxLength(50)
        self.add_form_layout.addRow("Экипаж:", self.crew_combo)
        self.add_form_layout.addRow("Должность:", self.job_position_edit)

    def update_ui_for_mode(self):
        super().update_ui_for_mode()

    def refresh_crew_combo(self):
        self.crew_combo.clear()
        try:
            with self.engine.connect() as conn:
                query = self.tables["crew"].join(
                    self.tables["aircraft"],
                    self.tables["crew"].c.aircraft_id == self.tables["aircraft"].c.aircraft_id
                ).select().order_by(self.tables["crew"].c.crew_id)

                result = conn.execute(query)
                for row in result:
                    self.crew_combo.addItem(
                        f"Экипаж {row.crew_id} (Самолет: {row.model}, ID: {row.aircraft_id})",
                        row.crew_id
                    )
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка загрузки экипажей", str(e))

    def add_crew_member(self):
        if self.current_mode != AppMode.ADD:
            return

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
                conn.execute(insert(self.tables["crew_member"]).values(
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
        if self.current_mode != AppMode.ADD:
            return

        idx = self.add_table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите члена экипажа")
            return

        member_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.tables["crew_member"]).where(
                    self.tables["crew_member"].c.member_id == member_id
                ))
            self.model.refresh()
            self.window().refresh_combos()
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def clear_form(self):
        self.job_position_edit.clear()
