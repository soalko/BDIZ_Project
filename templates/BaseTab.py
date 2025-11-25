from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox,
    QPushButton, QFormLayout, QTableView,
    QComboBox, QLineEdit, QDialog,
    QLabel, QTabWidget, QTextEdit,
    QGroupBox, QHBoxLayout, QDialogButtonBox,
    QMessageBox, QScrollArea
)

from PySide6.QtCore import (Qt)
from typing import List
from sqlalchemy import text

from templates.modes import AppMode
from styles import apply_compact_table_view

from sqlalchemy.exc import SQLAlchemyError


class BaseTab(QWidget):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(parent)

        self.engine = engine
        self.tables = tables
        self.current_mode = AppMode.READ
        self.table = table

        self.tool_panel = QWidget()
        self.tool_layout = QHBoxLayout(self.tool_panel)
        self.tool_layout.setContentsMargins(0, 0, 0, 0)

        # Элементы для режима чтения
        self.read_widgets = QWidget()
        self.read_layout = QVBoxLayout(self.read_widgets)

        # кнопка фильтрации для режима чтения
        self.filter_button = QPushButton("Фильтрация")
        self.filter_button.clicked.connect(self.open_filter_dialog)
        self.read_layout.addWidget(self.filter_button)

        self.read_table = QTableView()
        self.read_layout.addWidget(self.read_table)

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
        self.edit_buttons_layout.addWidget(self.add_column_btn)
        self.edit_buttons_layout.addWidget(self.delete_column_btn)
        self.edit_buttons_layout.addWidget(self.edit_column_btn)

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

        # Общее

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.tool_panel)
        self.connect_buttons()

        self.added_functions_list = ""

    def connect_buttons(self):
        # чтение

        self.custom_types_btn = QPushButton("Пользовательские типы")
        self.custom_types_btn.clicked.connect(self.open_custom_types_dialog)

        #self.case_expression_btn = QPushButton("CASE выражение")
        #self.case_expression_btn.clicked.connect(self.open_case_expression_dialog)

        # Добавить кнопки в tool_layout
        self.edit_layout.addWidget(self.custom_types_btn)
        #self.read_layout.addWidget(self.case_expression_btn)

        # редактирование
        self.add_column_btn.clicked.connect(self.show_add_column_dialog)
        self.delete_column_btn.clicked.connect(self.delete_selected_column)
        self.edit_column_btn.clicked.connect(self.show_edit_column_dialog)

        # добавление

    def update_model(self):
        from sqlalchemy import Table, MetaData

        # Создаем объект метаданных
        metadata = MetaData()

        # Автоматически загружаем структуру таблицы из базы данных
        self.tables[self.table] = Table(
            self.table,
            metadata,
            autoload_with=self.engine
        )

    def update_tables(self):
        pass

    def open_custom_types_dialog(self):
        """Открывает диалог управления пользовательскими типами"""
        dialog = CustomTypesDialog(self.engine, self)
        dialog.exec()

    def open_case_expression_dialog(self):
        """Открывает конструктор CASE выражений"""
        columns = self.get_table_columns(self.table)
        dialog = CaseExpressionDialog(self, columns)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            case_expr = dialog.get_case_expression()
            if case_expr:
                # Добавляем CASE выражение в список SELECT
                current_text = self.added_functions_list.toPlainText()
                if current_text:
                    current_text += ",\n" + case_expr
                else:
                    current_text = case_expr
                self.added_functions_list.setPlainText(current_text)

    def load_table_structure(self):
        try:
            from PySide6.QtGui import QStandardItemModel, QStandardItem

            # Создаем модель для отображения структуры
            structure_model = QStandardItemModel()
            structure_model.setHorizontalHeaderLabels(["Название столбца", "Тип данных", "Ограничения"])

            table = self.tables[self.table]

            for i, column in enumerate(table.columns):
                row_items = [
                    QStandardItem(column.name),
                    QStandardItem(str(column.type)),
                    QStandardItem(self._get_column_constraints(column))
                ]

                # Сохраняем имя столбца в данных для последующего использования
                for item in row_items:
                    item.setData(column.name, Qt.UserRole)

                structure_model.appendRow(row_items)

            self.structure_table.setModel(structure_model)
            self.structure_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            apply_compact_table_view(self.structure_table)

            self.delete_column_btn.setEnabled(False)
            self.edit_column_btn.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка загрузки структуры", str(e))

    def _get_column_constraints(self, column):
        constraints = []
        if not column.nullable:
            constraints.append("NOT NULL")
        if column.primary_key:
            constraints.append("PRIMARY KEY")
        if column.unique:
            constraints.append("UNIQUE")

        return ", ".join(constraints) if constraints else "нет"

    def refresh_table_structure(self):
        """Обновляет метаданные таблицы и перезагружает структуру"""
        try:
            from sqlalchemy import Table, MetaData

            metadata = MetaData()
            refreshed_table = Table(
                self.table,
                metadata,
                autoload_with=self.engine
            )

            self.tables[self.table] = refreshed_table

            self.load_table_structure()

            if hasattr(self, 'model') and self.model:
                self.model.refresh()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка обновления", f"Не удалось обновить структуру таблицы: {str(e)}")

    def on_structure_column_selected(self, index):
        if index.isValid():
            self.delete_column_btn.setEnabled(True)
            self.edit_column_btn.setEnabled(True)
        else:
            self.delete_column_btn.setEnabled(False)
            self.edit_column_btn.setEnabled(False)

    def show_add_column_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить столбец")
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Название столбца:"))
        name_edit = QLineEdit()
        layout.addWidget(name_edit)

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

        layout.addWidget(QLabel("Значение по умолчанию:"))
        default_edit = QLineEdit()
        layout.addWidget(default_edit)

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

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.add_column_to_structure(
                name_edit.text().strip(),
                type_combo.currentText(),
                check_not_null.isChecked(),
                default_edit.text(),
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

        layout.addWidget(check_not_null)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.edit_column(
                column_name,
                name_edit.text().strip(),
                type_combo.currentText(),
                check_not_null.isChecked()
            )

    def add_column_to_structure(self, name, data_type, not_null, default, unique, foreign_key, foreign_table, check_constraint,
                                check_condition):
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название столбца")
            return
        if not_null and not default:
            QMessageBox.warning(self, "Ошибка", "Введите значение по умолчанию")
            return



        try:
            sql_parts = [f'ALTER TABLE {self.table} ADD COLUMN {name} {data_type.upper()}']

            # Добавляем ограничения
            if not_null:
                sql_parts.append(f"NOT NULL DEFAULT {default}")
            if unique:
                sql_parts.append("UNIQUE")
            if foreign_key and foreign_table:
                sql_parts.append(f"REFERENCES {foreign_table}({name})")
            if check_constraint and check_condition:
                sql_parts.append(f"CHECK ({name} {check_condition})")

            sql = ' '.join(sql_parts)

            self.execute_sql(sql)

            QMessageBox.information(self, "Успех",
                                    f"Столбец '{name}' добавлен\n"
                                    )
            self.refresh_table_structure()
        except SQLAlchemyError as e:
            error = str(e.__dict__['orig'])
            print(error)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить столбец: {str(e)}")

    def delete_selected_column(self):
        index = self.structure_table.currentIndex()
        if not index.isValid():
            QMessageBox.warning(self, "Ошибка", "Выберите столбец для удаления")
            return

        model = self.structure_table.model()
        row = index.row()
        column_name = model.data(model.index(row, 0))

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Удаление столбца")
        msg_box.setText(f"Вы уверены, что хотите удалить столбец '{column_name}'?")
        msg_box.setIcon(QMessageBox.Icon.Question)

        # Создаем кнопки с русским текстом
        yes_button = msg_box.addButton("Да", QMessageBox.ButtonRole.YesRole)
        no_button = msg_box.addButton("Нет", QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(no_button)

        sql = f"ALTER TABLE {self.table} DROP COLUMN {column_name}"

        try:
            self.execute_sql(sql)

            msg_box.exec()

            if msg_box.clickedButton() == yes_button:
                QMessageBox.information(self, "Удаление", f"Столбец '{column_name}' удален")
                self.refresh_table_structure()
        except Exception as e:
            QMessageBox.information(self, "Удаление", f"Столбец '{column_name}' не удален. Ошибка\n {e}")

    def edit_column(self, oldname, name, data_type, not_null):
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название столбца")
            return

        try:
            sql = f"ALTER TABLE {self.table} "
            sql_parts = []
            if oldname != name:
                self.execute_sql(f"ALTER TABLE {self.table} RENAME COLUMN {oldname} TO {name}")
            sql_parts.append(f"ALTER COLUMN {name} TYPE {data_type}")
            if not_null:
                sql_parts.append(f"ALTER COLUMN {name} SET NOT NULL")
            else:
                sql_parts.append(f"ALTER COLUMN {name} DROP NOT NULL")
            sql += ', '.join(sql_parts)

            self.execute_sql(sql)

            QMessageBox.information(self, "Успех",
                                    f"Столбец '{name}' изменен\n"
                                    )

            self.refresh_table_structure()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось изменить столбец: {str(e)}")

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
        """Выполняет SQL запрос и отображает результаты"""
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
            QMessageBox.critical(self, "Ошибка запроса\n",
                                 f"Некорректный запрос! \n\n"
                                 f"Запрос:\n{sql_query}\n\nЛог ошибки: {str(e)}")

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

    # Метод произвольного SQL запроса в BaseTab: (на всякий случай, может не пригодиться)
    def execute_sql(self, sql_query):
        try:
            with self.engine.begin() as conn:
                result = conn.execute(text(sql_query))
                return result
        except Exception as e:
            QMessageBox.critical(self, "Ошибка SQL", f"Ошибка выполнения запроса: {str(e)}")
            return None


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


class CustomTypesManager:
    def __init__(self, engine):
        self.engine = engine

    def create_enum_type(self, type_name, values):
        """Создает ENUM тип"""
        values_str = ", ".join(f"'{v}'" for v in values)
        sql = f"CREATE TYPE {type_name} AS ENUM ({values_str})"
        self.execute_sql(sql)

    def create_composite_type(self, type_name, fields):
        """Создает составной тип"""
        fields_str = ", ".join(f"{name} {data_type}" for name, data_type in fields.items())
        sql = f"CREATE TYPE {type_name} AS ({fields_str})"
        self.execute_sql(sql)

    def get_custom_types(self):
        """Получает список пользовательских типов"""
        sql = """
        SELECT typname, typtype 
        FROM pg_type 
        WHERE typtype IN ('e', 'c') AND typname NOT LIKE 'pg_%'
        """
        return self.execute_sql(sql)

    def drop_type(self, type_name):
        """Удаляет пользовательский тип"""
        sql = f"DROP TYPE {type_name}"
        self.execute_sql(sql)

    def execute_sql(self, sql):
        try:
            with self.engine.begin() as conn:
                return conn.execute(text(sql))
        except Exception as e:
            QMessageBox.critical(None, "Ошибка SQL", f"Ошибка выполнения запроса: {str(e)}")
            return None


class CustomTypesDialog(QDialog):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.types_manager = CustomTypesManager(engine)
        self.setWindowTitle("Управление пользовательскими типами")
        self.setup_ui()
        self.load_types()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Создание нового типа
        create_group = QGroupBox("Создать новый тип")
        create_layout = QVBoxLayout(create_group)

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Тип:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["ENUM", "COMPOSITE"])
        type_layout.addWidget(self.type_combo)

        type_layout.addWidget(QLabel("Имя типа:"))
        self.type_name_edit = QLineEdit()
        type_layout.addWidget(self.type_name_edit)
        create_layout.addLayout(type_layout)

        # Поля для ENUM
        self.enum_widget = QWidget()
        enum_layout = QVBoxLayout(self.enum_widget)
        enum_layout.addWidget(QLabel("Значения ENUM (каждое с новой строки):"))
        self.enum_values_edit = QTextEdit()
        self.enum_values_edit.setMaximumHeight(100)
        enum_layout.addWidget(self.enum_values_edit)
        create_layout.addWidget(self.enum_widget)

        # Поля для COMPOSITE
        self.composite_widget = QWidget()
        composite_layout = QVBoxLayout(self.composite_widget)
        composite_layout.addWidget(QLabel("Поля составного типа (каждое поле с новой строки в формате 'имя тип'):"))
        self.composite_fields_edit = QTextEdit()
        self.composite_fields_edit.setMaximumHeight(100)
        composite_layout.addWidget(self.composite_fields_edit)
        create_layout.addWidget(self.composite_widget)
        self.composite_widget.setVisible(False)

        self.create_button = QPushButton("Создать тип")
        self.create_button.clicked.connect(self.create_type)
        create_layout.addWidget(self.create_button)

        self.type_combo.currentTextChanged.connect(self.on_type_changed)

        # Список существующих типов
        list_group = QGroupBox("Существующие типы")
        list_layout = QVBoxLayout(list_group)

        self.types_table = QTableView()
        list_layout.addWidget(self.types_table)

        self.delete_button = QPushButton("Удалить выбранный тип")
        self.delete_button.clicked.connect(self.delete_type)
        list_layout.addWidget(self.delete_button)

        layout.addWidget(create_group)
        layout.addWidget(list_group)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def on_type_changed(self, type_name):
        self.enum_widget.setVisible(type_name == "ENUM")
        self.composite_widget.setVisible(type_name == "COMPOSITE")

    def create_type(self):
        type_name = self.type_name_edit.text().strip()
        if not type_name:
            QMessageBox.warning(self, "Ошибка", "Введите имя типа")
            return

        try:
            if self.type_combo.currentText() == "ENUM":
                values = [v.strip() for v in self.enum_values_edit.toPlainText().split('\n') if v.strip()]
                if not values:
                    QMessageBox.warning(self, "Ошибка", "Введите значения ENUM")
                    return
                self.types_manager.create_enum_type(type_name, values)
            else:
                fields_text = self.composite_fields_edit.toPlainText().strip()
                if not fields_text:
                    QMessageBox.warning(self, "Ошибка", "Введите поля составного типа")
                    return

                fields = {}
                for line in fields_text.split('\n'):
                    if line.strip():
                        name, data_type = line.strip().split()
                        fields[name] = data_type

                self.types_manager.create_composite_type(type_name, fields)

            QMessageBox.information(self, "Успех", f"Тип {type_name} создан")
            self.load_types()
            self.type_name_edit.clear()
            self.enum_values_edit.clear()
            self.composite_fields_edit.clear()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать тип: {str(e)}")

    def load_types(self):
        result = self.types_manager.get_custom_types()
        if result:
            from PySide6.QtGui import QStandardItemModel, QStandardItem
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["Имя типа", "Тип"])

            for row in result:
                type_name = row[0]
                type_type = "ENUM" if row[1] == 'e' else "COMPOSITE"
                model.appendRow([QStandardItem(type_name), QStandardItem(type_type)])

            self.types_table.setModel(model)

    def delete_type(self):
        index = self.types_table.currentIndex()
        if not index.isValid():
            QMessageBox.warning(self, "Ошибка", "Выберите тип для удаления")
            return

        model = self.types_table.model()
        type_name = model.data(model.index(index.row(), 0))

        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Вы уверены, что хотите удалить тип {type_name}?")
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.types_manager.drop_type(type_name)
                QMessageBox.information(self, "Успех", f"Тип {type_name} удален")
                self.load_types()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить тип: {str(e)}")


class CaseExpressionDialog(QDialog):
    def __init__(self, parent=None, table_columns=None):
        super().__init__(parent)
        self.table_columns = table_columns or []
        self.setWindowTitle("Конструктор CASE выражения")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Псевдоним для результата:"))
        self.alias_edit = QLineEdit()
        self.alias_edit.setPlaceholderText("result_column")
        layout.addWidget(self.alias_edit)

        # Условия WHEN
        self.conditions_widget = QWidget()
        conditions_layout = QVBoxLayout(self.conditions_widget)
        conditions_layout.addWidget(QLabel("Условия WHEN-THEN:"))

        self.conditions_scroll = QScrollArea()
        self.conditions_content = QWidget()
        self.conditions_layout = QVBoxLayout(self.conditions_content)
        self.conditions_scroll.setWidget(self.conditions_content)
        self.conditions_scroll.setWidgetResizable(True)
        self.conditions_scroll.setMaximumHeight(200)
        conditions_layout.addWidget(self.conditions_scroll)

        self.add_condition_button = QPushButton("Добавить условие")
        self.add_condition_button.clicked.connect(self.add_condition)
        conditions_layout.addWidget(self.add_condition_button)

        layout.addWidget(self.conditions_widget)

        # ELSE
        else_group = QGroupBox("ELSE (необязательно)")
        else_layout = QVBoxLayout(else_group)
        self.else_edit = QLineEdit()
        self.else_edit.setPlaceholderText("Значение по умолчанию")
        else_layout.addWidget(self.else_edit)
        layout.addWidget(else_group)

        # Предпросмотр
        preview_group = QGroupBox("Предпросмотр")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_edit = QTextEdit()
        self.preview_edit.setMaximumHeight(100)
        self.preview_edit.setReadOnly(True)
        preview_layout.addWidget(self.preview_edit)
        layout.addWidget(preview_group)

        self.add_condition()  # Добавить первое условие

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Обновление предпросмотра при изменениях
        self.alias_edit.textChanged.connect(self.update_preview)
        self.else_edit.textChanged.connect(self.update_preview)

    def add_condition(self):
        condition_widget = QWidget()
        condition_layout = QHBoxLayout(condition_widget)

        when_edit = QLineEdit()
        when_edit.setPlaceholderText("WHEN условие")
        when_edit.textChanged.connect(self.update_preview)

        then_edit = QLineEdit()
        then_edit.setPlaceholderText("THEN значение")
        then_edit.textChanged.connect(self.update_preview)

        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(30, 30)
        remove_btn.clicked.connect(lambda: self.remove_condition(condition_widget))

        condition_layout.addWidget(QLabel("WHEN"))
        condition_layout.addWidget(when_edit)
        condition_layout.addWidget(QLabel("THEN"))
        condition_layout.addWidget(then_edit)
        condition_layout.addWidget(remove_btn)

        # Сохраняем ссылки на редактируемые поля
        condition_widget.when_edit = when_edit
        condition_widget.then_edit = then_edit

        self.conditions_layout.addWidget(condition_widget)

    def remove_condition(self, widget):
        self.conditions_layout.removeWidget(widget)
        widget.deleteLater()
        self.update_preview()

    def update_preview(self):
        conditions = []
        for i in range(self.conditions_layout.count()):
            widget = self.conditions_layout.itemAt(i).widget()
            if widget and hasattr(widget, 'when_edit') and hasattr(widget, 'then_edit'):
                when = widget.when_edit.text().strip()
                then = widget.then_edit.text().strip()
                if when and then:
                    conditions.append(f"WHEN {when} THEN {then}")

        if not conditions:
            self.preview_edit.setPlainText("")
            return

        case_expr = "CASE\n  " + "\n  ".join(conditions)

        else_text = self.else_edit.text().strip()
        if else_text:
            case_expr += f"\n  ELSE {else_text}"

        case_expr += "\nEND"

        alias = self.alias_edit.text().strip()
        if alias:
            case_expr += f" AS {alias}"

        self.preview_edit.setPlainText(case_expr)

    def get_case_expression(self):
        return self.preview_edit.toPlainText()