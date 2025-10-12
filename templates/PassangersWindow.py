# ===== PySide6 =====
from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QPushButton, QMessageBox,
    QCheckBox, QTableView, QHeaderView
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
# Вкладка «Пассажиры»
# --------------------------------
class PassengersTab(BaseTab):
    def __init__(self, engine, tables, parent=None):
        super().__init__(engine, tables, parent)

        self.model = SATableModel(engine, self.t["passengers"], self)

        self.form_widget = QWidget()
        self.buttons_widget = QWidget()

        self.is_dependent_checkbox = QCheckBox("Зависимый пассажир")
        self.is_dependent_checkbox.setChecked(False)

        self.form = QFormLayout(self.form_widget)
        self.form.addRow("Тип пассажира:", self.is_dependent_checkbox)

        self.add_btn = QPushButton("Добавить пассажира (INSERT)")
        self.add_btn.clicked.connect(self.add_passenger)
        self.del_btn = QPushButton("Удалить выбранного пассажира")
        self.del_btn.clicked.connect(self.delete_selected)

        self.btns = QHBoxLayout(self.buttons_widget)
        self.btns.addWidget(self.add_btn)
        self.btns.addWidget(self.del_btn)

        self.table = QTableView()
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

        self.add_record_btn.clicked.connect(self.add_passenger)
        self.clear_form_btn.clicked.connect(self.clear_form)
        self.delete_record_btn.clicked.connect(self.delete_selected)

        self.main_layout.addWidget(self.form_widget)
        self.main_layout.addWidget(self.buttons_widget)
        self.main_layout.addWidget(self.table)

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

    def add_passenger(self):
        if self.current_mode != AppMode.ADD:
            return

        is_dependent = self.is_dependent_checkbox.isChecked()

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.t["passengers"]).values(
                    is_dependent=is_dependent
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

        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите пассажира")
            return

        passenger_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.t["passengers"]).where(
                    self.t["passengers"].c.passenger_id == passenger_id
                ))
            self.model.refresh()
            self.window().refresh_combos()
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def clear_form(self):
        self.is_dependent_checkbox.setChecked(False)