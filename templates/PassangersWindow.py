# ===== PySide6 =====
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QPushButton, QMessageBox,
    QCheckBox, QTableView
)


# ===== SQLAlchemy =====
from sqlalchemy import (
    insert, delete
)

from sqlalchemy.exc import IntegrityError, SQLAlchemyError


# ===== Files =====
from db.models import SATableModel



# -------------------------------
# Вкладка «Пассажиры»
# -------------------------------
class PassengersTab(QWidget):
    def __init__(self, engine, tables, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.t = tables
        self.model = SATableModel(engine, self.t["passengers"], self)

        # Создание виджетов для ввода данных
        self.is_dependent_checkbox = QCheckBox("Зависимый пассажир")
        self.is_dependent_checkbox.setChecked(False)

        # Форма для ввода данных
        form = QFormLayout()
        form.addRow("Тип пассажира:", self.is_dependent_checkbox)

        # Кнопки
        self.add_btn = QPushButton("Добавить пассажира (INSERT)")
        self.add_btn.clicked.connect(self.add_passenger)
        self.del_btn = QPushButton("Удалить выбранного пассажира")
        self.del_btn.clicked.connect(self.delete_selected)

        btns = QHBoxLayout()
        btns.addWidget(self.add_btn)
        btns.addWidget(self.del_btn)

        # Таблица
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        # Основной layout
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btns)
        layout.addWidget(self.table)

    def add_passenger(self):
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
        """Очистка формы после успешного добавления"""
        self.is_dependent_checkbox.setChecked(False)