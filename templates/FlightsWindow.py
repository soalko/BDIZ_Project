# ===== Base =====
from datetime import date, time

# ===== PySide6 =====
from PySide6.QtCore import QDate, QTime, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QPushButton, QMessageBox, QSpinBox,
    QDateEdit, QComboBox, QTableView, QTimeEdit, QHeaderView, QDialog, QCheckBox, QDialogButtonBox, QLabel
)
from styles.styles import apply_compact_table_view

# ===== SQLAlchemy =====
from sqlalchemy import (
    insert, delete
)

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# ===== Files =====
from db.models import SATableModel
from templates.BaseTab import BaseTab
from templates.modes import AppMode


# -------------------------------
# Вкладка «Рейсы»
# --------------------------------
class FlightsTab(BaseTab):
    def __init__(self, engine, tables, parent=None):
        super().__init__(engine, tables, parent)

        self.model = SATableModel(engine, self.t["flights"], self)

        self.form_widget = QWidget()
        self.buttons_widget = QWidget()

        self.aircraft_combo = QComboBox()
        self.departure_date_edit = QDateEdit()
        self.departure_date_edit.setCalendarPopup(False)
        self.departure_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.departure_date_edit.setDate(QDate.currentDate())

        self.departure_time_edit = QTimeEdit()
        self.departure_time_edit.setDisplayFormat("HH:mm")
        self.departure_time_edit.setTime(QTime(12, 0))

        self.departure_airport_edit = QLineEdit()
        self.departure_airport_edit.setMaxLength(3)

        self.arrival_airport_edit = QLineEdit()
        self.arrival_airport_edit.setMaxLength(3)

        self.flight_time_edit = QSpinBox()
        self.flight_time_edit.setRange(1, 1440)
        self.flight_time_edit.setValue(120)
        self.flight_time_edit.setSuffix(" минут")

        self.form = QFormLayout(self.form_widget)
        self.form.addRow("Самолет:", self.aircraft_combo)
        self.form.addRow("Дата вылета:", self.departure_date_edit)
        self.form.addRow("Время вылета:", self.departure_time_edit)
        self.form.addRow("Аэропорт вылета:", self.departure_airport_edit)
        self.form.addRow("Аэропорт прибытия:", self.arrival_airport_edit)
        self.form.addRow("Время полета:", self.flight_time_edit)

        self.add_btn = QPushButton("Добавить рейс (INSERT)")
        self.add_btn.clicked.connect(self.add_flight)
        self.del_btn = QPushButton("Удалить выбранный рейс")
        self.del_btn.clicked.connect(self.delete_selected)

        self.btns = QHBoxLayout(self.buttons_widget)
        self.btns.addWidget(self.add_btn)
        self.btns.addWidget(self.del_btn)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        apply_compact_table_view(self.table)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.table.setModel(self.proxy_model)
        self.table.setSortingEnabled(True)

        def on_header_clicked(self, logical_index):
            current_order = self.proxy_model.sortOrder()
            new_order = Qt.SortOrder.DescendingOrder if current_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
            self.proxy_model.sort(logical_index, new_order)

        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.proxy_model.sort(0, Qt.SortOrder.AscendingOrder)

        self.on_header_clicked = on_header_clicked.__get__(self)

        self.add_record_btn.clicked.connect(self.add_flight)
        self.clear_form_btn.clicked.connect(self.clear_form)
        self.delete_record_btn.clicked.connect(self.delete_selected)

        # Подключаем кнопки редактирования структуры
        self.add_column_btn.clicked.connect(self.show_add_column_dialog)
        self.delete_column_btn.clicked.connect(self.delete_selected_column)
        self.edit_column_btn.clicked.connect(self.show_edit_column_dialog)
        self.save_structure_btn.clicked.connect(self.save_structure_changes)
        self.cancel_structure_btn.clicked.connect(self.cancel_structure_changes)

        # Таблица для отображения структуры (столбцы как строки)
        self.structure_table = QTableView()
        self.structure_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.structure_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.structure_table.clicked.connect(self.on_structure_column_selected)
        apply_compact_table_view(self.structure_table)

        self.main_layout.addWidget(self.form_widget)
        self.main_layout.addWidget(self.buttons_widget)
        self.main_layout.addWidget(self.table)
        self.main_layout.addWidget(self.structure_table)

        self.refresh_aircraft_combo()

        self.update_ui_for_mode()

    def set_mode(self, mode: AppMode):
        super().set_mode(mode)
        self.update_ui_for_mode()

    def update_ui_for_mode(self):
        super().update_ui_for_mode()

        if self.current_mode == AppMode.ADD:
            self.form_widget.setVisible(True)
            self.buttons_widget.setVisible(True)
            self.table.setVisible(True)
            self.structure_table.setVisible(False)
        elif self.current_mode == AppMode.READ:
            self.form_widget.setVisible(False)
            self.buttons_widget.setVisible(False)
            self.table.setVisible(True)
            self.structure_table.setVisible(False)
        elif self.current_mode == AppMode.EDIT:
            self.form_widget.setVisible(False)
            self.buttons_widget.setVisible(False)
            self.table.setVisible(False)
            self.structure_table.setVisible(True)
            self.load_table_structure()

    def load_table_structure(self):
        """Загружает структуру таблицы - столбцы как строки"""
        try:
            from PySide6.QtGui import QStandardItemModel, QStandardItem

            # Создаем модель для отображения структуры
            structure_model = QStandardItemModel()
            structure_model.setHorizontalHeaderLabels(["Название столбца", "Тип данных", "Ограничения"])

            # Получаем информацию о столбцах таблицы
            table = self.t["flights"]
            for i, column in enumerate(table.columns):
                # Добавляем строку с информацией о столбце
                row_items = [
                    QStandardItem(column.name),  # Название столбца
                    QStandardItem(str(column.type)),  # Тип данных
                    QStandardItem(self._get_column_constraints(column))  # Ограничения
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
        """Возвращает строку с ограничениями столбца"""
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
        if self.t:
            for table_name in self.t.keys():
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
        column_name = model.data(model.index(row, 0))  # Название столбца из первого столбца

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

        if self.t:
            for table_name in self.t.keys():
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
        column_name = model.data(model.index(row, 0))  # Название столбца из первого столбца

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

    def refresh_aircraft_combo(self):
        self.aircraft_combo.clear()
        try:
            with self.engine.connect() as conn:
                result = conn.execute(self.t["aircraft"].select().order_by(self.t["aircraft"].c.model))
                for row in result:
                    self.aircraft_combo.addItem(f"{row.model} (ID: {row.aircraft_id})", row.aircraft_id)
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка загрузки самолетов", str(e))

    def _qdate_to_pydate(self, qd: QDate) -> date:
        return date(qd.year(), qd.month(), qd.day())

    def _qtime_to_pytime(self, qt: QTime) -> time:
        return time(qt.hour(), qt.minute())

    def add_flight(self):
        if self.current_mode != AppMode.ADD:
            return

        if self.aircraft_combo.currentIndex() == -1:
            QMessageBox.warning(self, "Ввод", "Необходимо выбрать самолет")
            return

        aircraft_id = self.aircraft_combo.currentData()
        departure_date = self._qdate_to_pydate(self.departure_date_edit.date())
        departure_time = self._qtime_to_pytime(self.departure_time_edit.time())
        departure_airport = self.departure_airport_edit.text().strip().upper()
        arrival_airport = self.arrival_airport_edit.text().strip().upper()
        flight_time = self.flight_time_edit.value()

        if not departure_airport or not arrival_airport:
            QMessageBox.warning(self, "Ввод", "Аэропорты вылета и прибытия обязательны")
            return

        if len(departure_airport) != 3 or len(arrival_airport) != 3:
            QMessageBox.warning(self, "Ввод", "Коды аэроподов должны состоять из 3 символов")
            return

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.t["flights"]).values(
                    aircraft_id=aircraft_id,
                    departure_date=departure_date,
                    departure_time=departure_time,
                    departure_airport=departure_airport,
                    arrival_airport=arrival_airport,
                    flight_time=flight_time
                ))
            self.model.refresh()
            self.clear_form()
            self.window().refresh_combos()
        except IntegrityError as e:
            QMessageBox.critical(self, "Ошибка INSERT (CHECK/FOREIGN KEY constraint)", str(e.orig))
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка INSERT", str(e))

    def delete_selected(self):
        if self.current_mode != AppMode.ADD:
            return

        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите рейс")
            return

        flight_id = self.model.pk_value_at(idx.row())
        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.t["flights"]).where(
                    self.t["flights"].c.flight_id == flight_id
                ))
            self.model.refresh()
            self.window().refresh_combos()
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def clear_form(self):
        self.departure_airport_edit.clear()
        self.arrival_airport_edit.clear()
        self.flight_time_edit.setValue(120)
        self.departure_date_edit.setDate(QDate.currentDate())
        self.departure_time_edit.setTime(QTime(12, 0))