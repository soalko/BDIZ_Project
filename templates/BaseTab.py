from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLineEdit, QDialog, QTabWidget, QLabel, QGroupBox, QTextEdit, QCheckBox
from PySide6.QtCore import QSortFilterProxyModel, Qt
from templates.modes import AppMode


class BaseTab(QWidget):
    def __init__(self, engine, tables, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.t = tables
        self.current_mode = AppMode.READ

        # Панель инструментов для всех режимов
        self.tool_panel = QWidget()
        self.tool_layout = QHBoxLayout(self.tool_panel)
        self.tool_layout.setContentsMargins(0, 0, 0, 0)

        # Элементы для режима чтения

        self.sort_combo = QComboBox()
        self.register_combo = QComboBox()
        self.join_btn = QPushButton("JOIN")
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Фильтр...")


        # кнопка фильтрации для режима чтения
        self.filter_button = QPushButton("Фильтрация")
        self.filter_button.clicked.connect(self.open_filter_dialog)

        # Элементы для режима редактирования
        self.add_column_btn = QPushButton("Добавить столбец")
        self.delete_column_btn = QPushButton("Удалить столбец")
        self.edit_column_btn = QPushButton("Изменить столбец")
        self.save_structure_btn = QPushButton("Сохранить структуру")
        self.cancel_structure_btn = QPushButton("Отменить изменения")

        # Отключаем кнопки удаления и изменения изначально
        self.delete_column_btn.setEnabled(False)
        self.edit_column_btn.setEnabled(False)

        # Элементы для режима добавления
        self.add_record_btn = QPushButton("Добавить запись")
        self.clear_form_btn = QPushButton("Очистить форму")
        self.delete_record_btn = QPushButton("Удалить запись")

        self.read_widgets = QWidget()
        self.read_layout = QHBoxLayout(self.read_widgets)
        self.read_layout.setContentsMargins(0, 0, 0, 0)

        self.edit_widgets = QWidget()
        self.edit_layout = QHBoxLayout(self.edit_widgets)
        self.edit_layout.setContentsMargins(0, 0, 0, 0)
        self.add_column_btn = QPushButton("Добавить столбец")
        self.delete_column_btn = QPushButton("Удалить столбец")
        self.edit_column_btn = QPushButton("Изменить столбец")
        self.save_structure_btn = QPushButton("Сохранить структуру")
        self.cancel_structure_btn = QPushButton("Отменить изменения")

        self.add_widgets = QWidget()
        self.add_layout = QHBoxLayout(self.add_widgets)
        self.add_layout.setContentsMargins(0, 0, 0, 0)

        self.setup_ui()
        self.setup_tool_widgets()

    def setup_ui(self):
        self.sort_combo.addItems(["По ID", "По имени", "По дате", "По рейсу"])
        self.register_combo.addItems(["Оригинал", "Верхний регистр", "Нижний регистр"])

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.tool_panel)


    def setup_tool_widgets(self):
        # В РЕЖИМЕ ЧТЕНИЯ показываем только новую кнопку "Фильтрация"
        # Старые элементы намеренно не добавляются в layout, чтобы их не было в интерфейсе
        self.read_layout.addWidget(self.filter_button)
        self.read_layout.addStretch()

        self.edit_layout.addWidget(self.add_column_btn)
        self.edit_layout.addWidget(self.delete_column_btn)
        self.edit_layout.addWidget(self.edit_column_btn)
        self.edit_layout.addWidget(self.save_structure_btn)
        self.edit_layout.addWidget(self.cancel_structure_btn)
        self.edit_layout.addStretch()

        self.add_layout.addWidget(self.add_record_btn)
        self.add_layout.addWidget(self.clear_form_btn)
        self.add_layout.addWidget(self.delete_record_btn)
        self.add_layout.addStretch()

    def set_mode(self, mode: AppMode):
        self.current_mode = mode
        self.update_ui_for_mode()

    def update_ui_for_mode(self):
        for i in reversed(range(self.tool_layout.count())):
            widget = self.tool_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if self.current_mode == AppMode.READ:
            self.tool_layout.addWidget(self.read_widgets)
        elif self.current_mode == AppMode.EDIT:
            self.tool_layout.addWidget(self.edit_widgets)
        elif self.current_mode == AppMode.ADD:
            self.tool_layout.addWidget(self.add_widgets)

        self.tool_panel.setVisible(self.current_mode in [AppMode.READ, AppMode.EDIT, AppMode.ADD])


    # диалог фильтрации и обработчики в режиме чтения

    def open_filter_dialog(self):
        """Открывает диалог построения SQL и передает результат в обработчик"""


        dialog = SQLFilterDialog(self)
        if dialog.exec() == QDialog.Accepted:
            sql_query = dialog.sql_preview.toPlainText().strip()
            if sql_query:
                self.apply_read_filter(sql_query)

    def apply_read_filter(self, sql_query: str):
        """Применение фильтра данных по SQL.

        Комментарий: по умолчанию заглушка. Дочерние вкладки могут переопределить
        этот метод, чтобы выполнить запрос и обновить таблицу.
        """
        # Заглушка: ничего не делаем в базовом классе
        pass


class SQLFilterDialog(QDialog):
    """Диалог для конструирования SQL-запроса фильтрации в режиме чтения.

    ""Диалог не зависит от конкретной таблицы
     он формирует текст SQL, который родительская вкладка
    может выполнить."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Фильтры SQL")
        self.setMinimumSize(900, 1000)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # вкладки для выбора действий SQL
        self.tabs_widget = QTabWidget()

        select_tab = self.create_select_tab()
        self.tabs_widget.addTab(select_tab, "SELECT & FROM")

        where_tab = self.create_where_tab()
        self.tabs_widget.addTab(where_tab, "WHERE")

        group_tab = self.create_group_tab()
        self.tabs_widget.addTab(group_tab, "GROUP BY & HAVING")

        order_tab = self.create_order_tab()
        self.tabs_widget.addTab(order_tab, "ORDER BY")

        # Вкладка JOIN оставлена в диалоге, но убрана из чтения
        join_tab = self.create_join_tab()
        self.tabs_widget.addTab(join_tab, "JOIN")

        layout.addWidget(self.tabs_widget)

        # Кнопки управления
        buttons_row = QHBoxLayout()
        self.apply_button = QPushButton("Применить фильтр")  # подтверждение выбора
        self.apply_button.clicked.connect(self.apply_filter)
        self.reset_button = QPushButton("Сбросить")  # сброс всех полей
        self.reset_button.clicked.connect(self.reset_filters)
        self.close_button = QPushButton("Закрыть")  # закрыть диалог
        self.close_button.clicked.connect(self.close)

        buttons_row.addWidget(self.apply_button)
        buttons_row.addWidget(self.reset_button)
        buttons_row.addStretch()
        buttons_row.addWidget(self.close_button)

        layout.addLayout(buttons_row)

        # Предпросмотр SQL
        layout.addWidget(QLabel("Предпросмотр SQL:"))
        self.sql_preview = QTextEdit()
        self.sql_preview.setPlaceholderText("Полученный SQL запрос")
        self.sql_preview.setMaximumHeight(100)
        layout.addWidget(self.sql_preview)

    def create_select_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)

        # FROM — выбор таблицы
        from_group = QGroupBox("FROM - Выбор таблицы")
        from_layout = QVBoxLayout(from_group)
        self.table_combo = QComboBox()
        # список таблиц БД
        self.table_combo.addItems(["Самолеты", "Рейсы", "Пассажиры", "Билеты", "Экипажи", "Члены экипажа"])
        from_layout.addWidget(QLabel("Основная таблица:"))
        from_layout.addWidget(self.table_combo)

        # SELECT — выбор колонок и функций
        select_group = QGroupBox("SELECT - Выбор колонок и функций")
        select_layout = QVBoxLayout(select_group)

        # cтолбцы
        self.columns_widget = QWidget()
        columns_layout = QVBoxLayout(self.columns_widget)
        self.column_checkboxes = {}
        sample_columns = ["aircraft_id", "model", "year", "seats_amount", "baggage_capacity"]
        for column_name in sample_columns:
            checkbox = QCheckBox(column_name)
            checkbox.setChecked(True)
            self.column_checkboxes[column_name] = checkbox
            columns_layout.addWidget(checkbox)

        # Функции SQL
        functions_group = QGroupBox("SQL функции")
        functions_layout = QVBoxLayout(functions_group)
        self.functions_combo = QComboBox()
        self.functions_combo.addItems([
            "COUNT", "AVG", "SUM", "MAX", "MIN",
            "UPPER", "LOWER", "CONCAT", "SUBSTRING",
            "TRIM", "LPAD", "RPAD",
        ])
        self.function_column_combo = QComboBox()
        self.function_column_combo.addItems(sample_columns)
        self.function_alias_edit = QLineEdit()
        self.function_alias_edit.setPlaceholderText("Название нового столбца с функцией (AS)")
        self.add_function_button = QPushButton("Добавить функцию")
        self.add_function_button.clicked.connect(self.add_function)

        functions_layout.addWidget(QLabel("Функция:"))
        functions_layout.addWidget(self.functions_combo)
        functions_layout.addWidget(QLabel("Колонка:"))
        functions_layout.addWidget(self.function_column_combo)
        functions_layout.addWidget(QLabel("Новый столбец:"))
        functions_layout.addWidget(self.function_alias_edit)
        functions_layout.addWidget(self.add_function_button)

        self.added_functions_list = QTextEdit()
        self.added_functions_list.setMaximumHeight(100)
        self.added_functions_list.setPlaceholderText("Добавленные функции")

        select_layout.addWidget(QLabel("Базовые колонки:"))
        select_layout.addWidget(self.columns_widget)
        select_layout.addWidget(functions_group)
        select_layout.addWidget(QLabel("Добавленные функции:"))
        select_layout.addWidget(self.added_functions_list)

        vbox.addWidget(from_group)
        vbox.addWidget(select_group)
        return tab

    def create_where_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)

        where_group = QGroupBox("WHERE - Условия фильтрации")
        where_layout = QVBoxLayout(where_group)

        simple_where = QGroupBox("Простое условие")
        simple_layout = QHBoxLayout(simple_where)

        self.where_column_combo = QComboBox()
        self.where_column_combo.addItems(["aircraft_id", "model", "year", "seats_amount", "baggage_capacity"])
        self.where_operator_combo = QComboBox()
        self.where_operator_combo.addItems(["=", "!=", ">", "<", ">=", "<=", "LIKE", "IN", "BETWEEN"])
        self.where_value_edit = QLineEdit()
        self.where_value_edit.setPlaceholderText("Значение для фильтрации")
        self.add_where_button = QPushButton("Добавить условие")
        self.add_where_button.clicked.connect(self.add_where_condition)

        simple_layout.addWidget(self.where_column_combo)
        simple_layout.addWidget(self.where_operator_combo)
        simple_layout.addWidget(self.where_value_edit)
        simple_layout.addWidget(self.add_where_button)

        self.where_conditions_list = QTextEdit()
        self.where_conditions_list.setMaximumHeight(150)
        self.where_conditions_list.setPlaceholderText("Добавленные условия WHERE")

        where_layout.addWidget(simple_where)
        where_layout.addWidget(QLabel("Текущие условия:"))
        where_layout.addWidget(self.where_conditions_list)

        vbox.addWidget(where_group)
        return tab

    def create_group_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)

        group_group = QGroupBox("GROUP BY - Группировка")
        group_layout = QVBoxLayout(group_group)
        self.group_column_combo = QComboBox()
        self.group_column_combo.addItems(["aircraft_id", "model", "year", "seats_amount", "baggage_capacity"])
        self.add_group_button = QPushButton("Добавить группировку")
        self.add_group_button.clicked.connect(self.add_group_column)
        self.group_columns_list = QTextEdit()
        self.group_columns_list.setMaximumHeight(80)
        self.group_columns_list.setPlaceholderText("Колонки для группировки")
        group_layout.addWidget(QLabel("Колонка для группировки:"))
        group_layout.addWidget(self.group_column_combo)
        group_layout.addWidget(self.add_group_button)
        group_layout.addWidget(QLabel("Колонки GROUP BY:"))
        group_layout.addWidget(self.group_columns_list)

        having_group = QGroupBox("HAVING - Условия для сгруппированных данных")
        having_layout = QVBoxLayout(having_group)
        self.having_function_combo = QComboBox()
        self.having_function_combo.addItems(["COUNT", "AVG", "SUM", "MAX", "MIN"])
        self.having_column_combo = QComboBox()
        self.having_column_combo.addItems(["aircraft_id", "model", "year", "seats_amount", "baggage_capacity"])
        self.having_operator_combo = QComboBox()
        self.having_operator_combo.addItems([">", "<", "=", "!=", ">=", "<="])
        self.having_value_edit = QLineEdit()
        self.having_value_edit.setPlaceholderText("Значение")
        self.add_having_button = QPushButton("Добавить условие HAVING")
        self.add_having_button.clicked.connect(self.add_having_condition)
        self.having_conditions_list = QTextEdit()
        self.having_conditions_list.setMaximumHeight(80)
        self.having_conditions_list.setPlaceholderText("Условия HAVING")
        having_layout.addWidget(QLabel("Функция:"))
        having_layout.addWidget(self.having_function_combo)
        having_layout.addWidget(QLabel("Колонка:"))
        having_layout.addWidget(self.having_column_combo)
        having_layout.addWidget(QLabel("Оператор:"))
        having_layout.addWidget(self.having_operator_combo)
        having_layout.addWidget(QLabel("Значение:"))
        having_layout.addWidget(self.having_value_edit)
        having_layout.addWidget(self.add_having_button)
        having_layout.addWidget(QLabel("Условия HAVING:"))
        having_layout.addWidget(self.having_conditions_list)

        vbox.addWidget(group_group)
        vbox.addWidget(having_group)
        return tab

    def create_order_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)
        order_group = QGroupBox("ORDER BY - Сортировка")
        order_layout = QVBoxLayout(order_group)
        self.order_column_combo = QComboBox()
        self.order_column_combo.addItems(["aircraft_id", "model", "year", "seats_amount", "baggage_capacity"])
        self.order_direction_combo = QComboBox()
        self.order_direction_combo.addItems(["По возрастанию", "По убыванию"])
        self.add_order_button = QPushButton("Сортировать")
        self.add_order_button.clicked.connect(self.add_order_column)
        self.order_columns_list = QTextEdit()
        self.order_columns_list.setMaximumHeight(150)
        self.order_columns_list.setPlaceholderText("Колонки для сортировки")
        order_layout.addWidget(QLabel("Колонка:"))
        order_layout.addWidget(self.order_column_combo)
        order_layout.addWidget(QLabel("Как сортировать:"))
        order_layout.addWidget(self.order_direction_combo)
        order_layout.addWidget(self.add_order_button)
        order_layout.addWidget(QLabel("Порядок сортировки:"))
        order_layout.addWidget(self.order_columns_list)
        vbox.addWidget(order_group)
        return tab

    def create_join_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)
        join_group = QGroupBox("JOIN - Объединение таблиц")
        join_layout = QVBoxLayout(join_group)
        self.join_type_combo = QComboBox()
        self.join_type_combo.addItems(["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN"])
        self.join_table_combo = QComboBox()
        self.join_table_combo.addItems(["Самолеты", "Рейсы", "Пассажиры", "Билеты", "Экипажи", "Члены экипажа"])
        self.join_condition_edit = QLineEdit()
        self.join_condition_edit.setPlaceholderText("Условие JOIN (например:aircrafts.aircraft_id = flights.flight_id)")
        self.add_join_button = QPushButton("Добавить JOIN")
        self.add_join_button.clicked.connect(self.add_join)
        self.joins_list = QTextEdit()
        self.joins_list.setMaximumHeight(150)
        self.joins_list.setPlaceholderText("Добавленные JOIN")
        join_layout.addWidget(QLabel("Тип JOIN:"))
        join_layout.addWidget(self.join_type_combo)
        join_layout.addWidget(QLabel("Таблица:"))
        join_layout.addWidget(self.join_table_combo)
        join_layout.addWidget(QLabel("Условие:"))
        join_layout.addWidget(self.join_condition_edit)
        join_layout.addWidget(self.add_join_button)
        join_layout.addWidget(QLabel("Текущие JOIN:"))
        join_layout.addWidget(self.joins_list)
        vbox.addWidget(join_group)
        return tab

    #Обработчики построения SQL
    def add_function(self):
        function = self.functions_combo.currentText()
        column = self.function_column_combo.currentText()
        alias = self.function_alias_edit.text().strip()
        if not column:
            return
        function_text = f"{function}({column})"
        if alias:
            function_text += f" AS {alias}"
        current_text = self.added_functions_list.toPlainText()
        current_text = (current_text + "\n" if current_text else "") + function_text
        self.added_functions_list.setPlainText(current_text)
        self.function_alias_edit.clear()
        self.update_sql_preview()

    def add_where_condition(self):
        column = self.where_column_combo.currentText()
        operator = self.where_operator_combo.currentText()
        value = self.where_value_edit.text().strip()
        if not value:
            return
        if operator.upper() == "LIKE":
            value = f"'%{value}%'"
        elif operator.upper() == "IN":
            value = f"({value})"
        elif operator.upper() == "BETWEEN":
            parts = value.split()
            if len(parts) == 2:
                value = f"{parts[0]} AND {parts[1]}"
        condition = f"{column} {operator} {value}"
        current_text = self.where_conditions_list.toPlainText()
        current_text = (current_text + "\nAND " if current_text else "") + condition
        self.where_conditions_list.setPlainText(current_text)
        self.where_value_edit.clear()
        self.update_sql_preview()

    def add_group_column(self):
        column = self.group_column_combo.currentText()
        current_text = self.group_columns_list.toPlainText()
        current_text = (current_text + ", " if current_text else "") + column
        self.group_columns_list.setPlainText(current_text)
        self.update_sql_preview()

    def add_having_condition(self):
        function = self.having_function_combo.currentText()
        column = self.having_column_combo.currentText()
        operator = self.having_operator_combo.currentText()
        value = self.having_value_edit.text().strip()
        if not value:
            return
        condition = f"{function}({column}) {operator} {value}"
        current_text = self.having_conditions_list.toPlainText()
        current_text = (current_text + "\nAND " if current_text else "") + condition
        self.having_conditions_list.setPlainText(current_text)
        self.having_value_edit.clear()
        self.update_sql_preview()

    def add_order_column(self):
        column = self.order_column_combo.currentText()
        direction = self.order_direction_combo.currentText()
        order_text = f"{column} {direction}"
        current_text = self.order_columns_list.toPlainText()
        current_text = (current_text + ", " if current_text else "") + order_text
        self.order_columns_list.setPlainText(current_text)
        self.update_sql_preview()

    def add_join(self):
        join_type = self.join_type_combo.currentText()
        table = self.join_table_combo.currentText()
        condition = self.join_condition_edit.text().strip()
        if not condition:
            return
        join_text = f"{join_type} {table} ON {condition}"
        current_text = self.joins_list.toPlainText()
        current_text = (current_text + "\n" if current_text else "") + join_text
        self.joins_list.setPlainText(current_text)
        self.join_condition_edit.clear()
        self.update_sql_preview()

    def update_sql_preview(self):
        # Сборка SQL частей из введенных пользователем элементов
        sql_parts = []
        select_columns = []
        for col_name, cb in self.column_checkboxes.items():
            if cb.isChecked():
                select_columns.append(col_name)
        functions_text = self.added_functions_list.toPlainText()
        if functions_text:
            select_columns.extend(functions_text.split("\n"))
        select_part = "SELECT " + (", ".join(select_columns) if select_columns else "*")
        sql_parts.append(select_part)
        from_part = f"FROM {self.table_combo.currentText()}"
        sql_parts.append(from_part)
        joins_text = getattr(self, "joins_list", QTextEdit()).toPlainText()
        if joins_text:
            sql_parts.append(joins_text)
        where_text = self.where_conditions_list.toPlainText()
        if where_text:
            sql_parts.append(f"WHERE {where_text}")
        group_text = self.group_columns_list.toPlainText()
        if group_text:
            sql_parts.append(f"GROUP BY {group_text}")
        having_text = self.having_conditions_list.toPlainText()
        if having_text:
            sql_parts.append(f"HAVING {having_text}")
        order_text = self.order_columns_list.toPlainText()
        if order_text:
            sql_parts.append(f"ORDER BY {order_text}")
        self.sql_preview.setPlainText("\n".join(sql_parts))

    def apply_filter(self):
        # обновление предпросмотра и закрываем с подтверждением, если SQL запрос непустой
        self.update_sql_preview()
        sql = self.sql_preview.toPlainText().strip()
        if not sql or sql == "Полученный SQL запрос":
            return
        self.accept()

    def reset_filters(self):
        # cброс всех полей диалога к значениям по умолчанию
        for cb in self.column_checkboxes.values():
            cb.setChecked(True)
        self.added_functions_list.clear()
        self.where_conditions_list.clear()
        self.group_columns_list.clear()
        self.having_conditions_list.clear()
        self.order_columns_list.clear()
        if hasattr(self, "joins_list"):
            self.joins_list.clear()
        self.table_combo.setCurrentIndex(0)
        self.functions_combo.setCurrentIndex(0)
        self.function_column_combo.setCurrentIndex(0)
        self.where_column_combo.setCurrentIndex(0)
        self.where_operator_combo.setCurrentIndex(0)
        self.group_column_combo.setCurrentIndex(0)
        self.having_function_combo.setCurrentIndex(0)
        self.having_column_combo.setCurrentIndex(0)
        self.having_operator_combo.setCurrentIndex(0)
        self.order_column_combo.setCurrentIndex(0)
        self.order_direction_combo.setCurrentIndex(0)
        if hasattr(self, "join_type_combo"):
            self.join_type_combo.setCurrentIndex(0)
        if hasattr(self, "join_table_combo"):
            self.join_table_combo.setCurrentIndex(0)
        self.update_sql_preview()