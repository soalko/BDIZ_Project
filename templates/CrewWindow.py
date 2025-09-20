# ===== PySide6 =====
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QPushButton, QMessageBox,
    QComboBox, QTableView
)


# ===== SQLAlchemy =====
from sqlalchemy import (
    insert, delete
)

from sqlalchemy.exc import IntegrityError, SQLAlchemyError


# ===== Files =====
from db.models import SATableModel



# -------------------------------
# Вкладка «Экипаж»
# -------------------------------
class CrewTab(QWidget):
    def __init__(self, engine, tables, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.t = tables
        self.model = SATableModel(engine, self.t["crew"], self)

        # Создание виджетов для ввода данных
        self.aircraft_combo = QComboBox()

        # Форма для ввода данных
        form = QFormLayout()
        form.addRow("Самолет:", self.aircraft_combo)

        # Кнопки
        self.add_btn = QPushButton("Добавить экипаж (INSERT)")
        self.add_btn.clicked.connect(self.add_crew)
        self.del_btn = QPushButton("Удалить выбранный экипаж")
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

        # Загрузка данных в комбобокс
        self.refresh_aircraft_combo()

    def refresh_aircraft_combo(self):
        """Обновление списка самолетов в комбобоксе"""
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
        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите экипаж")
            return

        crew_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
                # Сначала проверяем, есть ли члены экипажа
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
        """Очистка формы после успешного добавления"""
        # Не очищаем комбобокс, чтобы можно было быстро добавить несколько экипажей
        pass