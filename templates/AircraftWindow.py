# ===== PySide6 =====
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QPushButton,
    QMessageBox, QSpinBox, QTableView
)
from styles.styles import apply_compact_table_view

# ===== SQLAlchemy ======
from sqlalchemy import insert, delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# ===== Files =====
from db.models import SATableModel


# -------------------------------
# Вкладка «Самолеты»
# -------------------------------
class AircraftTab(QWidget):
    def __init__(self, engine, tables, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.t = tables
        self.model = SATableModel(engine, self.t["aircraft"], self)

        # Создание виджетов для ввода данных
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

        # Форма для ввода данных
        form = QFormLayout()
        form.addRow("Модель:", self.model_edit)
        form.addRow("Год выпуска:", self.year_edit)
        form.addRow("Количество мест:", self.seats_edit)
        form.addRow("Вместимость багажа:", self.baggage_edit)

        # Кнопки
        self.add_btn = QPushButton("Добавить самолет (INSERT)")
        self.add_btn.clicked.connect(self.add_aircraft)
        self.del_btn = QPushButton("Удалить выбранный самолет")
        self.del_btn.clicked.connect(self.delete_selected)

        btns = QHBoxLayout()
        btns.addWidget(self.add_btn)
        btns.addWidget(self.del_btn)

        # Таблица
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        apply_compact_table_view(self.table)

        # Основной layout
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btns)
        layout.addWidget(self.table)

    def add_aircraft(self):
        model = self.model_edit.text().strip()
        year = self.year_edit.value()
        seats = self.seats_edit.value()
        baggage = self.baggage_edit.value()

        if not model:
            QMessageBox.warning(self, "Ввод", "Модель самолета обязательна (NOT NULL)")
            return

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.t["aircraft"]).values(
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
        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите самолет")
            return

        aircraft_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.t["aircraft"]).where(
                    self.t["aircraft"].c.aircraft_id == aircraft_id
                ))
            self.model.refresh()
            self.window().refresh_combos()
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def clear_form(self):
        """Очистка формы после успешного добавления"""
        self.model_edit.clear()
        self.year_edit.setValue(2000)
        self.seats_edit.setValue(150)
        self.baggage_edit.setValue(1000)
