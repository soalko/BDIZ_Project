# ===== PySide6 =====
from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QPushButton, QMessageBox,
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
# Вкладка «Экипаж»
# --------------------------------
class CrewTab(BaseTab):
    def __init__(self, engine, tables, parent=None):
        super().__init__(engine, tables, parent)

        self.model = SATableModel(engine, self.t["crew"], self)

        self.form_widget = QWidget()
        self.buttons_widget = QWidget()

        self.aircraft_combo = QComboBox()

        self.form = QFormLayout(self.form_widget)
        self.form.addRow("Самолет:", self.aircraft_combo)

        self.add_btn = QPushButton("Добавить экипаж (INSERT)")
        self.add_btn.clicked.connect(self.add_crew)
        self.del_btn = QPushButton("Удалить выбранный экипаж")
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

        self.add_record_btn.clicked.connect(self.add_crew)
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
        if self.current_mode != AppMode.ADD:
            return

        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите экипаж")
            return

        crew_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
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
        pass