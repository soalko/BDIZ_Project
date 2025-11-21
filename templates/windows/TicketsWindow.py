# ===== PySide6 =====
from PySide6.QtCore import QSortFilterProxyModel, Qt, QDate, QTime
from PySide6.QtWidgets import (
    QLineEdit, QMessageBox,
    QComboBox, QCheckBox, QTableView, QHeaderView, QDateEdit, QTimeEdit, QSpinBox
)
from styles.styles import apply_compact_table_view

# ===== SQLAlchemy =====
from sqlalchemy import (
    insert, delete
)

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# ===== Files =====
from db.models import SATableModel
from templates.tabs.AddWindow import AddWindow
from templates.tabs.BaseTab import BaseTab
from templates.tabs.EditWindow import EditWindow
from templates.tabs.ReadWindow import ReadWindow

# --------------------------------
# Вкладка «Билеты»
# -------------------------------
class TicketsTab(BaseTab):
    def __init__(self, engine, tables, parent=None):
        super().__init__(engine, tables, "tickets", parent)
        self.model = SATableModel(engine, self.tables["tickets"], self)
        self.update_model()
        self.update_ui_for_mode()

    def create_add_window(self):
        return TicketsAddWindow(self.engine, self.tables, self.table, self)


class TicketsReadWindow(ReadWindow):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(engine, tables, table, parent)
        self.setup_tickets_ui()

    def setup_tickets_ui(self):
        from db.models import SATableModel
        self.model = SATableModel(self.engine, self.tables[self.table], self)

        self.read_table.setModel(self.model)
        self.read_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.read_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        apply_compact_table_view(self.read_table)
        self.read_table.setSortingEnabled(True)


class TicketsEditWindow(EditWindow):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(engine, tables, table, parent)
        self.load_table_structure()


class TicketsAddWindow(AddWindow):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(engine, tables, table, parent)
        self.model = SATableModel(self.engine, self.tables[self.table], self)
        self.setup_tickets_ui()

    def setup_tickets_ui(self):
        from db.models import SATableModel
        self.model = SATableModel(self.engine, self.tables[self.table], self)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.add_table.setModel(self.proxy_model)
        self.add_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.add_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        apply_compact_table_view(self.add_table)
        self.add_table.setSortingEnabled(True)

        header = self.add_table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.proxy_model.sort(0, Qt.SortOrder.AscendingOrder)

        header.sectionClicked.connect(self.on_header_clicked)

    def refresh_form_widgets(self):
        """Обновляет виджеты формы при каждом открытии вкладки"""
        super().refresh_form_widgets()  # Вызываем родительский метод

        # Обновляем таблицу данных
        if hasattr(self, 'model') and self.model:
            self.model.refresh()

    # Для CrewWindow.py можно добавить кастомное обновление комбобоксов:
    def _refresh_combobox_data(self, combo: QComboBox, column_name: str):
        """Переопределяем для кастомного обновления комбобоксов"""
        if column_name == 'aircraft_id':
            # Кастомная логика для обновления комбобокса самолетов
            super()._refresh_combobox_data(combo, column_name)

    def on_header_clicked(self, logical_index):
        current_order = self.proxy_model.sortOrder()
        new_order = Qt.SortOrder.DescendingOrder if current_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        self.proxy_model.sort(logical_index, new_order)

    def connect_buttons(self):
        self.add_record_btn.clicked.connect(self.add_ticket)
        self.clear_form_btn.clicked.connect(self.clear_form)
        self.delete_record_btn.clicked.connect(self.delete_selected)

    def add_ticket(self):
        # Получаем данные из автоматически созданной формы
        form_data = self.get_form_data()

        # Валидация данных
        seat_number = form_data.get('seat_number', '')

        if not seat_number:
            QMessageBox.warning(self, "Ввод", "Номер места обязателен")
            return

        if not isinstance(seat_number, str):
            QMessageBox.warning(self, "Ввод", "Номер места должен быть текстовым значением")
            return

        seat_number = seat_number.strip().upper()

        if not (len(seat_number) >= 2 and len(seat_number) <= 4 and
                seat_number[:-1].isdigit() and seat_number[-1].isalpha()):
            QMessageBox.warning(self, "Ввод", "Номер места должен быть в формате: число + буква (например: 12A)")
            return

        # Обновляем данные формы с проверенными значениями
        form_data['seat_number'] = seat_number

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.tables["tickets"]).values(**form_data))
            self.model.refresh()
            self.clear_form()

            parent_window = self.window()
            if hasattr(parent_window, 'refresh_combos'):
                parent_window.refresh_combos()

        except IntegrityError as e:
            QMessageBox.critical(self, "Ошибка INSERT (UNIQUE/FOREIGN KEY/CHECK constraint)", str(e.orig))
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка INSERT", str(e))

    def delete_selected(self):
        idx = self.add_table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите билет")
            return

        source_index = self.proxy_model.mapToSource(idx)
        ticket_id = self.model.pk_value_at(source_index.row())

        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.tables["tickets"]).where(
                    self.tables["tickets"].c.ticket_id == ticket_id
                ))
            self.model.refresh()

            parent_window = self.window()
            if hasattr(parent_window, 'refresh_combos'):
                parent_window.refresh_combos()

        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))