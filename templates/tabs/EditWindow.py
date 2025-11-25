import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox,
    QPushButton, QFormLayout, QTableView,
    QComboBox, QLineEdit, QDialog,
    QLabel, QTabWidget, QTextEdit,
    QGroupBox, QHBoxLayout, QDialogButtonBox,
    QMessageBox, QScrollArea
)

from PySide6.QtCore import (Qt)
from sqlalchemy import text

from styles import apply_compact_table_view

from sqlalchemy.exc import SQLAlchemyError

from templates.tabs.CustomFilesDialog import CustomTypesDialog


class ValidationError(Exception):
    """Кастомное исключение для ошибок валидации"""

    def __init__(self, message, field_name=None):
        super().__init__(message)
        self.field_name = field_name
        self.message = message


class EditWindow(QWidget):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.tables = tables
        self.table = table

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

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

        layout.addWidget(self.edit_buttons)
        layout.addWidget(self.structure_table)

        layout.addStretch()

        self.connect_buttons()
        self.load_table_structure()

    def connect_buttons(self):
        self.add_column_btn.clicked.connect(self.show_add_column_dialog)
        self.delete_column_btn.clicked.connect(self.delete_selected_column)
        self.edit_column_btn.clicked.connect(self.show_edit_column_dialog)

        self.custom_types_btn = QPushButton("Пользовательские типы")
        self.custom_types_btn.clicked.connect(self.open_custom_types_dialog)
        self.layout().addWidget(self.custom_types_btn)

    def open_custom_types_dialog(self):
        """Открывает диалог управления пользовательскими типами"""
        dialog = CustomTypesDialog(self.engine, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.close()

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
        sql = """
              SELECT typname, typtype
              FROM pg_type \
              """
        types = self.execute_sql(sql)
        types = [i[0] for i in types if i[1] == 'b']
        type_combo.addItems(types)
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

        if self.tables:
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
        sql = """
              SELECT typname, typtype
              FROM pg_type \
              """
        types = self.execute_sql(sql)
        types = [i[0] for i in types if i[1] == 'b']
        type_combo.addItems(types)
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

    def add_column_to_structure(self, name, data_type, not_null, default, unique, foreign_key, foreign_table,
                                check_constraint, check_condition):
        try:
            # Валидация перед выполнением
            self._validate_column_addition(name, data_type, not_null, default)

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
            self.refresh_table_structure()

            # QMessageBox.information(self, "Успех", f"Столбец '{name}' успешно добавлен")

        except ValidationError as e:
            QMessageBox.warning(self, "Ошибка валидации", str(e))
        except SQLAlchemyError as e:
            error_message = self._format_sql_error(str(e))
            QMessageBox.critical(self, "Ошибка базы данных", error_message)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить столбец: {str(e)}")

    def _validate_column_addition(self, name, data_type, not_null, default):
        """Валидация добавления столбца"""
        if not name:
            raise ValidationError("Введите название столбца")

        if not name.replace('_', '').isalnum():
            raise ValidationError("Название столбца может содержать только буквы, цифры и символ подчеркивания")

        if not data_type:
            raise ValidationError("Выберите тип данных для столбца")

        if not_null and not default:
            raise ValidationError("Для столбца с ограничением NOT NULL необходимо указать значение по умолчанию")

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

        yes_button = msg_box.addButton("Да", QMessageBox.ButtonRole.YesRole)
        no_button = msg_box.addButton("Нет", QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(no_button)

        sql = f"ALTER TABLE {self.table} DROP COLUMN {column_name}"

        try:
            self.execute_sql(sql)

            msg_box.exec()

            if msg_box.clickedButton() == yes_button:
                QMessageBox.information(self, "Успех", f"Столбец '{column_name}' успешно удален")
                self.refresh_table_structure()

        except SQLAlchemyError as e:
            error_message = self._format_sql_error(str(e))
            if "cannot drop" in error_message.lower() and "constraint" in error_message.lower():
                QMessageBox.critical(self, "Ошибка удаления",
                                     f"Нельзя удалить столбец '{column_name}', так как на него ссылаются другие таблицы.\n"
                                     f"Сначала удалите связанные ограничения.")
            else:
                QMessageBox.critical(self, "Ошибка удаления", error_message)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить столбец: {str(e)}")

    def _format_sql_error(self, error_str: str) -> str:
        """Форматирует SQL ошибку в понятный для пользователя вид"""
        # Аналогично методу в ReadWindow
        if "null value in column" in error_str:
            match = re.search(r'column "([^"]+)"', error_str)
            if match:
                column = match.group(1)
                return f"Ошибка: Поле '{column}' не может быть пустым."

        elif "violates check constraint" in error_str:
            return "Ошибка проверки данных: нарушено ограничение CHECK. Проверьте введенные значения."

        elif "duplicate key value violates unique constraint" in error_str:
            return "Ошибка уникальности: такое значение уже существует в таблице."

        return f"Ошибка базы данных:\n{error_str}"

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

    def execute_sql(self, sql_query):
        try:
            with self.engine.begin() as conn:
                result = conn.execute(text(sql_query))
                return result
        except Exception as e:
            QMessageBox.critical(self, "Ошибка SQL", f"Ошибка выполнения запроса: {str(e)}")
            return None
