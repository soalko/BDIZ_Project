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

from styles import apply_compact_table_view

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.models import SATableModel
from templates.tabs.BaseTab import BaseTab, ReadWindow, EditWindow, AddWindow


class ValidationError(Exception):
    """Кастомное исключение для ошибок валидации"""

    def __init__(self, message, field_name=None):
        super().__init__(message)
        self.field_name = field_name
        self.message = message


# -------------------------------
# Вкладка «Самолеты»
# -------------------------------
class AircraftTab(BaseTab):
    def __init__(self, engine, tables, parent=None):
        super().__init__(engine, tables, "aircraft", parent)
        self.model = SATableModel(engine, self.tables["aircraft"], self)
        self.update_model()
        self.update_ui_for_mode()

    def create_add_window(self):
        return AircraftAddWindow(self.engine, self.tables, self.table, self)


class AircraftReadWindow(ReadWindow):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(engine, tables, table, parent)


class AircraftEditWindow(EditWindow):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(engine, tables, table, parent)
        self.load_table_structure()


class AircraftAddWindow(AddWindow):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(engine, tables, table, parent)
        self.model = SATableModel(self.engine, self.tables[self.table], self)
        self.setup_aircraft_ui()

    def setup_aircraft_ui(self):
        # Настраиваем прокси-модель для сортировки
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.add_table.setModel(self.proxy_model)
        self.add_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.add_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        apply_compact_table_view(self.add_table)
        self.add_table.setSortingEnabled(True)

        # Настраиваем заголовок для сортировки
        header = self.add_table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.proxy_model.sort(0, Qt.SortOrder.AscendingOrder)

        # Подключаем обработчик клика по заголовку
        header.sectionClicked.connect(self.on_header_clicked)

    def refresh_form_widgets(self):
        """Обновляет виджеты формы при каждом открытии вкладки"""
        super().refresh_form_widgets()  # Вызываем родительский метод

        # ДОБАВЛЕНО: Обновляем спинбоксы с актуальными значениями
        self._refresh_spinboxes()

        # ДОБАВЛЕНО: Обновляем таблицу данных
        if hasattr(self, 'model') and self.model:
            self.model.refresh()

    def _refresh_spinboxes(self):
        """Обновляет значения в спинбоксах"""
        try:
            # Обновляем год выпуска - текущий год
            if hasattr(self, 'input_widgets'):
                for column_name, widget in self.input_widgets.items():
                    if isinstance(widget, QSpinBox):
                        if column_name == 'year':
                            current_year = QDate.currentDate().year()
                            widget.setMaximum(current_year)
                        elif column_name == 'seats_amount':
                            widget.setValue(150)  # Значение по умолчанию
                        elif column_name == 'baggage_capacity':
                            widget.setValue(1000)  # Значение по умолчанию
        except Exception as e:
            print(f"Ошибка при обновлении спинбоксов: {e}")

    def on_header_clicked(self, logical_index):
        current_order = self.proxy_model.sortOrder()
        new_order = Qt.SortOrder.DescendingOrder if current_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        self.proxy_model.sort(logical_index, new_order)

    def connect_buttons(self):
        self.add_record_btn.clicked.connect(self.add_aircraft)
        self.clear_form_btn.clicked.connect(self.clear_form)
        self.delete_record_btn.clicked.connect(self.delete_selected)

    def add_aircraft(self):
        try:
            # Получаем данные из автоматически созданной формы
            form_data = self.get_form_data()

            # Валидация данных
            errors = self.validate_form_data(form_data)

            # Дополнительная бизнес-логика валидации
            model = form_data.get('model', '')
            if model and len(model) > 100:
                errors.append("Модель самолета не должна превышать 100 символов")

            year = form_data.get('year', 0)
            if year < 2000 or year > QDate.currentDate().year():
                errors.append(f"Год выпуска должен быть между 2000 и {QDate.currentDate().year()}")

            seats = form_data.get('seats_amount', 0)
            if seats < 1 or seats > 1000:
                errors.append("Количество мест должно быть от 1 до 1000")

            baggage = form_data.get('baggage_capacity', 0)
            if baggage < 0 or baggage > 10000:
                errors.append("Вместимость багажа должна быть от 0 до 10000 кг")

            # Показываем ошибки, если есть
            if not self.show_validation_errors(errors):
                return

            # Если ошибок нет, сохраняем данные
            with self.engine.begin() as conn:
                conn.execute(insert(self.tables[self.table]).values(**form_data))
            self.model.refresh()
            self.clear_form()

            QMessageBox.information(self, "Успех", "Самолет успешно добавлен")

            parent_window = self.window()
            if hasattr(parent_window, 'refresh_combos'):
                parent_window.refresh_combos()

        except IntegrityError as e:
            error_message = self._format_sql_error(str(e.orig))
            QMessageBox.critical(self, "Ошибка сохранения", error_message)
        except SQLAlchemyError as e:
            error_message = self._format_sql_error(str(e))
            QMessageBox.critical(self, "Ошибка базы данных", error_message)
        except ValidationError as e:
            QMessageBox.warning(self, "Ошибка ввода", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Неожиданная ошибка: {str(e)}")

    def delete_selected(self):
        idx = self.add_table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите самолет")
            return

        source_index = self.proxy_model.mapToSource(idx)
        aircraft_id = self.model.pk_value_at(source_index.row())

        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.tables["aircraft"]).where(
                    self.tables["aircraft"].c.aircraft_id == aircraft_id
                ))
            self.model.refresh()

            parent_window = self.window()
            if hasattr(parent_window, 'refresh_combos'):
                parent_window.refresh_combos()

        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))
