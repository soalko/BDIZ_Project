import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox,
    QPushButton, QFormLayout, QTableView,
    QComboBox, QLineEdit, QDialog,
    QLabel, QTabWidget, QTextEdit,
    QGroupBox, QHBoxLayout, QDialogButtonBox,
    QMessageBox, QScrollArea, QHeaderView,
    QMenu, QInputDialog, QSplitter,
    QListWidget, QListWidgetItem, QTableWidget,
    QTableWidgetItem, QSpinBox
)

from PySide6.QtCore import Qt, Signal
from typing import List, Tuple, Optional
from sqlalchemy import text, inspect

from templates.tabs.SQLFilterDialog import SQLFilterDialog
from templates.tabs.ViewWindow import ViewWindow
from templates.tabs.CTEWindow import CTEWindow


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


class WindowFunctionDialog(QDialog):
    """Диалог для настройки оконных функций"""

    def __init__(self, table_name: str, columns: List[str], parent=None):
        super().__init__(parent)
        self.table_name = table_name
        self.columns = columns
        self.window_functions = []

        self.setWindowTitle("Оконные функции")
        self.setMinimumSize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        # Создаем основной layout
        main_layout = QVBoxLayout(self)

        # Создаем QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # Важно: содержимое будет растягиваться
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Создаем основной виджет для содержимого
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)

        # Основной сплиттер
        splitter = QSplitter(Qt.Vertical)

        # Верхняя часть - настройки функций
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)

        # Группа для выбора типа функции
        function_group = QGroupBox("Тип оконной функции")
        function_layout = QVBoxLayout(function_group)

        self.function_type_combo = QComboBox()
        self.function_type_combo.addItems(["RANK", "LAG", "LEAD"])
        self.function_type_combo.currentTextChanged.connect(self.on_function_type_changed)
        function_layout.addWidget(QLabel("Функция:"))
        function_layout.addWidget(self.function_type_combo)

        config_layout.addWidget(function_group)

        # Группа для параметров функции
        self.params_group = QGroupBox("Параметры функции")
        self.params_layout = QVBoxLayout(self.params_group)

        # Для всех функций: выбор колонки для функции
        column_layout = QHBoxLayout()
        column_layout.addWidget(QLabel("Колонка:"))
        self.column_combo = QComboBox()
        self.column_combo.addItems(self.columns)
        column_layout.addWidget(self.column_combo)
        self.params_layout.addLayout(column_layout)

        # Алиас для функции
        alias_layout = QHBoxLayout()
        alias_layout.addWidget(QLabel("Алиас:"))
        self.alias_edit = QLineEdit()
        self.alias_edit.setPlaceholderText("rank_col")
        alias_layout.addWidget(self.alias_edit)
        self.params_layout.addLayout(alias_layout)

        # Специфичные параметры для LAG/LEAD
        self.offset_layout = QHBoxLayout()
        self.offset_layout.addWidget(QLabel("Смещение:"))
        self.offset_spin = QSpinBox()
        self.offset_spin.setMinimum(1)
        self.offset_spin.setMaximum(100)
        self.offset_spin.setValue(1)
        self.offset_layout.addWidget(self.offset_spin)
        self.offset_layout.addWidget(QLabel("Значение по умолчанию:"))
        self.default_value_edit = QLineEdit()
        self.default_value_edit.setPlaceholderText("NULL")
        self.offset_layout.addWidget(self.default_value_edit)
        self.params_layout.addLayout(self.offset_layout)

        config_layout.addWidget(self.params_group)

        # Параметры для сортировки (ORDER BY)
        order_group = QGroupBox("ORDER BY (обязательно для оконных функций)")
        order_layout = QVBoxLayout(order_group)

        # Выбор колонок для сортировки
        self.order_columns_list = QListWidget()
        self.order_columns_list.setSelectionMode(QListWidget.MultiSelection)
        self.order_columns_list.setMaximumHeight(150)  # Ограничиваем высоту списка
        for col in self.columns:
            self.order_columns_list.addItem(col)

        # Прокрутка для списка колонок внутри группы
        order_scroll_area = QScrollArea()
        order_scroll_area.setWidgetResizable(True)
        order_scroll_area.setMaximumHeight(120)
        order_scroll_area.setWidget(self.order_columns_list)

        order_layout.addWidget(QLabel("Колонки для сортировки:"))
        order_layout.addWidget(order_scroll_area)

        # Направление сортировки для выбранных колонок
        order_direction_layout = QHBoxLayout()
        order_direction_layout.addWidget(QLabel("Направление сортировки:"))
        self.order_direction_combo = QComboBox()
        self.order_direction_combo.addItems(["ASC", "DESC"])
        order_direction_layout.addWidget(self.order_direction_combo)
        order_direction_layout.addStretch()
        order_layout.addLayout(order_direction_layout)

        config_layout.addWidget(order_group)

        # Параметры для разбиения (PARTITION BY) - опционально
        partition_group = QGroupBox("PARTITION BY (опционально)")
        partition_layout = QVBoxLayout(partition_group)

        self.partition_columns_list = QListWidget()
        self.partition_columns_list.setSelectionMode(QListWidget.MultiSelection)
        self.partition_columns_list.setMaximumHeight(150)  # Ограничиваем высоту списка

        # Прокрутка для списка колонок внутри группы
        partition_scroll_area = QScrollArea()
        partition_scroll_area.setWidgetResizable(True)
        partition_scroll_area.setMaximumHeight(120)
        partition_scroll_area.setWidget(self.partition_columns_list)

        for col in self.columns:
            self.partition_columns_list.addItem(col)

        partition_layout.addWidget(QLabel("Колонки для разбиения:"))
        partition_layout.addWidget(partition_scroll_area)

        config_layout.addWidget(partition_group)

        # Кнопка добавления функции
        add_button = QPushButton("Добавить функцию")
        add_button.clicked.connect(self.add_function)
        config_layout.addWidget(add_button)

        splitter.addWidget(config_widget)

        # Нижняя часть - список добавленных функций
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)

        list_layout.addWidget(QLabel("Добавленные оконные функции:"))

        self.functions_table = QTableWidget()
        self.functions_table.setColumnCount(6)
        self.functions_table.setHorizontalHeaderLabels([
            "Тип", "Колонка", "Алиас", "Смещение", "ORDER BY", "PARTITION BY"
        ])
        self.functions_table.horizontalHeader().setStretchLastSection(True)
        self.functions_table.setMaximumHeight(200)  # Ограничиваем высоту таблицы

        # Прокрутка для таблицы функций
        table_scroll_area = QScrollArea()
        table_scroll_area.setWidgetResizable(True)
        table_scroll_area.setWidget(self.functions_table)

        list_layout.addWidget(table_scroll_area)

        # Кнопки управления списком
        buttons_layout = QHBoxLayout()
        remove_button = QPushButton("Удалить выбранную")
        remove_button.clicked.connect(self.remove_function)
        clear_button = QPushButton("Очистить все")
        clear_button.clicked.connect(self.clear_functions)
        buttons_layout.addWidget(remove_button)
        buttons_layout.addWidget(clear_button)
        buttons_layout.addStretch()
        list_layout.addLayout(buttons_layout)

        splitter.addWidget(list_widget)

        layout.addWidget(splitter)
        splitter.setSizes([400, 250])  # Увеличиваем размер верхней части

        # Устанавливаем контентный виджет в scroll area
        scroll_area.setWidget(content_widget)

        # Добавляем scroll area в основной layout
        main_layout.addWidget(scroll_area)

        # Кнопки диалога
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        # Инициализация видимости элементов
        self.on_function_type_changed("RANK")

    def on_function_type_changed(self, function_type: str):
        """Обновляет видимость элементов в зависимости от типа функции"""
        # Находим родительский виджет для offset_layout
        if hasattr(self, 'offset_widget'):
            # Если уже создан виджет-контейнер
            if function_type == "RANK":
                self.offset_widget.setVisible(False)
            else:  # LAG или LEAD
                self.offset_widget.setVisible(True)
        else:
            # Или альтернативный подход - скрываем/показываем отдельные элементы
            for i in range(self.offset_layout.count()):
                item = self.offset_layout.itemAt(i)
                if item.widget():
                    if function_type == "RANK":
                        item.widget().setVisible(False)
                    else:
                        item.widget().setVisible(True)

    def add_function(self):
        """Добавляет оконную функцию в список"""
        function_type = self.function_type_combo.currentText()
        column = self.column_combo.currentText()
        alias = self.alias_edit.text().strip() or f"{function_type.lower()}_{column}"

        # Получаем ORDER BY колонки
        order_columns = []
        for i in range(self.order_columns_list.count()):
            item = self.order_columns_list.item(i)
            if item.isSelected():
                order_columns.append(item.text())

        if not order_columns:
            QMessageBox.warning(self, "Ошибка",
                                "Для оконных функций необходимо указать хотя бы одну колонку для ORDER BY")
            return

        order_by = ", ".join(order_columns)
        direction = self.order_direction_combo.currentText()
        if direction == "DESC":
            order_by = f"{order_by} DESC"

        # Получаем PARTITION BY колонки
        partition_columns = []
        for i in range(self.partition_columns_list.count()):
            item = self.partition_columns_list.item(i)
            if item.isSelected():
                partition_columns.append(item.text())

        partition_by = ", ".join(partition_columns) if partition_columns else ""

        # Получаем параметры для LAG/LEAD
        offset = ""
        default_value = ""
        if function_type in ["LAG", "LEAD"]:
            offset = str(self.offset_spin.value())
            default_value = self.default_value_edit.text().strip()

        # Добавляем функцию в список
        self.window_functions.append({
            'type': function_type,
            'column': column,
            'alias': alias,
            'order_by': order_by,
            'partition_by': partition_by,
            'offset': offset,
            'default_value': default_value
        })

        self.update_functions_table()

    def update_functions_table(self):
        """Обновляет таблицу с функциями"""
        self.functions_table.setRowCount(len(self.window_functions))

        for row, func in enumerate(self.window_functions):
            self.functions_table.setItem(row, 0, QTableWidgetItem(func['type']))
            self.functions_table.setItem(row, 1, QTableWidgetItem(func['column']))
            self.functions_table.setItem(row, 2, QTableWidgetItem(func['alias']))
            self.functions_table.setItem(row, 3, QTableWidgetItem(func['offset']))
            self.functions_table.setItem(row, 4, QTableWidgetItem(func['order_by']))
            self.functions_table.setItem(row, 5, QTableWidgetItem(func['partition_by']))

        self.functions_table.resizeColumnsToContents()

    def remove_function(self):
        """Удаляет выбранную функцию"""
        current_row = self.functions_table.currentRow()
        if current_row >= 0 and current_row < len(self.window_functions):
            self.window_functions.pop(current_row)
            self.update_functions_table()

    def clear_functions(self):
        """Очищает все функции"""
        self.window_functions = []
        self.update_functions_table()

    def get_window_functions(self) -> List[dict]:
        """Возвращает список настроенных оконных функций"""
        return self.window_functions

    def get_window_functions_sql(self) -> List[Tuple[str, str]]:
        """Возвращает SQL выражения для оконных функций в формате (выражение, алиас)"""
        result = []

        for func in self.window_functions:
            if func['type'] == "RANK":
                expression = f"RANK()"
            elif func['type'] == "LAG":
                expression = f"LAG({func['column']}, {func['offset']}"
                if func['default_value']:
                    expression += f", {func['default_value']}"
                expression += ")"
            elif func['type'] == "LEAD":
                expression = f"LEAD({func['column']}, {func['offset']}"
                if func['default_value']:
                    expression += f", {func['default_value']}"
                expression += ")"

            # Добавляем OVER() clause
            over_parts = []
            if func['partition_by']:
                over_parts.append(f"PARTITION BY {func['partition_by']}")

            over_parts.append(f"ORDER BY {func['order_by']}")

            expression += f" OVER ({' '.join(over_parts)})"
            result.append((expression, func['alias']))

        return result


class ReadWindow(QWidget):
    """Окно чтения с расширенными функциями группировки и управления представлениями"""

    view_created = Signal(str)
    view_dropped = Signal(str)

    def __init__(self, engine, tables, table, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.tables = tables
        self.table = table
        self.current_view = None
        self.views_cache = {}
        self.window_functions = []  # Список оконных функций

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Верхняя панель с кнопками
        self.top_panel = QHBoxLayout()

        # Кнопка фильтрации

        self.buttons_panel = QWidget()
        self.buttons_layout = QHBoxLayout(self.buttons_panel)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)

        # Кнопка фильтрации
        self.filter_button = QPushButton("Фильтрация SQL")
        self.filter_button.clicked.connect(self.open_filter_dialog)

        # Кнопка VIEW запросов
        self.view_button = QPushButton("VIEW запросы")
        self.view_button.clicked.connect(self.open_view_dialog)

        self.cte_button = QPushButton("Конструктор CTE")
        self.cte_button.clicked.connect(self.open_cte_dialog)

        # Кнопка оконных функций
        self.window_func_button = QPushButton("Оконные функции")
        self.window_func_button.clicked.connect(self.open_window_function_dialog)

        self.create_view_btn = QPushButton("Создать представление")
        self.create_view_btn.clicked.connect(self.create_view_from_current)
        self.create_view_btn.setEnabled(False)

        self.buttons_layout.addWidget(self.filter_button)
        self.buttons_layout.addWidget(self.view_button)
        self.buttons_layout.addWidget(self.cte_button)
        self.buttons_layout.addWidget(self.window_func_button)
        self.buttons_layout.addWidget(self.create_view_btn)

        self.buttons_layout.addStretch()

        layout.addWidget(self.buttons_panel)

        # Кнопка создания представления из текущего запроса

        self.top_panel.addStretch()
        layout.addLayout(self.top_panel)

        # Сплиттер для разделения таблицы и дополнительной информации
        self.splitter = QSplitter(Qt.Vertical)

        # Таблица данных
        self.read_table = QTableView()
        self.splitter.addWidget(self.read_table)

        # Панель информации о расширенной группировке
        self.grouping_info_panel = QGroupBox("Информация о расширенной группировке")
        self.grouping_info_layout = QVBoxLayout(self.grouping_info_panel)
        self.grouping_info_label = QLabel("")
        self.grouping_info_label.setWordWrap(True)
        self.grouping_info_layout.addWidget(self.grouping_info_label)
        self.grouping_info_panel.setVisible(False)
        self.splitter.addWidget(self.grouping_info_panel)

        layout.addWidget(self.splitter)
        self.splitter.setSizes([400, 100])

        self.setup_read_model()
        self.load_views_from_db()

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

    def open_view_dialog(self):
        """Открывает диалог работы с VIEW"""
        dialog = ViewWindow(self.engine, self.table, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            view_query = dialog.get_view_query()
            if view_query:
                self.execute_sql_query(view_query)

    def open_cte_dialog(self):
        """Открывает конструктор Common Table Expressions"""
        dialog = CTEWindow(self.engine, self.table, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cte_query = dialog.get_cte_query()
            if cte_query:
                self.execute_sql_query(cte_query)

    def open_window_function_dialog(self):
        """Открывает диалог для настройки оконных функций"""
        columns = self.get_table_columns(self.table)
        dialog = WindowFunctionDialog(self.table, columns, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Получаем настроенные оконные функции
            self.window_functions = dialog.get_window_functions_sql()

            if self.window_functions:
                # Включаем кнопку создания представления
                self.create_view_btn.setEnabled(True)

                # Строим базовый запрос с оконными функциями
                sql_query = self.build_sql_with_window_functions()
                self.current_sql_query = sql_query

                # Показываем информацию о примененных функциях
                self.show_window_functions_info()

                # Выполняем запрос
                self.execute_sql_query(sql_query)

    def build_sql_with_window_functions(self) -> str:
        """Строит SQL запрос с оконными функциями"""
        # Получаем все колонки таблицы
        columns = self.get_table_columns(self.table)

        # Строим SELECT часть
        select_parts = [f"{self.table}.{col}" for col in columns]

        # Добавляем оконные функции
        for expression, alias in self.window_functions:
            select_parts.append(f"{expression} AS {alias}")

        # Базовая часть запроса
        sql_parts = [
            f"SELECT {', '.join(select_parts)}",
            f"FROM {self.table}"
        ]

        return " ".join(sql_parts)

    def show_window_functions_info(self):
        """Показывает информацию о примененных оконных функциях"""
        if not self.window_functions:
            self.grouping_info_panel.setVisible(False)
            return

        info_text = "<b>Применены оконные функции:</b><br>"

        for expression, alias in self.window_functions:
            # Извлекаем тип функции из выражения
            func_type = expression.split('(')[0]
            info_text += f"• {alias}: {func_type}<br>"

        self.grouping_info_label.setText(info_text)
        self.grouping_info_panel.setTitle("Оконные функции")
        self.grouping_info_panel.setVisible(True)

    def get_filters(self, dialog):
        try:
            parsed_filters = self.parse_all_filters(dialog)
            sql_query = self.build_sql_from_parsed_filters(parsed_filters)

            # Включаем кнопку создания представления
            self.create_view_btn.setEnabled(True)

            # Сохраняем текущий SQL для возможного создания представления
            self.current_sql_query = sql_query

            # Если есть настройки расширенной группировки, показываем информацию
            if hasattr(dialog, 'grouping_type_radio_simple'):
                grouping_info = self.parse_advanced_grouping(dialog)
                if grouping_info:
                    self.show_grouping_info(grouping_info)

            self.execute_sql_query(sql_query)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при обработке фильтров: {str(e)}")

    def parse_advanced_grouping(self, dialog):
        """Парсит настройки расширенной группировки"""
        grouping_info = {
            'type': 'SIMPLE',
            'columns': [],
            'aggregations': [],
            'sets': [],
            'level_detail': 'Все уровни'
        }

        # Определяем тип группировки
        if dialog.grouping_type_radio_rollup.isChecked():
            grouping_info['type'] = 'ROLLUP'
            grouping_info['level_detail'] = dialog.grouping_levels_combo.currentText()
        elif dialog.grouping_type_radio_cube.isChecked():
            grouping_info['type'] = 'CUBE'
        elif dialog.grouping_type_radio_sets.isChecked():
            grouping_info['type'] = 'GROUPING_SETS'
            # Парсим наборы
            sets_text = dialog.grouping_sets_text.toPlainText().strip()
            if sets_text:
                for line in sets_text.split('\n'):
                    line = line.strip()
                    if line:
                        grouping_info['sets'].append([col.strip() for col in line.split(',')])

        # Парсим выбранные колонки
        for i in range(dialog.grouping_columns_list.count()):
            item = dialog.grouping_columns_list.item(i)
            if item.isSelected():
                grouping_info['columns'].append(item.text())

        # Парсим агрегатные функции
        for i in range(dialog.aggregation_functions_list.count()):
            item = dialog.aggregation_functions_list.item(i)
            if item.isSelected():
                grouping_info['aggregations'].append(item.text())

        return grouping_info if grouping_info['columns'] else None

    def show_grouping_info(self, grouping_info):
        """Показывает информацию о примененной расширенной группировке"""
        info_text = f"<b>Применена расширенная группировка:</b><br>"
        info_text += f"Тип: {grouping_info['type']}<br>"

        if grouping_info['columns']:
            info_text += f"Колонки: {', '.join(grouping_info['columns'])}<br>"

        if grouping_info['aggregations']:
            info_text += f"Агрегаты: {', '.join(grouping_info['aggregations'])}<br>"

        if grouping_info['type'] == 'ROLLUP':
            info_text += f"Детализация: {grouping_info['level_detail']}<br>"
        elif grouping_info['type'] == 'GROUPING_SETS' and grouping_info['sets']:
            info_text += f"Наборы: {len(grouping_info['sets'])} набор(ов)<br>"

        self.grouping_info_label.setText(info_text)
        self.grouping_info_panel.setVisible(True)

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
                else:
                    # Для других СУБД
                    query = text(f"SELECT * FROM {table_name} LIMIT 1")
                    result = conn.execute(query)
                    columns = result.keys()
                    return list(columns)

                columns = [row[0] for row in result]
                return columns
        except Exception as e:
            print(f"Ошибка при получении колонок таблицы {table_name}: {e}")
            # Возвращаем пустой список вместо дефолтных значений
            return []

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
            'case_expressions': self.parse_case_expressions(dialog),
            'advanced_grouping': self.parse_advanced_grouping(dialog) if hasattr(dialog,
                                                                                 'grouping_type_radio_simple') else None
        }
        return filters

    def parse_case_expressions(self, dialog):
        """Парсит CASE выражения из вкладки CASE EXPRESSIONS"""
        if hasattr(dialog, 'case_preview_edit'):
            case_text = dialog.case_preview_edit.toPlainText().strip()
            if case_text:
                return [case_text]
        return []

    def build_sql_from_parsed_filters(self, parsed_filters):
        """Строит SQL запрос из распарсенных фильтров с поддержкой расширенной группировки"""
        sql_parts = [f"SELECT "]

        # Обрабатываем SELECT колонки
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

        # Обрабатываем WHERE
        if parsed_filters['where']:
            where_conditions = " AND ".join(parsed_filters['where'])
            sql_parts.append(f"WHERE {where_conditions}")

        # Обрабатываем GROUP BY (обычный или расширенный)
        if parsed_filters['advanced_grouping']:
            grouping_info = parsed_filters['advanced_grouping']
            if grouping_info and grouping_info['columns']:
                # Добавляем агрегатные функции из расширенной группировки
                for agg in grouping_info['aggregations']:
                    sql_parts.append(f", {agg}")

                # Строим GROUP BY часть в зависимости от типа
                if grouping_info['type'] == 'SIMPLE':
                    group_by = f"GROUP BY {', '.join(grouping_info['columns'])}"
                elif grouping_info['type'] == 'ROLLUP':
                    group_by = f"GROUP BY ROLLUP({', '.join(grouping_info['columns'])})"
                elif grouping_info['type'] == 'CUBE':
                    group_by = f"GROUP BY CUBE({', '.join(grouping_info['columns'])})"
                elif grouping_info['type'] == 'GROUPING_SETS':
                    if grouping_info['sets']:
                        sets_str = []
                        for s in grouping_info['sets']:
                            sets_str.append(f"({', '.join(s)})")
                        group_by = f"GROUP BY GROUPING SETS ({', '.join(sets_str)})"
                    else:
                        group_by = f"GROUP BY {', '.join(grouping_info['columns'])}"

                sql_parts.append(group_by)
        elif parsed_filters['group_by']:
            group_columns = ", ".join(parsed_filters['group_by'])
            sql_parts.append(f"GROUP BY {group_columns}")

        # Обрабатываем HAVING
        if parsed_filters['having']:
            having_conditions = " AND ".join(parsed_filters['having'])
            sql_parts.append(f"HAVING {having_conditions}")

        # Обрабатываем ORDER BY
        if parsed_filters['order_by']:
            order_columns = ", ".join(parsed_filters['order_by'])
            sql_parts.append(f"ORDER BY {order_columns}")

        if parsed_filters['advanced']:
            sql_parts.append(f'WHERE {parsed_filters["advanced"]}')

        sql_query = " ".join(sql_parts)
        return sql_query

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
                self.read_table.setSortingEnabled(True)  # Включаем сортировку

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

    # ======================== ФУНКЦИИ ДЛЯ РАБОТЫ С ПРЕДСТАВЛЕНИЯМИ ========================

    def show_views_manager(self):
        """Показывает менеджер представлений"""
        dialog = ViewManagerDialog(self.engine, self)
        if dialog.exec():
            self.load_views_from_db()

    def load_views_from_db(self):
        """Загружает список представлений из базы данных"""
        try:
            inspector = inspect(self.engine)
            self.views_cache = {}

            # Получаем список представлений
            views = inspector.get_view_names()
            for view_name in views:
                try:
                    # Получаем определение представления
                    view_def = inspector.get_view_definition(view_name)
                    self.views_cache[view_name] = {
                        'definition': view_def,
                        'columns': inspector.get_columns(view_name)
                    }
                except:
                    continue

        except Exception as e:
            print(f"Ошибка загрузки представлений: {e}")

    def create_view_from_current(self):
        """Создает представление из текущего SQL запроса"""
        if not hasattr(self, 'current_sql_query') or not self.current_sql_query:
            QMessageBox.warning(self, "Ошибка", "Нет текущего SQL запроса для создания представления")
            return

        view_name, ok = QInputDialog.getText(
            self, "Создание представления",
            "Введите имя представления:",
            QLineEdit.Normal, f"view_{self.table}"
        )

        if ok and view_name:
            # Убираем возможные кавычки и пробелы
            view_name = view_name.strip().replace('"', '').replace("'", "")

            if not view_name:
                QMessageBox.warning(self, "Ошибка", "Имя представления не может быть пустым")
                return

            # Проверяем, существует ли уже представление
            if view_name in self.views_cache:
                reply = QMessageBox.question(
                    self, "Подтверждение",
                    f"Представление '{view_name}' уже существует. Перезаписать?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

            # Создаем представление
            create_sql = f"CREATE OR REPLACE VIEW {view_name} AS\n{self.current_sql_query}"

            try:
                with self.engine.begin() as conn:
                    conn.execute(text(create_sql))
                    QMessageBox.information(self, "Успех",
                                            f"Представление '{view_name}' успешно создано")
                    self.load_views_from_db()
                    self.view_created.emit(view_name)

            except Exception as e:
                QMessageBox.critical(self, "Ошибка",
                                     f"Ошибка создания представления: {str(e)}")

    def get_view_names(self) -> List[str]:
        """Возвращает список имен представлений"""
        return list(self.views_cache.keys())

    def get_view_definition(self, view_name: str) -> str:
        """Возвращает определение представления"""
        return self.views_cache.get(view_name, {}).get('definition', '')

    def drop_view(self, view_name: str) -> bool:
        """Удаляет представление"""
        try:
            drop_sql = f"DROP VIEW IF EXISTS {view_name}"
            with self.engine.begin() as conn:
                conn.execute(text(drop_sql))

            # Удаляем из кэша
            if view_name in self.views_cache:
                del self.views_cache[view_name]

            QMessageBox.information(self, "Успех",
                                    f"Представление '{view_name}' удалено")
            self.view_dropped.emit(view_name)
            return True

        except Exception as e:
            QMessageBox.critical(self, "Ошибка",
                                 f"Ошибка удаления представления: {str(e)}")
        return False


class ViewManagerDialog(QDialog):
    """Диалог для управления представлениями"""

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.parent_window = parent

        self.setWindowTitle("Управление представлениями")
        self.setMinimumSize(800, 600)
        self.setup_ui()
        self.load_views()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Список представлений
        list_group = QGroupBox("Список представлений")
        list_layout = QVBoxLayout(list_group)

        self.view_list = QListWidget()
        self.view_list.itemSelectionChanged.connect(self.on_view_selected)
        list_layout.addWidget(self.view_list)

        # Кнопки для списка
        list_buttons = QHBoxLayout()
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.load_views)
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_selected_view)

        list_buttons.addWidget(self.refresh_btn)
        list_buttons.addWidget(self.delete_btn)
        list_buttons.addStretch()

        list_layout.addLayout(list_buttons)
        layout.addWidget(list_group)

        splitter = QSplitter(Qt.Vertical)

        # Информация о представлении
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)

        self.view_name_label = QLabel()
        self.view_name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        info_layout.addWidget(self.view_name_label)

        self.view_sql_text = QTextEdit()
        self.view_sql_text.setReadOnly(True)
        self.view_sql_text.setMaximumHeight(50)
        info_layout.addWidget(QLabel("SQL определение:"))
        info_layout.addWidget(self.view_sql_text)

        # Колонки представления
        self.columns_table = QTableWidget()
        self.columns_table.setColumnCount(3)
        self.columns_table.setHorizontalHeaderLabels(["Имя", "Тип", "Nullable"])
        self.columns_table.horizontalHeader().setStretchLastSection(True)
        info_layout.addWidget(QLabel("Колонки:"))
        info_layout.addWidget(self.columns_table)

        splitter.addWidget(info_widget)

        # Создание нового представления
        create_widget = QWidget()
        create_layout = QVBoxLayout(create_widget)

        create_layout.addWidget(QLabel("Создать новое представление:"))

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Имя:"))
        self.new_view_name = QLineEdit()
        name_layout.addWidget(self.new_view_name)
        create_layout.addLayout(name_layout)

        self.new_view_sql = QTextEdit()
        # self.new_view_sql.setMaximumHeight(200)
        self.new_view_sql.setPlaceholderText("Введите SQL запрос для представления...")
        create_layout.addWidget(QLabel("SQL запрос:"))
        create_layout.addWidget(self.new_view_sql)

        create_btn_layout = QHBoxLayout()
        self.create_from_current = QPushButton("Создать из текущего запроса")
        self.create_from_current.clicked.connect(self.create_from_current_query)
        self.create_btn = QPushButton("Создать представление")
        self.create_btn.clicked.connect(self.create_view)

        create_btn_layout.addWidget(self.create_from_current)
        create_btn_layout.addWidget(self.create_btn)
        create_btn_layout.addStretch()

        create_layout.addLayout(create_btn_layout)
        splitter.addWidget(create_widget)

        splitter.setSizes([300, 300])
        layout.addWidget(splitter)

        # Кнопки диалога
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_views(self):
        """Загружает список представлений"""
        try:
            inspector = inspect(self.engine)
            views = inspector.get_view_names()

            self.view_list.clear()
            for view_name in views:
                self.view_list.addItem(view_name)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить представления: {str(e)}")

    def on_view_selected(self):
        """Обработчик выбора представления в списке"""
        current_item = self.view_list.currentItem()
        if not current_item:
            return

        view_name = current_item.text()

        try:
            inspector = inspect(self.engine)

            # Показываем имя
            self.view_name_label.setText(f"Представление: {view_name}")

            # Получаем и показываем SQL
            view_def = inspector.get_view_definition(view_name)
            self.view_sql_text.setPlainText(view_def or "Не удалось получить определение")

            # Получаем и показываем колонки
            columns = inspector.get_columns(view_name)
            self.columns_table.setRowCount(len(columns))

            for row, column in enumerate(columns):
                self.columns_table.setItem(row, 0, QTableWidgetItem(column['name']))
                self.columns_table.setItem(row, 1, QTableWidgetItem(str(column['type'])))
                self.columns_table.setItem(row, 2, QTableWidgetItem(
                    "Да" if column['nullable'] else "Нет"
                ))

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить информацию: {str(e)}")

    def delete_selected_view(self):
        """Удаляет выбранное представление"""
        current_item = self.view_list.currentItem()
        if not current_item:
            return

        view_name = current_item.text()

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить представление '{view_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.parent_window.drop_view(view_name):
                self.load_views()

    def create_from_current_query(self):
        """Создает представление из текущего SQL запроса родительского окна"""
        if hasattr(self.parent_window, 'current_sql_query'):
            self.new_view_sql.setPlainText(self.parent_window.current_sql_query)
        else:
            QMessageBox.warning(self, "Информация", "Нет текущего запроса для создания представления")

    def create_view(self):
        """Создает новое представление"""
        view_name = self.new_view_name.text().strip()
        sql_query = self.new_view_sql.toPlainText().strip()

        if not view_name:
            QMessageBox.warning(self, "Ошибка", "Введите имя представления")
            return

        if not sql_query:
            QMessageBox.warning(self, "Ошибка", "Введите SQL запрос")
            return

        # Создаем представление
        create_sql = f"CREATE OR REPLACE VIEW {view_name} AS\n{sql_query}"

        try:
            with self.engine.begin() as conn:
                conn.execute(text(create_sql))

            QMessageBox.information(self, "Успех",
                                    f"Представление '{view_name}' успешно создано")

            # Обновляем список и очищаем поля
            self.load_views()
            self.new_view_name.clear()
            self.new_view_sql.clear()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка",
                                 f"Ошибка создания представления: {str(e)}")