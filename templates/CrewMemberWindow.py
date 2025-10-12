# ===== PySide6 =====
from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QPushButton, QMessageBox,
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

        self.model = SATableModel(engine, self.t["crew_member"], self)

        self.form_widget = QWidget()
        self.buttons_widget = QWidget()

        self.crew_combo = QComboBox()
        self.job_position_edit = QLineEdit()
        self.job_position_edit.setMaxLength(50)

        self.form = QFormLayout(self.form_widget)
        self.form.addRow("Экипаж:", self.crew_combo)
        self.form.addRow("Должность:", self.job_position_edit)

        self.add_btn = QPushButton("Добавить члена экипажа (INSERT)")
        self.add_btn.clicked.connect(self.add_crew_member)
        self.del_btn = QPushButton("Удалить выбранного члена экипажа")
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

        self.add_record_btn.clicked.connect(self.add_crew_member)
        self.clear_form_btn.clicked.connect(self.clear_form)
        self.delete_record_btn.clicked.connect(self.delete_selected)

        self.main_layout.addWidget(self.form_widget)
        self.main_layout.addWidget(self.buttons_widget)
        self.main_layout.addWidget(self.table)

        self.refresh_crew_combo()

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

    def refresh_crew_combo(self):
        self.crew_combo.clear()
        try:
            with self.engine.connect() as conn:
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
        if self.current_mode != AppMode.ADD:
            return

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
        self.job_position_edit.clear()