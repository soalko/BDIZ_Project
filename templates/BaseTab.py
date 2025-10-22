from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox,
    QPushButton, QFormLayout, QTableView,
    QComboBox, QLineEdit, QDialog,
    QLabel, QTabWidget, QTextEdit,
    QGroupBox, QHBoxLayout, QDialogButtonBox,
    QMessageBox, QScrollArea
)

from PySide6.QtCore import (Qt)

from templates.modes import AppMode
from styles import apply_compact_table_view


class BaseTab(QWidget):
    def __init__(self, engine, tables, parent=None):
        super().__init__(parent)

        self.engine = engine
        self.tables = tables
        self.current_mode = AppMode.READ

        # Панель инструментов для всех режимов
        self.tool_panel = QWidget()
        self.tool_layout = QHBoxLayout(self.tool_panel)
        self.tool_layout.setContentsMargins(0, 0, 0, 0)

        # Элементы для режима чтения
        self.read_widgets = QWidget()
        self.read_layout = QHBoxLayout(self.read_widgets)

        self.sort_combo = QComboBox()
        self.register_combo = QComboBox()
        self.join_btn = QPushButton("JOIN")
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Фильтр...")

        # кнопка фильтрации для режима чтения
        self.filter_button = QPushButton("Фильтрация")
        self.filter_button.clicked.connect(self.open_filter_dialog)
        self.read_layout.addWidget(self.filter_button)

        self.read_layout.setContentsMargins(0, 0, 0, 0)
        self.read_layout.addStretch()

        # Элементы для режима редактирования

        self.edit_widgets = QWidget()
        self.edit_layout = QVBoxLayout(self.edit_widgets)

        self.edit_buttons = QWidget()
        self.edit_buttons_layout = QHBoxLayout(self.edit_buttons)
        self.add_column_btn = QPushButton("Добавить столбец")
        self.delete_column_btn = QPushButton("Удалить столбец")
        self.edit_column_btn = QPushButton("Изменить столбец")
        self.save_structure_btn = QPushButton("Сохранить структуру")
        self.cancel_structure_btn = QPushButton("Отменить изменения")
        self.edit_buttons_layout.addWidget(self.add_column_btn)
        self.edit_buttons_layout.addWidget(self.delete_column_btn)
        self.edit_buttons_layout.addWidget(self.edit_column_btn)
        self.edit_buttons_layout.addWidget(self.save_structure_btn)
        self.edit_buttons_layout.addWidget(self.cancel_structure_btn)
        self.connect_buttons()

        self.structure_table = QTableView()
        self.structure_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.structure_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.structure_table.clicked.connect(self.on_structure_column_selected)
        apply_compact_table_view(self.structure_table)

        self.edit_layout.addWidget(self.edit_buttons)
        self.edit_layout.addWidget(self.structure_table)

        self.edit_layout.setContentsMargins(0, 0, 0, 0)
        self.edit_layout.addStretch()

        # Элементы для режима добавления
        self.add_widgets = QWidget()
        self.add_layout = QVBoxLayout(self.add_widgets)

        self.add_buttons = QWidget()
        self.add_buttons_layout = QHBoxLayout(self.add_buttons)
        self.add_record_btn = QPushButton("Добавить запись")
        self.clear_form_btn = QPushButton("Очистить форму")
        self.delete_record_btn = QPushButton("Удалить запись")
        self.add_buttons_layout.addWidget(self.add_record_btn)
        self.add_buttons_layout.addWidget(self.clear_form_btn)
        self.add_buttons_layout.addWidget(self.delete_record_btn)

        self.add_form = QWidget()
        self.add_form_layout = QFormLayout(self.add_form)
        self.add_form_rows()

        self.add_table = QTableView()

        self.add_layout.addWidget(self.add_buttons)
        self.add_layout.addWidget(self.add_form)
        self.add_layout.addWidget(self.add_table)

        self.add_layout.setContentsMargins(0, 0, 0, 0)
        self.add_layout.addStretch()

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.tool_panel)

    def connect_buttons(self):
        self.add_column_btn.clicked.connect(self.show_add_column_dialog)
        self.delete_column_btn.clicked.connect(self.delete_selected_column)
        self.edit_column_btn.clicked.connect(self.show_edit_column_dialog)
        self.save_structure_btn.clicked.connect(self.save_structure_changes)
        self.cancel_structure_btn.clicked.connect(self.cancel_structure_changes)

    def load_table_structure(self):
        pass

    def _get_column_constraints(self, column):
        constraints = []
        if not column.nullable:
            constraints.append("NOT NULL")
        if column.primary_key:
            constraints.append("PRIMARY KEY")
        if column.unique:
            constraints.append("UNIQUE")
        # Можно добавить проверку других ограничений, если нужно

        return ", ".join(constraints) if constraints else "нет"

    def on_structure_column_selected(self, index):
        """Обработчик выбора столбца в структуре"""
        if index.isValid():
            self.delete_column_btn.setEnabled(True)
            self.edit_column_btn.setEnabled(True)
        else:
            self.delete_column_btn.setEnabled(False)
            self.edit_column_btn.setEnabled(False)

    def show_add_column_dialog(self):
        """Показывает диалог добавления столбца"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить столбец")
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Название столбца:"))
        name_edit = QLineEdit()
        layout.addWidget(name_edit)

        # Выбор типа данных
        layout.addWidget(QLabel("Тип данных:"))
        type_combo = QComboBox()
        type_combo.addItems([
            "integer", "char", "varchar", "text", "real",
            "decimal", "boolean", "date", "time", "timestamp", "interval"
        ])
        layout.addWidget(type_combo)

        # Чекбоксы для ограничений
        check_not_null = QCheckBox("NOT NULL")
        check_unique = QCheckBox("UNIQUE")
        check_foreign = QCheckBox("FOREIGN KEY")
        check_check = QCheckBox("CHECK")

        layout.addWidget(check_not_null)
        layout.addWidget(check_unique)
        layout.addWidget(check_foreign)
        layout.addWidget(check_check)

        # Поле для условия CHECK
        layout.addWidget(QLabel("Условие CHECK:"))
        check_condition_edit = QLineEdit()
        check_condition_edit.setEnabled(False)
        layout.addWidget(check_condition_edit)

        # Включаем поле CHECK только при выборе чекбокса
        check_check.toggled.connect(check_condition_edit.setEnabled)

        # Комбобокс для выбора таблицы при FOREIGN KEY
        foreign_table_combo = QComboBox()
        foreign_table_combo.setEnabled(False)
        layout.addWidget(QLabel("Связанная таблица:"))
        layout.addWidget(foreign_table_combo)

        # Заполняем список таблиц
        if self.add_table:
            for table_name in self.tables.keys():
                foreign_table_combo.addItem(table_name)

        # Включаем комбобокс только при выборе FOREIGN KEY
        check_foreign.toggled.connect(foreign_table_combo.setEnabled)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            self.add_column_to_structure(
                name_edit.text().strip(),
                type_combo.currentText(),
                check_not_null.isChecked(),
                check_unique.isChecked(),
                check_foreign.isChecked(),
                foreign_table_combo.currentText() if check_foreign.isChecked() else None,
                check_check.isChecked(),
                check_condition_edit.text() if check_check.isChecked() else None
            )

    def show_edit_column_dialog(self):
        """Показывает диалог редактирования столбца"""
        index = self.structure_table.currentIndex()
        if not index.isValid():
            QMessageBox.warning(self, "Ошибка", "Выберите столбец для редактирования")
            return

        # Получаем выбранную строку
        model = self.structure_table.model()
        row = index.row()
        column_name = model.data(model.index(row, 0))  # Название столбца из второго столбца

        dialog = QDialog(self)
        dialog.setWindowTitle("Редактировать столбец")
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Название столбца:"))
        name_edit = QLineEdit()
        name_edit.setText(column_name)
        layout.addWidget(name_edit)

        # Выбор типа данных
        layout.addWidget(QLabel("Тип данных:"))
        type_combo = QComboBox()
        type_combo.addItems([
            "integer", "char", "varchar", "text", "real",
            "decimal", "boolean", "date", "time", "timestamp", "interval"
        ])
        layout.addWidget(type_combo)

        check_not_null = QCheckBox("NOT NULL")
        check_unique = QCheckBox("UNIQUE")
        check_foreign = QCheckBox("FOREIGN KEY")
        check_check = QCheckBox("CHECK")

        layout.addWidget(check_not_null)
        layout.addWidget(check_unique)
        layout.addWidget(check_foreign)
        layout.addWidget(check_check)

        # Поле для условия CHECK
        layout.addWidget(QLabel("Условие CHECK:"))
        check_condition_edit = QLineEdit()
        check_condition_edit.setEnabled(False)
        layout.addWidget(check_condition_edit)

        check_check.toggled.connect(check_condition_edit.setEnabled)

        foreign_table_combo = QComboBox()
        foreign_table_combo.setEnabled(False)
        layout.addWidget(QLabel("Связанная таблица:"))
        layout.addWidget(foreign_table_combo)

        if self.add_table:
            for table_name in self.tables.keys():
                foreign_table_combo.addItem(table_name)

        check_foreign.toggled.connect(foreign_table_combo.setEnabled)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            QMessageBox.information(self, "Редактирование", f"Столбец '{name_edit.text()}' изменен")

    def add_column_to_structure(self, name, data_type, not_null, unique, foreign_key, foreign_table, check_constraint,
                                check_condition):
        """Добавляет столбец в структуру"""
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название столбца")
            return

        try:
            constraints = []
            if not_null:
                constraints.append("NOT NULL")
            if unique:
                constraints.append("UNIQUE")
            if foreign_key and foreign_table:
                constraints.append(f"FOREIGN KEY REFERENCES {foreign_table}")
            if check_constraint and check_condition:
                constraints.append(f"CHECK ({check_condition})")

            constraint_text = ", ".join(constraints)
            QMessageBox.information(self, "Успех",
                                    f"Столбец '{name}' добавлен\n"
                                    f"Тип: {data_type}\n"
                                    f"Ограничения: {constraint_text if constraint_text else 'нет'}")
            self.load_table_structure()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить столбец: {str(e)}")

    def delete_selected_column(self):
        """Удаляет выбранный столбец"""
        index = self.structure_table.currentIndex()
        if not index.isValid():
            QMessageBox.warning(self, "Ошибка", "Выберите столбец для удаления")
            return

        # Получаем выбранную строку
        model = self.structure_table.model()
        row = index.row()
        column_name = model.data(model.index(row, 1))  # Название столбца из второго столбца

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Удаление столбца")
        msg_box.setText(f"Вы уверены, что хотите удалить столбец '{column_name}'?")
        msg_box.setIcon(QMessageBox.Icon.Question)

        # Создаем кнопки с русским текстом
        yes_button = msg_box.addButton("Да", QMessageBox.ButtonRole.YesRole)
        no_button = msg_box.addButton("Нет", QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(no_button)

        msg_box.exec()

        if msg_box.clickedButton() == yes_button:
            QMessageBox.information(self, "Удаление", f"Столбец '{column_name}' удален")

    def save_structure_changes(self):
        """Сохраняет изменения структуры"""
        QMessageBox.information(self, "Сохранение", "Изменения структуры сохранены")

    def cancel_structure_changes(self):
        """Отменяет изменения структуры"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Отмена изменений")
        msg_box.setText("Вы уверены, что хотите отменить все изменения структуры?")
        msg_box.setIcon(QMessageBox.Icon.Question)

        # Создаем кнопки с русским текстом
        yes_button = msg_box.addButton("Да", QMessageBox.ButtonRole.YesRole)
        no_button = msg_box.addButton("Нет", QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(no_button)

        msg_box.exec()

        if msg_box.clickedButton() == yes_button:
            self.load_table_structure()
            QMessageBox.information(self, "Отмена", "Изменения структуры отменены")

    def add_form_rows(self):
        pass

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

    def open_filter_dialog(self):
        """Открывает диалог построения SQL и передает результат в обработчик"""

        dialog = SQLFilterDialog(self)
        if dialog.exec() == QDialog.Accepted:
            sql_query = dialog.added_functions_list.toPlainText()
            if sql_query:
                self.apply_read_filter(sql_query)

    def apply_read_filter(self, sql_query: str):
        pass


class SQLFilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
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

    def create_select_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)

        select_group = QGroupBox("SELECT - Выбор колонок и функций")
        select_layout = QVBoxLayout(select_group)

        self.columns_widget = QWidget()
        columns_layout = QVBoxLayout(self.columns_widget)
        self.column_checkboxes = {}
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
        self.function_column_combo.addItems(sample_columns)

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
        self.where_column_combo.addItems(["aircraft_id", "model", "year", "seats_amount", "baggage_capacity"])
        self.where_operator_combo = QComboBox()
        self.where_operator_combo.addItems(["=", "!=", ">", "<", ">=", "<=",
                                            "LIKE", "IN", "~", "~*", "!~", "!~*"])
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
        self.join_type_combo = QComboBox()
        self.join_type_combo.addItems(["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN"])
        self.join_table_combo = QComboBox()
        self.join_table_combo.addItems(["Самолеты", "Рейсы", "Пассажиры", "Билеты", "Экипажи", "Члены экипажа"])
        self.join_column1_combo = QComboBox()
        self.join_column1_combo.addItems(["РЕЙС1"])
        self.join_column2_combo = QComboBox()
        self.join_column2_combo.addItems(["РЕЙС2"])
        self.add_join_button = QPushButton("Добавить JOIN")
        self.add_join_button.clicked.connect(self.add_join)
        self.joins_list = QTextEdit()
        self.joins_list.setMaximumHeight(150)
        self.joins_list.setPlaceholderText("Добавленные JOIN")
        join_layout.addWidget(QLabel("Тип JOIN:"))
        join_layout.addWidget(self.join_type_combo)
        join_layout.addWidget(QLabel("Таблица:"))
        join_layout.addWidget(self.join_table_combo)
        join_layout.addWidget(QLabel("Колонка 1:"))
        join_layout.addWidget(self.join_column1_combo)
        join_layout.addWidget(QLabel("Колонка 2:"))
        join_layout.addWidget(self.join_column2_combo)
        join_layout.addWidget(self.add_join_button)
        join_layout.addWidget(QLabel("Текущие JOIN:"))
        join_layout.addWidget(self.joins_list)
        vbox.addWidget(join_group)
        return tab

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
        table = self.join_table_combo.currentText()
        col1 = self.join_column1_combo.currentText()
        col2 = self.join_column2_combo.currentText()
        join_text = f"aircraft {join_type} {table} ON {col1} = {col2}"
        current_text = self.joins_list.toPlainText()
        current_text = (current_text + "\n" if current_text else "") + join_text
        self.joins_list.setPlainText(current_text)

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