from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox,
    QPushButton, QFormLayout, QTableView,
    QComboBox, QLineEdit, QDialog,
    QLabel, QTabWidget, QTextEdit,
    QGroupBox, QHBoxLayout, QDialogButtonBox,
    QMessageBox, QScrollArea
)

from PySide6.QtCore import (Qt)


class SQLFilterDialog(QDialog):
    def __init__(self, parent=None, current_table=""):
        super().__init__(parent)
        self.current_table = current_table
        self.setWindowTitle("Фильтры SQL")
        self.setMinimumSize(900, 600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        self.tabs_widget = QTabWidget()

        select_tab = self.create_select_tab()
        self.tabs_widget.addTab(select_tab, "SELECT")

        where_tab = self.create_where_tab()
        self.tabs_widget.addTab(where_tab, "WHERE & ORDER BY")

        group_tab = self.create_group_tab()
        self.tabs_widget.addTab(group_tab, "GROUP BY & HAVING")

        join_tab = self.create_join_tab()
        self.tabs_widget.addTab(join_tab, "JOIN")

        advanced_tab = self.create_advanced_tab()
        self.tabs_widget.addTab(advanced_tab, "ADVANCED")

        null_functions_tab = self.create_null_functions_tab()
        self.tabs_widget.addTab(null_functions_tab, "NULL FUNCTIONS")

        case_tab = self.create_case_tab()
        self.tabs_widget.addTab(case_tab, "CASE EXPRESSIONS")

        main_layout.addWidget(self.tabs_widget)

        buttons_row = QHBoxLayout()
        self.apply_button = QPushButton("Применить")
        self.apply_button.clicked.connect(self.apply_filter)
        self.reset_button = QPushButton("Сбросить")
        self.reset_button.clicked.connect(self.reset_filters)
        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.close)

        buttons_row.addWidget(self.apply_button)
        buttons_row.addWidget(self.reset_button)
        buttons_row.addStretch()
        buttons_row.addWidget(self.close_button)

        main_layout.addLayout(buttons_row)

        scroll_area.setWidget(main_widget)
        layout.addWidget(scroll_area)

    def get_all_tables_columns(self) -> dict:
        tables_columns = {}
        for table_name in self.tables.keys():
            columns = self.get_table_columns(table_name)
            tables_columns[table_name] = columns
        return tables_columns

    def create_select_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)

        select_group = QGroupBox("SELECT - Выбор колонок и функций")
        select_layout = QVBoxLayout(select_group)

        self.columns_widget = QWidget()
        columns_layout = QVBoxLayout(self.columns_widget)
        self.column_checkboxes = {}

        parent = self.parent()
        if parent and hasattr(parent, 'get_table_columns'):
            sample_columns = parent.get_table_columns(self.current_table)
        else:
            sample_columns = ["aircraft_id", "model", "year", "seats_amount", "baggage_capacity"]

        for column_name in sample_columns:
            checkbox = QCheckBox(column_name)
            checkbox.setChecked(True)
            self.column_checkboxes[column_name] = checkbox
            columns_layout.addWidget(checkbox)

        functions_group = QGroupBox("SQL функции")
        functions_layout = QVBoxLayout(functions_group)

        self.functions_label = QLabel("Функция:")
        self.functions_combo = QComboBox()
        self.functions_combo.addItems([
            "UPPER", "LOWER", "TRIM",
            "SUBSTRING", "LPAD", "RPAD",
            "CONCAT"
        ])

        self.function_column_label = QLabel("Колонка:")
        self.function_column_combo = QComboBox()
        self.function_column_combo.addItems(sample_columns)

        self.function_alias_label = QLabel("Новый столбец:")
        self.function_alias_edit = QLineEdit()
        self.function_alias_edit.setPlaceholderText("Название нового столбца с функцией (AS)")

        self.function_string_label = QLabel("Строка")
        self.function_string_edit = QLineEdit()
        self.function_string_edit.setPlaceholderText("Строка")

        self.function_column2_label = QLabel("Колонка 2:")
        self.function_column2_combo = QComboBox()
        self.function_column2_combo.addItems(sample_columns)

        self.add_function_button = QPushButton("Добавить функцию")
        self.add_function_button.clicked.connect(self.add_function)

        functions_layout.addWidget(self.functions_label)
        functions_layout.addWidget(self.functions_combo)
        functions_layout.addWidget(self.function_column_label)
        functions_layout.addWidget(self.function_column_combo)
        functions_layout.addWidget(self.function_string_label)
        functions_layout.addWidget(self.function_string_edit)
        functions_layout.addWidget(self.function_column2_label)
        functions_layout.addWidget(self.function_column2_combo)
        functions_layout.addWidget(self.function_alias_label)
        functions_layout.addWidget(self.function_alias_edit)
        functions_layout.addWidget(self.add_function_button)
        self.function_string_label.setVisible(False)
        self.function_string_edit.setVisible(False)
        self.function_column2_label.setVisible(False)
        self.function_column2_combo.setVisible(False)

        self.added_functions_list = QTextEdit()
        self.added_functions_list.setMaximumHeight(100)
        self.added_functions_list.setPlaceholderText("Добавленные функции")

        def functions_combo_changed(text):
            index = self.functions_combo.currentIndex()
            self.function_string_label.setVisible(False)
            self.function_string_edit.setVisible(False)
            self.function_column2_label.setVisible(False)
            self.function_column2_combo.setVisible(False)
            if index in [3, 4, 5]:
                self.function_string_label.setVisible(True)
                self.function_string_edit.setVisible(True)
            if index in [6]:
                self.function_column2_label.setVisible(True)
                self.function_column2_combo.setVisible(True)
                self.add_function_button.setVisible(True)

        self.functions_combo.activated.connect(functions_combo_changed)

        select_layout.addWidget(QLabel("Базовые колонки:"))
        select_layout.addWidget(self.columns_widget)
        select_layout.addWidget(functions_group)
        select_layout.addWidget(QLabel("Добавленные функции:"))
        select_layout.addWidget(self.added_functions_list)

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

        parent = self.parent()
        if parent and hasattr(parent, 'get_table_columns'):
            where_columns = parent.get_table_columns(self.current_table)
            self.where_column_combo.addItems(where_columns)
        else:
            self.where_column_combo.addItems(["aircraft_id", "model", "year", "seats_amount", "baggage_capacity"])

        self.where_operator_combo = QComboBox()
        self.where_operator_combo.addItems(["=", "!=", ">", "<", ">=", "<=",
                                            "LIKE", "IN", "~", "~*", "!~", "!~*",
                                            "SIMILAR TO", "NOT SIMILAR TO"])
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

        order_group = QGroupBox("ORDER BY - Сортировка")
        order_layout = QVBoxLayout(order_group)
        self.order_column_combo = QComboBox()
        self.order_column_combo.addItems(["aircraft_id", "model", "year", "seats_amount", "baggage_capacity"])
        self.order_direction_combo = QComboBox()
        self.order_direction_combo.addItems(["ASC", "DESC"])
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

    def create_group_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)

        group_group = QGroupBox("GROUP BY - Группировка")
        group_layout = QVBoxLayout(group_group)
        self.group_column_combo = QComboBox()
        parent = self.parent()
        if parent and hasattr(parent, 'get_table_columns'):
            group_columns = parent.get_table_columns(self.current_table)
            self.group_column_combo.addItems(group_columns)
        else:
            self.group_column_combo.addItems(["aircraft_id", "model", "year", "seats_amount", "baggage_capacity"])

        self.add_group_button = QPushButton("Добавить группировку")
        self.add_group_button.clicked.connect(self.add_group_column)
        self.group_columns_list = QTextEdit()
        group_layout.addWidget(self.group_column_combo)
        group_layout.addWidget(self.add_group_button)
        group_layout.addWidget(QLabel("Колонки GROUP BY:"))
        group_layout.addWidget(self.group_columns_list)

        having_group = QGroupBox("HAVING - Условия для сгруппированных данных")
        having_layout = QVBoxLayout(having_group)
        self.having_column_combo = QComboBox()

        if parent and hasattr(parent, 'get_table_columns'):
            having_columns = parent.get_table_columns(self.current_table)
            self.having_column_combo.addItems(having_columns)
        else:
            self.having_column_combo.addItems(["aircraft_id", "model", "year", "seats_amount", "baggage_capacity"])

        self.having_operator_combo = QComboBox()
        self.having_operator_combo.addItems([">", "<", "=", "!=", ">=", "<="])
        self.having_function_combo = QComboBox()
        self.having_function_combo.addItems(["COUNT", "AVG", "SUM", "MAX", "MIN"])
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

    def create_join_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)

        join_group = QGroupBox("JOIN - Объединение таблиц")
        join_layout = QVBoxLayout(join_group)

        join_layout.addWidget(QLabel("Тип JOIN:"))
        self.join_type_combo = QComboBox()
        self.join_type_combo.addItems(["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN"])
        join_layout.addWidget(self.join_type_combo)

        join_layout.addWidget(QLabel("Таблица для JOIN:"))
        self.join_table_combo = QComboBox()

        parent = self.parent()
        if parent and hasattr(parent, 'tables') and parent.tables:
            for table_name in parent.tables.keys():
                if table_name != self.current_table:  # Исключаем текущую таблицу
                    self.join_table_combo.addItem(table_name)
        else:
            sample_tables = ["flights", "passengers", "tickets", "crew", "crew_members"]
            for table in sample_tables:
                if table != self.current_table:
                    self.join_table_combo.addItem(table)

        join_layout.addWidget(self.join_table_combo)

        join_layout.addWidget(QLabel(f"Колонка из {self.current_table}:"))
        self.join_main_column_combo = QComboBox()

        if parent and hasattr(parent, 'get_table_columns'):
            main_columns = parent.get_table_columns(self.current_table)
            self.join_main_column_combo.addItems(main_columns)
        else:
            main_columns = ["aircraft_id", "model", "year", "seats_amount", "baggage_capacity"]
            self.join_main_column_combo.addItems(main_columns)

        self.join_main_column_combo.addItems(main_columns)
        join_layout.addWidget(self.join_main_column_combo)

        join_layout.addWidget(QLabel("Колонка из присоединяемой таблицы:"))
        self.join_foreign_column_combo = QComboBox()

        # Заполняем колонками из присоединяемой таблицы
        foreign_columns = ["aircraft_id", "flight_id", "passenger_id", "ticket_id", "crew_id"]
        self.join_foreign_column_combo.addItems(foreign_columns)
        join_layout.addWidget(self.join_foreign_column_combo)

        self.add_join_button = QPushButton("Добавить JOIN")
        self.add_join_button.clicked.connect(self.add_join)
        join_layout.addWidget(self.add_join_button)

        join_layout.addWidget(QLabel("Добавленные JOIN:"))
        self.joins_list = QTextEdit()
        self.joins_list.setMaximumHeight(150)
        self.joins_list.setPlaceholderText("Добавленные JOIN будут отображаться здесь")
        join_layout.addWidget(self.joins_list)

        self.clear_joins_button = QPushButton("Очистить все JOIN")
        self.clear_joins_button.clicked.connect(self.clear_joins)
        join_layout.addWidget(self.clear_joins_button)

        vbox.addWidget(join_group)
        return tab

    def create_advanced_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)

        # Подзапросы
        subquery_group = QGroupBox("Подзапросы (ANY, ALL, EXISTS)")
        subquery_layout = QVBoxLayout(subquery_group)

        # Основное условие
        condition_layout = QHBoxLayout()
        condition_layout.addWidget(QLabel("Колонка:"))
        self.adv_column_combo = QComboBox()

        # Заполняем колонками текущей таблицы
        parent = self.parent()
        if parent and hasattr(parent, 'get_table_columns'):
            adv_columns = parent.get_table_columns(self.current_table)
            self.adv_column_combo.addItems(adv_columns)
        else:
            sample_columns = ["aircraft_id", "model", "year", "seats_amount", "baggage_capacity"]
            self.adv_column_combo.addItems(sample_columns)

        condition_layout.addWidget(self.adv_column_combo)

        condition_layout.addWidget(QLabel("Оператор:"))
        self.adv_operator_combo = QComboBox()
        self.adv_operator_combo.addItems([
            "IN", "NOT IN",
            "= ANY", "!= ANY", "> ANY", "< ANY", ">= ANY", "<= ANY",
            "= ALL", "!= ALL", "> ALL", "< ALL", ">= ALL", "<= ALL",
            "EXISTS", "NOT EXISTS"
        ])
        condition_layout.addWidget(self.adv_operator_combo)

        subquery_layout.addLayout(condition_layout)

        # Конструктор подзапроса
        subquery_builder = QGroupBox("Конструктор подзапроса")
        builder_layout = QVBoxLayout(subquery_builder)

        # Выбор таблицы для подзапроса
        table_layout = QHBoxLayout()
        table_layout.addWidget(QLabel("Таблица подзапроса:"))
        self.adv_subquery_table_combo = QComboBox()

        if parent and hasattr(parent, 'tables') and parent.tables:
            for table_name in parent.tables.keys():
                if table_name != self.current_table:
                    self.adv_subquery_table_combo.addItem(table_name)
        else:
            sample_tables = ["flights", "passengers", "tickets", "crew", "crew_members"]
            for table in sample_tables:
                if table != self.current_table:
                    self.adv_subquery_table_combo.addItem(table)

        table_layout.addWidget(self.adv_subquery_table_combo)
        subquery_layout.addLayout(table_layout)

        # Выбор колонки для подзапроса
        column_layout = QHBoxLayout()
        column_layout.addWidget(QLabel("Колонка подзапроса:"))
        self.adv_subquery_column_combo = QComboBox()
        # Заполнение колонок будет при изменении таблицы
        self.adv_subquery_table_combo.currentTextChanged.connect(self.update_adv_subquery_columns)
        self.update_adv_subquery_columns(self.adv_subquery_table_combo.currentText())
        column_layout.addWidget(self.adv_subquery_column_combo)
        subquery_layout.addLayout(column_layout)

        # Условие WHERE для подзапроса
        where_layout = QHBoxLayout()
        where_layout.addWidget(QLabel("Условие WHERE:"))
        self.adv_subquery_where_edit = QLineEdit()
        self.adv_subquery_where_edit.setPlaceholderText("опционально, например: year > 2020")
        where_layout.addWidget(self.adv_subquery_where_edit)
        subquery_layout.addLayout(where_layout)

        # Кнопка построения подзапроса
        self.adv_build_subquery_btn = QPushButton("Построить подзапрос")
        self.adv_build_subquery_btn.clicked.connect(self.build_adv_subquery)
        subquery_layout.addWidget(self.adv_build_subquery_btn)

        # Список добавленных условий
        self.adv_conditions_list = QTextEdit()
        self.adv_conditions_list.setMaximumHeight(100)
        self.adv_conditions_list.setPlaceholderText("Добавленные условия с подзапросами")
        subquery_layout.addWidget(QLabel("Текущие условия:"))
        subquery_layout.addWidget(self.adv_conditions_list)

        vbox.addWidget(subquery_group)

        vbox.addWidget(subquery_group)

        return tab

    def create_null_functions_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)

        # COALESCE
        coalesce_group = QGroupBox("COALESCE - Возвращает первое ненулевое значение")
        coalesce_layout = QVBoxLayout(coalesce_group)

        # Поле для значений
        values_layout = QHBoxLayout()
        values_layout.addWidget(QLabel("Значения (через запятую):"))
        self.null_coalesce_values_edit = QLineEdit()
        self.null_coalesce_values_edit.setPlaceholderText("column1, 'default_value', column2")
        values_layout.addWidget(self.null_coalesce_values_edit)
        coalesce_layout.addLayout(values_layout)

        # Псевдоним
        alias_layout = QHBoxLayout()
        alias_layout.addWidget(QLabel("Псевдоним:"))
        self.null_coalesce_alias_edit = QLineEdit()
        self.null_coalesce_alias_edit.setPlaceholderText("result_column")
        alias_layout.addWidget(self.null_coalesce_alias_edit)
        coalesce_layout.addLayout(alias_layout)

        # Кнопка добавления
        self.null_add_coalesce_btn = QPushButton("Добавить COALESCE")
        self.null_add_coalesce_btn.clicked.connect(self.add_null_coalesce)
        coalesce_layout.addWidget(self.null_add_coalesce_btn)

        vbox.addWidget(coalesce_group)

        # NULLIF
        nullif_group = QGroupBox("NULLIF - Возвращает NULL если значения равны")
        nullif_layout = QVBoxLayout(nullif_group)

        # Значение 1
        value1_layout = QHBoxLayout()
        value1_layout.addWidget(QLabel("Значение 1:"))
        self.null_nullif_value1_edit = QLineEdit()
        self.null_nullif_value1_edit.setPlaceholderText("column1 или значение")
        value1_layout.addWidget(self.null_nullif_value1_edit)
        nullif_layout.addLayout(value1_layout)

        # Значение 2
        value2_layout = QHBoxLayout()
        value2_layout.addWidget(QLabel("Значение 2:"))
        self.null_nullif_value2_edit = QLineEdit()
        self.null_nullif_value2_edit.setPlaceholderText("column2 или значение")
        value2_layout.addWidget(self.null_nullif_value2_edit)
        nullif_layout.addLayout(value2_layout)

        # Псевдоним
        nullif_alias_layout = QHBoxLayout()
        nullif_alias_layout.addWidget(QLabel("Псевдоним:"))
        self.null_nullif_alias_edit = QLineEdit()
        self.null_nullif_alias_edit.setPlaceholderText("result_column")
        nullif_alias_layout.addWidget(self.null_nullif_alias_edit)
        nullif_layout.addLayout(nullif_alias_layout)

        # Кнопка добавления
        self.null_add_nullif_btn = QPushButton("Добавить NULLIF")
        self.null_add_nullif_btn.clicked.connect(self.add_null_nullif)
        nullif_layout.addWidget(self.null_add_nullif_btn)

        vbox.addWidget(nullif_group)

        # Список добавленных функций NULL
        self.null_functions_list = QTextEdit()
        self.null_functions_list.setMaximumHeight(150)
        self.null_functions_list.setPlaceholderText("Добавленные функции NULL будут отображаться здесь")
        vbox.addWidget(QLabel("Добавленные функции NULL:"))
        vbox.addWidget(self.null_functions_list)

        # Кнопка очистки
        clear_layout = QHBoxLayout()
        self.null_clear_btn = QPushButton("Очистить список")
        self.null_clear_btn.clicked.connect(self.clear_null_functions)
        clear_layout.addWidget(self.null_clear_btn)
        clear_layout.addStretch()
        vbox.addLayout(clear_layout)

        return tab

    def add_null_coalesce(self):
        """Добавляет COALESCE функцию в список"""
        values = self.null_coalesce_values_edit.text().strip()
        alias = self.null_coalesce_alias_edit.text().strip()

        if not values:
            QMessageBox.warning(self, "Ошибка", "Введите значения для COALESCE")
            return

        # Форматируем значения
        formatted_values = []
        for val in values.split(','):
            val = val.strip()
            # Если это не число и не колонка, заключаем в кавычки
            if not val.replace('.', '').isdigit() and not self._is_column_reference(val):
                formatted_values.append(f"'{val}'")
            else:
                formatted_values.append(val)

        values_str = ", ".join(formatted_values)
        expr = f"COALESCE({values_str})"

        if alias:
            expr += f" AS {alias}"

        self._add_to_null_functions_list(expr)

        # Очищаем поля
        self.null_coalesce_values_edit.clear()
        self.null_coalesce_alias_edit.clear()

    def add_null_nullif(self):
        """Добавляет NULLIF функцию в список"""
        value1 = self.null_nullif_value1_edit.text().strip()
        value2 = self.null_nullif_value2_edit.text().strip()
        alias = self.null_nullif_alias_edit.text().strip()

        if not value1 or not value2:
            QMessageBox.warning(self, "Ошибка", "Введите оба значения для NULLIF")
            return

        # Форматируем значения
        val1 = self._format_value(value1)
        val2 = self._format_value(value2)

        expr = f"NULLIF({val1}, {val2})"

        if alias:
            expr += f" AS {alias}"

        self._add_to_null_functions_list(expr)

        # Очищаем поля
        self.null_nullif_value1_edit.clear()
        self.null_nullif_value2_edit.clear()
        self.null_nullif_alias_edit.clear()

    def create_case_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)

        # Конструктор CASE выражения
        case_builder_group = QGroupBox("Конструктор CASE выражения")
        case_builder_layout = QVBoxLayout(case_builder_group)

        # Псевдоним
        alias_layout = QHBoxLayout()
        alias_layout.addWidget(QLabel("Псевдоним для результата:"))
        self.case_alias_edit = QLineEdit()
        self.case_alias_edit.setPlaceholderText("result_column")
        alias_layout.addWidget(self.case_alias_edit)
        case_builder_layout.addLayout(alias_layout)

        # Условия WHEN-THEN

        """Добавляет новое условие WHEN-THEN в конструктор"""
        condition_widget = QWidget()
        condition_layout = QHBoxLayout(condition_widget)

        # Поле WHEN
        when_edit = QLineEdit()
        when_edit.setPlaceholderText("условие, например: year > 2018")
        when_edit.textChanged.connect(self.update_case_preview)
        self.when = when_edit

        # Поле THEN
        then_edit = QLineEdit()
        then_edit.setPlaceholderText("результат, например: 'Скоро'")
        self.then = then_edit

        condition_layout.addWidget(QLabel("WHEN"))
        condition_layout.addWidget(when_edit)
        condition_layout.addWidget(QLabel("THEN"))
        condition_layout.addWidget(then_edit)

        case_builder_layout.addWidget(condition_widget)

        # ELSE часть
        else_group = QWidget()
        else_layout = QHBoxLayout(else_group)
        else_layout.addWidget(QLabel("ELSE значение:"))
        self.case_else_edit = QLineEdit()
        self.case_else_edit.setPlaceholderText("значение по умолчанию")
        else_layout.addWidget(self.case_else_edit)
        case_builder_layout.addWidget(else_group)

        # Кнопка построения CASE
        self.case_build_btn = QPushButton("Построить CASE выражение")
        self.case_build_btn.clicked.connect(self.build_case_expression)
        case_builder_layout.addWidget(self.case_build_btn)

        vbox.addWidget(case_builder_group)

        # Предпросмотр
        preview_group = QGroupBox("Предпросмотр CASE выражения")
        preview_layout = QVBoxLayout(preview_group)
        self.case_preview_edit = QTextEdit()
        self.case_preview_edit.setMaximumHeight(80)
        self.case_preview_edit.setReadOnly(True)
        preview_layout.addWidget(self.case_preview_edit)
        vbox.addWidget(preview_group)

        return tab

    def update_case_preview(self):
        """Обновляет предпросмотр CASE выражения"""
        condition = ''
        when = self.when.text().strip()
        then = self.then.text().strip()
        if when and then:
            # Форматируем THEN значение
            formatted_then = self._format_case_value(then)
            condition = f"WHEN {when} THEN {formatted_then}"

        if not condition:
            self.case_preview_edit.setPlainText("")
            return

        case_expr = "CASE\n  " + "\n  " + condition

        else_text = self.case_else_edit.text().strip()
        if else_text:
            formatted_else = self._format_case_value(else_text)
            case_expr += f"\n  ELSE {formatted_else}"

        case_expr += "\nEND"

        alias = self.case_alias_edit.text().strip()
        if alias:
            case_expr += f" AS {alias}"

        self.case_preview_edit.setPlainText(case_expr)

    def _format_case_value(self, value):
        """Форматирует значение для CASE выражения"""
        # Если это число
        if value.replace('.', '').isdigit():
            return value
        # Если это SQL выражение (содержит пробелы или скобки)
        elif any(char in value for char in [' ', '(', ')', '>', '<', '=', '!']):
            return value
        # Если это булево значение
        elif value.upper() in ['TRUE', 'FALSE']:
            return value.upper()
        # Иначе - строка, заключаем в кавычки
        else:
            return f"'{value}'"

    def build_case_expression(self):
        """Строит CASE выражение и показывает в предпросмотре"""
        self.update_case_preview()

    def _format_value(self, value):
        """Форматирует значение для SQL"""
        # Если это число
        if value.replace('.', '').isdigit():
            return value
        # Если это колонка (содержит только буквы, цифры и подчеркивания)
        elif self._is_column_reference(value):
            return value
        # Иначе - строка, заключаем в кавычки
        else:
            return f"'{value}'"

    def _is_column_reference(self, value):
        """Проверяет, является ли значение ссылкой на колонку"""
        # Простая проверка: если содержит только буквы, цифры и подчеркивания
        return all(c.isalnum() or c == '_' for c in value)

    def _add_to_null_functions_list(self, expr):
        """Добавляет выражение в список функций NULL"""
        current_text = self.null_functions_list.toPlainText()
        if current_text:
            current_text += ",\n" + expr
        else:
            current_text = expr
        self.null_functions_list.setPlainText(current_text)

    def clear_null_functions(self):
        """Очищает список функций NULL"""
        self.null_functions_list.clear()

    def update_adv_subquery_columns(self, table_name):
        """Обновляет список колонок для выбранной таблицы подзапроса"""
        self.adv_subquery_column_combo.clear()

        if not table_name:
            return

        parent = self.parent()
        if parent and hasattr(parent, 'get_table_columns'):
            columns = parent.get_table_columns(table_name)
            self.adv_subquery_column_combo.addItems(columns)
        else:
            sample_columns = ["aircraft_id", "flight_id", "passenger_id", "ticket_id", "crew_id"]
            self.adv_subquery_column_combo.addItems(sample_columns)

    def build_adv_subquery(self):
        """Строит подзапрос на основе выбранных параметров"""
        table = self.adv_subquery_table_combo.currentText()
        column = self.adv_subquery_column_combo.currentText()
        where = self.adv_subquery_where_edit.text().strip()

        if not table or not column:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу и колонку для подзапроса")
            return

        subquery = f"SELECT {column} FROM {table}"
        if where:
            subquery += f" WHERE {table}.{where}"

        """Добавляет условие с подзапросом в список"""
        column = self.adv_column_combo.currentText()
        operator = self.adv_operator_combo.currentText()

        if not subquery:
            QMessageBox.warning(self, "Ошибка", "Создайте или введите подзапрос")
            return

        if operator in ["EXISTS", "NOT EXISTS"]:
            condition = f"{operator} ({subquery})"
        else:
            condition = f"{column} {operator} ({subquery})"

        current_text = self.adv_conditions_list.toPlainText()
        if current_text:
            current_text += "\nAND " + condition
        else:
            current_text = condition

        self.adv_conditions_list.setPlainText(current_text)

    def add_function(self):
        function = self.functions_combo.currentText()
        column1 = self.function_column_combo.currentText()
        alias = self.function_alias_edit.text().strip()
        if not alias:
            return
        if self.functions_combo.currentIndex() in [0, 1, 2]:
            function_text = f"{function} ({column1}) AS {alias}"
        if self.functions_combo.currentIndex() in [3, 4, 5]:
            string = self.function_string_edit.text()
            function_text = f"{function} (\"{string}\", {column1}) AS {alias}"
        if self.functions_combo.currentIndex() in [6]:
            column2 = self.function_column2_combo.currentText()
            function_text = f"{function} ({column1}, {column2}) AS {alias}"
        current_text = self.added_functions_list.toPlainText()
        current_text = (current_text + "\n" if current_text else "") + function_text
        self.added_functions_list.setPlainText(current_text)
        self.function_alias_edit.clear()

    def add_where_condition(self):
        column = self.where_column_combo.currentText()
        operator = self.where_operator_combo.currentText()
        value = self.where_value_edit.text().strip()
        if not value:
            return
        condition = f"{column} {operator} {value}"
        current_text = self.where_conditions_list.toPlainText()
        current_text = (current_text + "\nAND " if current_text else "WHERE ") + condition
        self.where_conditions_list.setPlainText(current_text)
        self.where_value_edit.clear()

    def add_group_column(self):
        column = self.group_column_combo.currentText()
        current_text = self.group_columns_list.toPlainText()
        current_text = (current_text + ", " if current_text else "GROUP BY ") + column
        self.group_columns_list.setPlainText(current_text)

    def add_having_condition(self):
        function = self.having_function_combo.currentText()
        column = self.having_column_combo.currentText()
        operator = self.having_operator_combo.currentText()
        value = self.having_value_edit.text().strip()
        if not value:
            return
        condition = f"{function}({column}) {operator} {value}"
        current_text = self.having_conditions_list.toPlainText()
        current_text = (current_text + "\nAND " if current_text else "HAVING ") + condition
        self.having_conditions_list.setPlainText(current_text)
        self.having_value_edit.clear()

    def add_order_column(self):
        column = self.order_column_combo.currentText()
        direction = self.order_direction_combo.currentText()
        order_text = f"{column} {direction}"
        current_text = self.order_columns_list.toPlainText()
        current_text = (current_text + ", " if current_text else "ORDER BY ") + order_text
        self.order_columns_list.setPlainText(current_text)

    def add_join(self):
        join_type = self.join_type_combo.currentText()
        join_table = self.join_table_combo.currentText()
        main_column = self.join_main_column_combo.currentText()
        foreign_column = self.join_foreign_column_combo.currentText()

        if not join_table or not main_column or not foreign_column:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля для JOIN")
            return

        join_text = f"{join_type} {join_table} ON {self.current_table}.{main_column} = {join_table}.{foreign_column}"

        current_text = self.joins_list.toPlainText()
        if current_text:
            current_text += "\n" + join_text
        else:
            current_text = join_text

        self.joins_list.setPlainText(current_text)

    def clear_joins(self):
        self.joins_list.clear()

    def apply_filter(self):
        self.accept()

    def reset_filters(self):
        for cb in self.column_checkboxes.values():
            cb.setChecked(True)
        self.added_functions_list.clear()
        self.where_conditions_list.clear()
        self.group_columns_list.clear()
        self.having_conditions_list.clear()
        self.order_columns_list.clear()
        if hasattr(self, "joins_list"):
            self.joins_list.clear()
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
