import re
from datetime import date
from typing import List, Dict, Any

from PySide6.QtCore import QDate, QTime, QDateTime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox,
    QPushButton, QFormLayout, QTableView,
    QComboBox, QLineEdit, QDialog,
    QLabel, QTabWidget, QTextEdit,
    QGroupBox, QHBoxLayout, QDialogButtonBox,
    QMessageBox, QScrollArea, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit
)

from sqlalchemy import text, inspect


class ValidationError(Exception):
    """Кастомное исключение для ошибок валидации"""

    def __init__(self, message, field_name=None):
        super().__init__(message)
        self.field_name = field_name
        self.message = message


class AddWindow(QWidget):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.tables = tables
        self.table = table
        self.input_widgets = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.add_buttons = QWidget()
        self.add_buttons_layout = QHBoxLayout(self.add_buttons)
        self.add_record_btn = QPushButton("Добавить запись")
        self.clear_form_btn = QPushButton("Очистить форму")
        self.delete_record_btn = QPushButton("Удалить запись")
        self.add_buttons_layout.addWidget(self.add_record_btn)
        self.add_buttons_layout.addWidget(self.clear_form_btn)
        self.add_buttons_layout.addWidget(self.delete_record_btn)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        # Создаем контейнер для формы внутри ScrollArea
        self.form_container = QWidget()
        self.add_form_layout = QFormLayout(self.form_container)

        # Автоматически создаем поля формы на основе структуры таблицы
        self.create_form_from_table_structure()

        # Устанавливаем контейнер формы в ScrollArea
        self.scroll_area.setWidget(self.form_container)

        self.add_table = QTableView()

        layout.addWidget(self.add_buttons)
        layout.addWidget(self.scroll_area)  # Добавляем ScrollArea вместо формы
        layout.addWidget(self.add_table)

        layout.addStretch()

        self.connect_buttons()

    def showEvent(self, event):
        """Вызывается при каждом показе окна"""
        super().showEvent(event)
        self.refresh_form_widgets()  # Обновляем виджеты при каждом открытии

    def refresh_form_widgets(self):
        """Обновляет данные в комбобоксах и других виджетах формы"""
        try:
            for column_name, widget in self.input_widgets.items():
                if isinstance(widget, QComboBox):
                    self._refresh_combobox_data(widget, column_name)
        except Exception as e:
            print(f"Ошибка при обновлении виджетов формы: {e}")

    def _refresh_combobox_data(self, combo: QComboBox, column_name: str):
        """Обновляет данные в комбобоксе для внешнего ключа"""
        try:
            # Получаем информацию о столбце
            columns_info = self.get_table_columns_info()
            column_info = next((col for col in columns_info if col['name'] == column_name), None)

            if column_info and column_info.get('foreign_key'):
                foreign_key_info = column_info['foreign_key']
                self._populate_foreign_key_combo(combo, foreign_key_info)
        except Exception as e:
            print(f"Ошибка при обновлении комбобокса {column_name}: {e}")


    def create_form_from_table_structure(self):
        """Автоматически создает поля формы на основе структуры таблицы"""
        # Очищаем существующую форму
        for i in reversed(range(self.add_form_layout.count())):
            item = self.add_form_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        self.input_widgets.clear()

        # Получаем информацию о столбцах
        columns_info = self.get_table_columns_info()

        for column_info in columns_info:
            column_name = column_info['name']
            column_type = column_info['type']
            is_primary_key = column_info['primary_key']
            is_nullable = column_info['nullable']

            # Пропускаем автоинкрементные первичные ключи
            if is_primary_key and self._is_auto_increment(column_type):
                continue

            # Создаем подпись с информацией о типе и ограничениях
            label_text = f"{column_name}"

            label = QLabel(label_text)

            # Создаем соответствующий виджет ввода
            input_widget = self._create_input_widget(column_type, column_info)
            self.input_widgets[column_name] = input_widget

            self.add_form_layout.addRow(label, input_widget)

    def _is_auto_increment(self, column_type: str) -> bool:
        """Проверяет, является ли тип данных автоинкрементным"""
        type_lower = column_type.lower()
        return any(inc_type in type_lower for inc_type in ['serial', 'identity', 'auto_increment'])

    def _format_type_name(self, column_type: str) -> str:
        """Форматирует название типа для отображения"""
        type_lower = column_type.lower()

        type_mapping = {
            'integer': 'целое число',
            'bigint': 'большое целое',
            'smallint': 'малое целое',
            'varchar': 'текст',
            'text': 'текст',
            'character varying': 'текст',
            'boolean': 'логический',
            'date': 'дата',
            'timestamp': 'дата/время',
            'time': 'время',
            'numeric': 'число',
            'decimal': 'десятичное',
            'real': 'вещественное',
            'double precision': 'двойная точность'
        }

        for sql_type, display_type in type_mapping.items():
            if sql_type in type_lower:
                return display_type

        return column_type

    def _create_input_widget(self, column_type: str, column_info: Dict[str, Any]):
        """Создает соответствующий виджет ввода для типа данных"""
        type_lower = column_type.lower()

        # Для внешних ключей создаем ComboBox
        if column_info.get('foreign_key'):
            return self._create_foreign_key_widget(column_info['foreign_key'])

        # Для boolean - CheckBox
        elif 'bool' in type_lower:
            return QCheckBox()

        # Для целых чисел - SpinBox
        elif any(num_type in type_lower for num_type in ['int', 'serial']):
            spinbox = QSpinBox()
            spinbox.setRange(-2147483647, 2147483647)  # PostgreSQL integer range
            return spinbox

        # Для чисел с плавающей точкой
        elif any(float_type in type_lower for float_type in ['numeric', 'decimal', 'real', 'double']):
            from PySide6.QtWidgets import QDoubleSpinBox
            spinbox = QDoubleSpinBox()
            spinbox.setRange(-999999999.99, 999999999.99)
            spinbox.setDecimals(2)
            return spinbox

        # Для даты
        elif 'date' in type_lower:
            from PySide6.QtWidgets import QDateEdit
            date_edit = QDateEdit()
            date_edit.setCalendarPopup(False)
            date_edit.setDate(QDate.currentDate())
            return date_edit

        # Для времени
        elif 'time' in type_lower and 'date' not in type_lower:
            from PySide6.QtWidgets import QTimeEdit
            time_edit = QTimeEdit()
            time_edit.setTime(QTime.currentTime())
            return time_edit

        # Для timestamp (дата и время)
        elif 'timestamp' in type_lower:
            from PySide6.QtWidgets import QDateTimeEdit
            datetime_edit = QDateTimeEdit()
            datetime_edit.setCalendarPopup(True)
            datetime_edit.setDateTime(QDateTime.currentDateTime())
            return datetime_edit

        # По умолчанию - текстовое поле
        else:
            line_edit = QLineEdit()
            # Устанавливаем максимальную длину для текстовых полей
            if 'varchar' in type_lower:
                # Парсим длину из типа, например: varchar(100)
                import re
                match = re.search(r'\((\d+)\)', column_type)
                if match:
                    line_edit.setMaxLength(int(match.group(1)))
            return line_edit

    def _create_foreign_key_widget(self, foreign_key_info: Dict[str, Any]):
        """Создает ComboBox для внешнего ключа"""
        combo = QComboBox()
        self._populate_foreign_key_combo(combo, foreign_key_info)
        return combo

    def _populate_foreign_key_combo(self, combo: QComboBox, foreign_key_info: Dict[str, Any]):
        """Заполняет ComboBox значениями из связанной таблицы"""
        try:
            # Сохраняем текущее выбранное значение
            current_data = combo.currentData()

            combo.clear()

            referenced_table = foreign_key_info['referenced_table']
            referenced_column = foreign_key_info['referenced_column'] or self._get_primary_key_column(referenced_table)

            with self.engine.connect() as conn:
                # Получаем все записи из связанной таблицы
                result = conn.execute(text(f"SELECT {referenced_column}, * FROM {referenced_table} ORDER BY 1"))

                for row in result:
                    # Создаем читаемое отображение
                    display_text = self._create_display_text(row, referenced_table)
                    combo.addItem(display_text, row[0])  # row[0] - значение первичного ключа

            # Восстанавливаем предыдущее выбранное значение, если оно еще существует
            if current_data:
                for i in range(combo.count()):
                    if combo.itemData(i) == current_data:
                        combo.setCurrentIndex(i)
                        break

        except Exception as e:
            print(f"Ошибка при заполнении ComboBox для внешнего ключа: {e}")
            combo.addItem("Ошибка загрузки данных", None)

    def _get_primary_key_column(self, table_name: str) -> str:
        """Получает имя первичного ключа таблицы"""
        try:
            inspector = inspect(self.engine)
            pk_constraint = inspector.get_pk_constraint(table_name)
            if pk_constraint and pk_constraint['constrained_columns']:
                return pk_constraint['constrained_columns'][0]
            return "id"  # fallback
        except:
            return "id"

    def _create_display_text(self, row, table_name: str) -> str:
        """Создает читаемый текст для отображения в ComboBox"""
        # Пытаемся найти столбец с именем или описанием
        for col_name, value in row._mapping.items():
            if any(name in col_name.lower() for name in ['name', 'title', 'model', 'description']):
                return f"{value} (ID: {row[0]})"

        # Если не нашли подходящий столбец, используем ID
        return f"Запись {row[0]}"

    def get_table_columns_info(self) -> List[Dict[str, Any]]:
        """Получает информацию о столбцах таблицы (может быть переопределен в дочерних классах)"""
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

    def get_form_data(self) -> Dict[str, Any]:
        """Получает данные из формы"""
        data = {}
        for column_name, widget in self.input_widgets.items():
            if isinstance(widget, QLineEdit):
                value = widget.text().strip()
                data[column_name] = value if value else None
            elif isinstance(widget, QSpinBox):
                data[column_name] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                data[column_name] = widget.value()
            elif isinstance(widget, QCheckBox):
                data[column_name] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                data[column_name] = widget.currentData()
            elif isinstance(widget, QDateEdit):
                data[column_name] = widget.date().toPython()
            elif isinstance(widget, QTimeEdit):
                data[column_name] = widget.time().toPython()
            elif isinstance(widget, QDateTimeEdit):
                data[column_name] = widget.dateTime().toPython()

        return data

    def clear_form(self):
        """Очищает форму"""
        for widget in self.input_widgets.values():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.setValue(0)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(False)
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
            elif isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate())
            elif isinstance(widget, QTimeEdit):
                widget.setTime(QTime.currentTime())
            elif isinstance(widget, QDateTimeEdit):
                widget.setDateTime(QDateTime.currentDateTime())

    def validate_form_data(self, form_data: Dict[str, Any]) -> List[str]:
        """Валидирует данные формы и возвращает список ошибок"""
        errors = []
        columns_info = self.get_table_columns_info()

        for column_info in columns_info:
            column_name = column_info['name']
            column_type = column_info['type']
            is_nullable = column_info['nullable']
            value = form_data.get(column_name)

            # Пропускаем автоинкрементные первичные ключи
            if column_info['primary_key'] and self._is_auto_increment(column_type):
                continue

            # Проверка на обязательность
            if not is_nullable and (value is None or value == '' or value == 0):
                errors.append(f"Поле '{column_name}' является обязательным")
                continue

            # Проверка типов данных
            if value is not None and value != '':
                try:
                    self._validate_column_value(column_name, value, column_type, column_info)
                except ValidationError as e:
                    errors.append(str(e))

        return errors

    def _validate_column_value(self, column_name: str, value: Any, column_type: str, column_info: Dict[str, Any]):
        """Валидирует значение для конкретного столбца"""
        type_lower = column_type.lower()

        # Для текстовых полей
        if any(text_type in type_lower for text_type in ['varchar', 'text', 'char']):
            if not isinstance(value, str):
                raise ValidationError(f"Поле '{column_name}' должно содержать текст")

            # Проверка длины для varchar
            if 'varchar' in type_lower:
                match = re.search(r'varchar\((\d+)\)', type_lower)
                if match:
                    max_length = int(match.group(1))
                    if len(value) > max_length:
                        raise ValidationError(
                            f"Текст в поле '{column_name}' слишком длинный. Максимальная длина: {max_length} символов")

        # Для целых чисел
        elif any(int_type in type_lower for int_type in ['int', 'serial']):
            if not isinstance(value, int) and not (isinstance(value, str) and value.isdigit()):
                raise ValidationError(f"Поле '{column_name}' должно содержать целое число")

        # Для чисел с плавающей точкой
        elif any(float_type in type_lower for float_type in ['numeric', 'decimal', 'real', 'double']):
            if not isinstance(value, (int, float)) and not (isinstance(value, str) and self._is_float(value)):
                raise ValidationError(f"Поле '{column_name}' должно содержать число")

        # Для boolean
        elif 'bool' in type_lower:
            if not isinstance(value, bool):
                raise ValidationError(f"Поле '{column_name}' должно быть логическим значением (Да/Нет)")

        # Для дат
        elif 'date' in type_lower:
            if not isinstance(value, (str, date)):
                raise ValidationError(f"Поле '{column_name}' должно содержать дату")

    def _is_float(self, value: str) -> bool:
        """Проверяет, можно ли преобразовать строку в float"""
        try:
            float(value)
            return True
        except ValueError:
            return False

    def get_form_data(self) -> Dict[str, Any]:
        """Получает данные из формы с базовой валидацией"""
        data = {}
        for column_name, widget in self.input_widgets.items():
            try:
                if isinstance(widget, QLineEdit):
                    value = widget.text().strip()
                    data[column_name] = value if value else None
                elif isinstance(widget, QSpinBox):
                    data[column_name] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    data[column_name] = widget.value()
                elif isinstance(widget, QCheckBox):
                    data[column_name] = widget.isChecked()
                elif isinstance(widget, QComboBox):
                    data[column_name] = widget.currentData()
                elif isinstance(widget, QDateEdit):
                    data[column_name] = widget.date().toPython()
                elif isinstance(widget, QTimeEdit):
                    data[column_name] = widget.time().toPython()
                elif isinstance(widget, QDateTimeEdit):
                    data[column_name] = widget.dateTime().toPython()
            except Exception as e:
                raise ValidationError(f"Ошибка получения данных из поля '{column_name}': {str(e)}")

        return data

    def show_validation_errors(self, errors: List[str]):
        """Показывает ошибки валидации в понятном виде"""
        if errors:
            error_text = "Обнаружены ошибки:\n\n" + "\n".join(f"• {error}" for error in errors)
            QMessageBox.warning(self, "Ошибки ввода", error_text)
            return False
        return True

    def _format_sql_error(self, error_str: str) -> str:
        """Форматирует SQL ошибку в понятный для пользователя вид"""
        # Аналогично методам в других классах
        error_mappings = {
            "null value in column": "Обязательное поле не заполнено",
            "violates check constraint": "Нарушено ограничение проверки данных",
            "violates foreign key constraint": "Ссылка на несуществующую запись",
            "duplicate key value violates unique constraint": "Такая запись уже существует",
            "value too long for type": "Превышена максимальная длина текста",
            "invalid input syntax": "Неверный формат данных"
        }

        for key, message in error_mappings.items():
            if key in error_str.lower():
                return f"{message}. Проверьте введенные данные."

        return f"Ошибка базы данных:\n{error_str}"

    def add_form_rows(self):
        """Может быть переопределен в дочерних классах для добавления кастомных полей"""
        pass

    def connect_buttons(self):
        """Должен быть переопределен в дочерних классах"""
        pass
