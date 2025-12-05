# ===== PySide6 =====
from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtWidgets import (
    QMessageBox, QSpinBox,
    QDateEdit, QTimeEdit
)

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


# -------------------------------
# Вкладка «Рейсы»
# --------------------------------
class FlightsTab(BaseTab):
    def __init__(self, engine, tables, parent=None):
        super().__init__(engine, tables, "flights", parent)
        self.model = SATableModel(engine, self.tables["flights"], self)
        self.update_model()
        self.update_ui_for_mode()

    def create_add_window(self):
        return FlightsAddWindow(self.engine, self.tables, self.table, self)


class FlightsEditWindow(EditWindow):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(engine, tables, table, parent)
        self.load_table_structure()


class FlightsAddWindow(AddWindow):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(engine, tables, table, parent)

    def refresh_form_widgets(self):
        """Обновляет виджеты формы при каждом открытии вкладки"""
        super().refresh_form_widgets()  # Вызываем родительский метод

        # ДОБАВЛЕНО: Обновляем спинбоксы и даты
        self._refresh_widgets()

        # ДОБАВЛЕНО: Обновляем таблицу данных
        if hasattr(self, 'model') and self.model:
            self.model.refresh()

    def _refresh_widgets(self):
        """Обновляет значения в виджетах"""
        try:
            current_date = QDate.currentDate()

            if hasattr(self, 'input_widgets'):
                for column_name, widget in self.input_widgets.items():
                    if isinstance(widget, QDateEdit) and column_name == 'departure_date':
                        widget.setDate(current_date)
                    elif isinstance(widget, QTimeEdit) and column_name == 'departure_time':
                        widget.setTime(QTime(12, 0))  # Значение по умолчанию
                    elif isinstance(widget, QSpinBox) and column_name == 'flight_time':
                        widget.setValue(120)  # Значение по умолчанию
        except Exception as e:
            print(f"Ошибка при обновлении виджетов: {e}")

    def on_header_clicked(self, logical_index):
        current_order = self.proxy_model.sortOrder()
        new_order = Qt.SortOrder.DescendingOrder if current_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        self.proxy_model.sort(logical_index, new_order)

    def connect_buttons(self):
        self.add_record_btn.clicked.connect(self.add_flight)
        self.clear_form_btn.clicked.connect(self.clear_form)
        self.delete_record_btn.clicked.connect(self.delete_selected)

    def add_form_rows(self):
        """Переопределяем для добавления кастомной логики, если нужно"""
        # Базовая форма создается автоматически в родительском классе
        # Здесь можно добавить дополнительные поля или кастомную логику
        pass

    def add_flight(self):
        # Получаем данные из автоматически созданной формы
        form_data = self.get_form_data()

        # Валидация данных
        departure_airport = form_data.get('departure_airport', '')
        arrival_airport = form_data.get('arrival_airport', '')

        if not departure_airport or not arrival_airport:
            QMessageBox.warning(self, "Ввод", "Аэропорты вылета и прибытия обязательны")
            return

        if not isinstance(departure_airport, str) or not isinstance(arrival_airport, str):
            QMessageBox.warning(self, "Ввод", "Аэропорты должны быть текстовыми значениями")
            return

        departure_airport = departure_airport.strip().upper()
        arrival_airport = arrival_airport.strip().upper()

        if not departure_airport.isalpha() or not arrival_airport.isalpha():
            QMessageBox.warning(self, "Ввод", "Аэропорты вылета и прибытия должны содержать только буквы")
            return

        if len(departure_airport) != 3 or len(arrival_airport) != 3:
            QMessageBox.warning(self, "Ввод", "Коды аэропортов должны состоять из 3 символов")
            return

        # Обновляем данные формы с проверенными значениями
        form_data['departure_airport'] = departure_airport
        form_data['arrival_airport'] = arrival_airport

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.tables["flights"]).values(**form_data))
            self.model.refresh()
            self.clear_form()

            parent_window = self.window()
            if hasattr(parent_window, 'refresh_combos'):
                parent_window.refresh_combos()

        except IntegrityError as e:
            QMessageBox.critical(self, "Ошибка INSERT (CHECK/FOREIGN KEY constraint)", str(e.orig))
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка INSERT", str(e))

    def delete_selected(self):
        idx = self.add_table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите рейс")
            return

        source_index = self.proxy_model.mapToSource(idx)
        flight_id = self.model.pk_value_at(source_index.row())

        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.tables["flights"]).where(
                    self.tables["flights"].c.flight_id == flight_id
                ))
            self.model.refresh()

            parent_window = self.window()
            if hasattr(parent_window, 'refresh_combos'):
                parent_window.refresh_combos()

        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def clear_form(self):
        """Очищает форму - теперь использует метод родительского класса"""
        super().clear_form()