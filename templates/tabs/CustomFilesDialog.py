from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox,
    QPushButton, QFormLayout, QTableView,
    QComboBox, QLineEdit, QDialog,
    QLabel, QTabWidget, QTextEdit,
    QGroupBox, QHBoxLayout, QDialogButtonBox,
    QMessageBox, QScrollArea
)

from sqlalchemy import text


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
              WHERE typtype IN ('e', 'c')
                AND typname NOT LIKE 'pg_%' \
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
