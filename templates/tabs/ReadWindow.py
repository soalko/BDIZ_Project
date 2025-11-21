import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox,
    QPushButton, QFormLayout, QTableView,
    QComboBox, QLineEdit, QDialog,
    QLabel, QTabWidget, QTextEdit,
    QGroupBox, QHBoxLayout, QDialogButtonBox,
    QMessageBox, QScrollArea, QHeaderView
)

from typing import List
from sqlalchemy import text

from templates.tabs.SQLFilterDialog import SQLFilterDialog


class ValidationError(Exception):
    """Кастомное исключение для ошибок валидации"""

    def __init__(self, message, field_name=None):
        super().__init__(message)
        self.field_name = field_name
        self.message = message


try:
    from styles import apply_compact_table_view
except ImportError:
    def apply_compact_table_view(table_widget):
        try:
            table_widget.setAlternatingRowColors(True)
            if hasattr(table_widget, "setShowGrid"):
                table_widget.setShowGrid(False)
            header = table_widget.horizontalHeader()
            header.setStretchLastSection(True)
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        except Exception:
            pass


class ReadWindow(QWidget):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.tables = tables
        self.table = table

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # кнопка фильтрации для режима чтения
        self.filter_button = QPushButton("Фильтрация")
        self.filter_button.clicked.connect(self.open_filter_dialog)
        layout.addWidget(self.filter_button)

        self.read_table = QTableView()
        layout.addWidget(self.read_table)

        layout.addStretch()
        self.setup_read_model()

    def setup_read_model(self):
        """Инициализирует модель для таблицы чтения"""
        try:
            from db.models import SATableModel
            self.model = SATableModel(self.engine, self.tables[self.table], self)
            self.read_table.setModel(self.model)
            self.read_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            self.read_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
            apply_compact_table_view(self.read_table)
            self.read_table.setSortingEnabled(True)
        except Exception as e:
            print(f"Ошибка при инициализации модели чтения: {e}")

    def open_filter_dialog(self):
        dialog = SQLFilterDialog(self, self.table)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.get_filters(dialog)

    def setup_read_table(self):
        """Настройка таблицы для режима чтения"""
        from db.models import SATableModel
        self.model = SATableModel(self.engine, self.tables[self.table], self)

        # Настраиваем таблицу
        self.read_table.setModel(self.model)
        self.read_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.read_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        apply_compact_table_view(self.read_table)

        # Включаем сортировку
        self.read_table.setSortingEnabled(True)

    def setup_ui(self):
        if self.layout() is None:
            layout = QVBoxLayout(self)
        else:
            layout = self.layout()

        # кнопка фильтрации для режима чтения
        self.filter_button = QPushButton("Фильтрация")
        self.filter_button.clicked.connect(self.open_filter_dialog)
        layout.addWidget(self.filter_button)

        self.read_table = QTableView()
        layout.addWidget(self.read_table)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()

    def open_filter_dialog(self):
        dialog = SQLFilterDialog(self, self.table)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.get_filters(dialog)

    def get_filters(self, dialog):
        try:
            parsed_filters = self.parse_all_filters(dialog)
            sql_query = self.build_sql_from_parsed_filters(parsed_filters)
            self.execute_sql_query(sql_query)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при обработке фильтров: {str(e)}")

    def get_table_columns(self, table_name: str) -> List[str]:
        """Получает список колонок для указанной таблицы из базы данных"""
        try:
            with self.engine.connect() as conn:
                if self.engine.dialect.name == 'postgresql':
                    query = text(
                        """SELECT column_name
                           FROM information_schema.columns
                           WHERE table_name = :table_name
                           ORDER BY ordinal_position""")
                    result = conn.execute(query, {'table_name': table_name})

                columns = [row[0] for row in result]
                return columns
        except Exception as e:
            print(f"Ошибка при получении колонок таблицы {table_name}: {e}")
            return ["id", "name", "created_at"]

    def parse_select_columns(self, dialog):
        select_parts = []

        for column_name, checkbox in dialog.column_checkboxes.items():
            if checkbox.isChecked():
                select_parts.append(column_name)

        functions_text = dialog.added_functions_list.toPlainText().strip()
        if functions_text:
            function_lines = functions_text.split('\n')
            select_parts.extend(function_lines)

        return select_parts

    def parse_where_conditions(self, dialog):
        where_text = dialog.where_conditions_list.toPlainText().strip()
        if where_text:
            conditions = where_text.replace("WHERE ", "").split("\nAND ")
            return conditions
        return []

    def parse_order_by(self, dialog):
        order_text = dialog.order_columns_list.toPlainText().strip()
        if order_text:
            order_parts = order_text.replace("ORDER BY ", "").split(", ")
            return order_parts
        return []

    def parse_group_by(self, dialog):
        group_text = dialog.group_columns_list.toPlainText().strip()
        if group_text:
            group_parts = group_text.replace("GROUP BY ", "").split(", ")
            return group_parts
        return []

    def parse_having_conditions(self, dialog):
        having_text = dialog.having_conditions_list.toPlainText().strip()
        if having_text:
            conditions = having_text.replace("HAVING ", "").split("\nAND ")
            return conditions
        return []

    def parse_joins(self, dialog):
        if hasattr(dialog, 'joins_list'):
            joins_text = dialog.joins_list.toPlainText().strip()
            if joins_text:
                join_lines = joins_text.split('\n')
                return join_lines
        return []

    def parse_null_functions(self, dialog):
        """Парсит функции NULL из вкладки NULL FUNCTIONS"""
        if hasattr(dialog, 'null_functions_list'):
            null_text = dialog.null_functions_list.toPlainText().strip()
            if null_text:
                null_lines = null_text.split(',\n')
                return [line.strip() for line in null_lines if line.strip()]
        return []

    def parse_combo_boxes(self, dialog):
        """Парсит текущие значения выпадающих списков"""
        combo_values = {
            'functions': {
                'function': dialog.functions_combo.currentText(),
                'column': dialog.function_column_combo.currentText(),
                'alias': dialog.function_alias_edit.text().strip(),
                'string_param': dialog.function_string_edit.text().strip(),
                'column2': dialog.function_column2_combo.currentText()
            },
            'where': {
                'column': dialog.where_column_combo.currentText(),
                'operator': dialog.where_operator_combo.currentText(),
                'value': dialog.where_value_edit.text().strip()
            },
            'group_by': {
                'column': dialog.group_column_combo.currentText()
            },
            'having': {
                'function': dialog.having_function_combo.currentText(),
                'column': dialog.having_column_combo.currentText(),
                'operator': dialog.having_operator_combo.currentText(),
                'value': dialog.having_value_edit.text().strip()
            },
            'order_by': {
                'column': dialog.order_column_combo.currentText(),
                'direction': dialog.order_direction_combo.currentText()
            },
            'join': {
                'type': getattr(dialog, 'join_type_combo', None).currentText() if hasattr(dialog,
                                                                                          'join_type_combo') else "",
                'table': getattr(dialog, 'join_table_combo', None).currentText() if hasattr(dialog,
                                                                                            'join_table_combo') else "",
                'main_column': getattr(dialog, 'join_main_column_combo', None).currentText() if hasattr(dialog,
                                                                                                        'join_main_column_combo') else "",
                'foreign_column': getattr(dialog, 'join_foreign_column_combo', None).currentText() if hasattr(dialog,
                                                                                                              'join_foreign_column_combo') else ""
            }
        }
        return combo_values

    def parse_advanced(self, dialog):
        if hasattr(dialog, 'adv_conditions_list'):
            conditions = dialog.adv_conditions_list.toPlainText().strip()
            return conditions

    def parse_all_filters(self, dialog):
        """Парсит все элементы фильтрации и возвращает структурированные данные"""
        filters = {
            'select': self.parse_select_columns(dialog),
            'where': self.parse_where_conditions(dialog),
            'order_by': self.parse_order_by(dialog),
            'group_by': self.parse_group_by(dialog),
            'having': self.parse_having_conditions(dialog),
            'joins': self.parse_joins(dialog),
            'current_values': self.parse_combo_boxes(dialog),
            'advanced': self.parse_advanced(dialog),
            'null_functions': self.parse_null_functions(dialog),
            'case_expressions': self.parse_case_expressions(dialog)
        }
        print(filters)
        return filters

    def parse_case_expressions(self, dialog):
        """Парсит CASE выражения из вкладки CASE EXPRESSIONS"""
        if hasattr(dialog, 'case_preview_edit'):
            case_text = dialog.case_preview_edit.toPlainText().strip()
            if case_text:
                return [case_text]
        return []

    def build_sql_from_parsed_filters(self, parsed_filters):
        """Строит SQL запрос из распарсенных фильтров"""
        sql_parts = [f"SELECT "]

        if parsed_filters['select']:
            pts = parsed_filters['select']
            for i in range(len(pts)):
                if i == 0:
                    sql_parts.append(f"{self.table}.{pts[i]}")
                elif i != '' and "UPPER" not in pts[i] and "LOWER" not in pts[i] and "TRIM" not in pts[
                    i] and "SUBSTRING" not in pts[i] and "LPAD" not in pts[i] and "RPAD" not in pts[
                    i] and "CONCAT" not in pts[i]:
                    sql_parts.append(f", {self.table}.{pts[i]}")
                else:
                    sql_parts.append(f", {pts[i]}")
            for i in parsed_filters['null_functions']:
                sql_parts.append(f", {i}")
            for i in parsed_filters['case_expressions']:
                sql_parts.append(f", {i}")

        else:
            sql_parts.append("*")

        sql_parts.append(f"FROM {self.table}")

        if parsed_filters['joins']:
            sql_parts.extend(parsed_filters['joins'])

        if parsed_filters['where']:
            where_conditions = " AND ".join(parsed_filters['where'])
            sql_parts.append(f"WHERE {where_conditions}")

        if parsed_filters['group_by']:
            group_columns = ", ".join(parsed_filters['group_by'])
            sql_parts.append(f"GROUP BY {group_columns}")

        if parsed_filters['having']:
            having_conditions = " AND ".join(parsed_filters['having'])
            sql_parts.append(f"HAVING {having_conditions}")

        if parsed_filters['order_by']:
            order_columns = ", ".join(parsed_filters['order_by'])
            sql_parts.append(f"ORDER BY {order_columns}")

        if parsed_filters['advanced']:
            sql_parts.append(f'WHERE {parsed_filters["advanced"]}')

        print(" ".join(sql_parts))

        return " ".join(sql_parts)

    def execute_sql_query(self, sql_query):
        """Выполняет SQL запрос и отображает результаты с обработкой ошибок"""
        try:
            with self.engine.begin() as conn:
                result = conn.execute(text(sql_query))

                from PySide6.QtGui import QStandardItemModel, QStandardItem
                model = QStandardItemModel()

                column_names = result.keys()
                model.setHorizontalHeaderLabels(column_names)

                for row in result:
                    row_items = []
                    for value in row:
                        item = QStandardItem(str(value) if value is not None else "")
                        row_items.append(item)
                    model.appendRow(row_items)

                self.read_table.setModel(model)

        except Exception as e:
            error_message = self._format_sql_error(str(e))
            QMessageBox.critical(self, "Ошибка выполнения запроса", error_message)

    def _format_sql_error(self, error_str: str) -> str:
        """Форматирует SQL ошибку в понятный для пользователя вид"""
        # PostgreSQL ошибки
        if "null value in column" in error_str:
            match = re.search(r'column "([^"]+)"', error_str)
            if match:
                column = match.group(1)
                return f"Ошибка: Поле '{column}' не может быть пустым. Заполните это поле."

        elif "violates check constraint" in error_str:
            match = re.search(r'CHECK "([^"]+)"', error_str)
            if match:
                constraint = match.group(1)
                return f"Ошибка проверки данных: нарушено ограничение '{constraint}'. Проверьте введенные значения."

        elif "violates foreign key constraint" in error_str:
            match = re.search(r'Key \(([^)]+)\)=\(([^)]+)\)', error_str)
            if match:
                column = match.group(1)
                value = match.group(2)
                return f"Ошибка связи: значение '{value}' в поле '{column}' не найдено в связанной таблице."

        elif "duplicate key value violates unique constraint" in error_str:
            match = re.search(r'Key \(([^)]+)\)=\(([^)]+)\)', error_str)
            if match:
                column = match.group(1)
                value = match.group(2)
                return f"Ошибка уникальности: значение '{value}' в поле '{column}' уже существует. Введите уникальное значение."

        elif "value too long for type" in error_str:
            match = re.search(r'type character varying\((\d+)\)', error_str)
            if match:
                max_length = match.group(1)
                return f"Ошибка длины: текст слишком длинный. Максимальная длина: {max_length} символов."

        # Общая обработка
        return f"Ошибка базы данных:\n{error_str}"

    def _update_conditions_with_table(self, conditions, table_name):
        """Добавляет имя таблицы к колонкам в условиях"""
        table_columns = self.get_table_columns(table_name)

        for column in table_columns:
            conditions = conditions.replace(f" {column} ", f" {table_name}.{column} ")
            conditions = conditions.replace(f"({column}", f"({table_name}.{column}")
            conditions = conditions.replace(f"{column})", f"{table_name}.{column})")

        return conditions

    def _get_columns_from_function(self, func_text):
        """Извлекает имена колонок из текста функции"""
        current_table_columns = self.get_table_columns(self.table)
        found_columns = []

        for column in current_table_columns:
            if column in func_text:
                found_columns.append(column)

        return found_columns
