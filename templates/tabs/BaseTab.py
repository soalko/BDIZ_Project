from typing import List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox,
    QPushButton, QFormLayout, QTableView,
    QComboBox, QLineEdit, QDialog,
    QLabel, QTabWidget, QTextEdit,
    QGroupBox, QHBoxLayout, QDialogButtonBox,
    QMessageBox, QScrollArea
)

from sqlalchemy import text, inspect

from templates.modes import AppMode

from templates.tabs.AddWindow import AddWindow
from templates.tabs.EditWindow import EditWindow
from templates.tabs.ReadWindow import ReadWindow


class BaseTab(QWidget):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(parent)

        self.engine = engine
        self.tables = tables
        self.current_mode = AppMode.READ
        self.table = table

        # Создаем контейнер для смены окон
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Создаем контейнер для текущего окна
        self.current_window = None

        self.added_functions_list = ""

    def set_mode(self, mode: AppMode):
        self.current_mode = mode
        self.update_ui_for_mode()

    def update_ui_for_mode(self):
        # Удаляем текущее окно
        if self.current_window:
            self.current_window.setParent(None)
            self.current_window = None

        # Создаем новое окно в зависимости от режима
        if self.current_mode == AppMode.READ:
            self.current_window = self.create_read_window()
        elif self.current_mode == AppMode.EDIT:
            self.current_window = self.create_edit_window()
        elif self.current_mode == AppMode.ADD:
            self.current_window = self.create_add_window()

        if self.current_window:
            self.main_layout.addWidget(self.current_window)
            if hasattr(self.current_window, 'model') and self.current_window.model:
                self.current_window.model.refresh()

                # ДОБАВЛЕНО: Обновляем виджеты формы при смене на режим ADD
            if self.current_mode == AppMode.ADD and hasattr(self.current_window, 'refresh_form_widgets'):
                self.current_window.refresh_form_widgets()

    def create_read_window(self):
        """Должен быть переопределен в дочерних классах"""
        return ReadWindow(self.engine, self.tables, self.table, self)

    def create_edit_window(self):
        """Должен быть переопределен в дочерних классах"""
        return EditWindow(self.engine, self.tables, self.table, self)

    def create_add_window(self):
        """Должен быть переопределен в дочерних классах"""
        return AddWindow(self.engine, self.tables, self.table, self)

    def update_model(self):
        from sqlalchemy import Table, MetaData
        metadata = MetaData()
        self.tables[self.table] = Table(
            self.table,
            metadata,
            autoload_with=self.engine
        )

    def update_tables(self):
        pass

    def load_table_structure(self):
        """Делегирует загрузку структуры таблицы в окно редактирования"""
        edit_window = self.create_edit_window()
        if hasattr(edit_window, 'load_table_structure'):
            edit_window.load_table_structure()

    def execute_sql(self, sql_query):
        try:
            with self.engine.begin() as conn:
                result = conn.execute(text(sql_query))
                return result
        except Exception as e:
            QMessageBox.critical(self, "Ошибка SQL", f"Ошибка выполнения запроса: {str(e)}")
            return None

    def get_table_columns_info(self) -> List[Dict[str, Any]]:
        """Получает информацию о столбцах таблицы из базы данных"""
        try:
            inspector = inspect(self.engine)
            columns_info = []

            for column in inspector.get_columns(self.table):
                column_info = {
                    'name': column['name'],
                    'type': str(column['type']),
                    'nullable': column['nullable'],
                    'default': column.get('default'),
                    'primary_key': False,
                    'foreign_key': None
                }

                # Проверяем, является ли столбец первичным ключом
                pk_constraint = inspector.get_pk_constraint(self.table)
                if pk_constraint and column['name'] in pk_constraint['constrained_columns']:
                    column_info['primary_key'] = True

                # Проверяем внешние ключи
                foreign_keys = inspector.get_foreign_keys(self.table)
                for fk in foreign_keys:
                    if column['name'] in fk['constrained_columns']:
                        column_info['foreign_key'] = {
                            'referenced_table': fk['referred_table'],
                            'referenced_column': fk['referred_columns'][0] if fk['referred_columns'] else None
                        }
                        break

                columns_info.append(column_info)

            return columns_info
        except Exception as e:
            print(f"Ошибка при получении информации о столбцах: {e}")
            return []


