from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QTextEdit, QPushButton, QComboBox, QMessageBox,
    QTabWidget, QWidget, QCheckBox, QScrollArea, QFormLayout,
    QListWidget, QListWidgetItem
)

from PySide6.QtCore import Qt
from sqlalchemy import text


class CTEWindow(QDialog):
    def __init__(self, engine, current_table, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.current_table = current_table
        self.cte_queries = {}  # Словарь для хранения CTE запросов: имя -> запрос
        self.selected_cte_name = None  # Имя выбранного CTE
        self.selected_cte_query = None  # SQL запрос выбранного CTE

        self.setWindowTitle("Конструктор Common Table Expressions (CTE)")
        self.setMinimumSize(1000, 700)
        self.setup_ui()
        self.load_table_columns()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Создаем вкладки
        self.tabs = QTabWidget()

        # Вкладка создания CTE
        create_tab = self.create_cte_tab()
        self.tabs.addTab(create_tab, "Создание CTE")

        # Вкладка выполнения CTE
        execute_tab = self.execute_cte_tab()
        self.tabs.addTab(execute_tab, "Выполнение CTE")

        self.tabs.currentChanged.connect(self.on_tab_changed)

        layout.addWidget(self.tabs)

        # Кнопки внизу
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.apply_button = QPushButton("Применить CTE")
        self.apply_button.clicked.connect(self.apply_cte)
        self.apply_button.setEnabled(False)

        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.reject)

        buttons_layout.addWidget(self.apply_button)
        buttons_layout.addWidget(self.close_button)

        layout.addLayout(buttons_layout)

    def create_cte_tab(self):
        """Создает вкладку для создания CTE"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # Группа имени CTE
        name_group = QGroupBox("Имя CTE")
        name_layout = QHBoxLayout(name_group)
        name_layout.addWidget(QLabel("Имя CTE:"))
        self.cte_name_edit = QLineEdit()
        self.cte_name_edit.setPlaceholderText("например: aircraft_info, recent_flights")
        name_layout.addWidget(self.cte_name_edit)
        content_layout.addWidget(name_group)

        # Группа базовой таблицы
        table_group = QGroupBox("Базовая таблица")
        table_layout = QVBoxLayout(table_group)

        table_layout.addWidget(QLabel("Выберите таблицу:"))
        self.table_combo = QComboBox()
        self.table_combo.currentTextChanged.connect(self.on_table_changed)
        table_layout.addWidget(self.table_combo)

        # Загружаем список таблиц
        self.load_tables()

        content_layout.addWidget(table_group)

        # Группа выбора колонок
        columns_group = QGroupBox("Выбор колонок")
        columns_layout = QVBoxLayout(columns_group)

        self.column_checkboxes = {}
        self.columns_container = QWidget()
        self.columns_layout = QVBoxLayout(self.columns_container)
        columns_layout.addWidget(self.columns_container)

        # Кнопки выбора колонок
        column_buttons_layout = QHBoxLayout()
        self.select_all_cols_button = QPushButton("Выбрать все")
        self.select_all_cols_button.clicked.connect(self.select_all_columns)
        self.select_none_cols_button = QPushButton("Снять все")
        self.select_none_cols_button.clicked.connect(self.select_none_columns)
        column_buttons_layout.addWidget(self.select_all_cols_button)
        column_buttons_layout.addWidget(self.select_none_cols_button)
        column_buttons_layout.addStretch()
        columns_layout.addLayout(column_buttons_layout)

        content_layout.addWidget(columns_group)

        # Группа условий
        conditions_group = QGroupBox("Условия (опционально)")
        conditions_form = QFormLayout(conditions_group)

        self.where_edit = QLineEdit()
        self.where_edit.setPlaceholderText("WHERE условие, например: year > 2018")
        conditions_form.addRow("WHERE:", self.where_edit)

        self.group_by_edit = QLineEdit()
        self.group_by_edit.setPlaceholderText("GROUP BY колонки, через запятую")
        conditions_form.addRow("GROUP BY:", self.group_by_edit)

        self.having_edit = QLineEdit()
        self.having_edit.setPlaceholderText("HAVING условие")
        conditions_form.addRow("HAVING:", self.having_edit)

        self.order_by_edit = QLineEdit()
        self.order_by_edit.setPlaceholderText("ORDER BY колонки, например: created_at DESC")
        conditions_form.addRow("ORDER BY:", self.order_by_edit)

        self.limit_edit = QLineEdit()
        self.limit_edit.setPlaceholderText("LIMIT число")
        conditions_form.addRow("LIMIT:", self.limit_edit)

        content_layout.addWidget(conditions_group)


        self.cte_preview = QTextEdit()

        # Кнопки управления
        buttons_group = QGroupBox()
        buttons_layout = QHBoxLayout(buttons_group)

        self.save_button = QPushButton("Сохранить CTE")
        self.save_button.clicked.connect(self.save_cte)
        buttons_layout.addWidget(self.save_button)

        self.clear_button = QPushButton("Очистить форму")
        self.clear_button.clicked.connect(self.clear_form)
        buttons_layout.addWidget(self.clear_button)

        buttons_layout.addStretch()
        content_layout.addWidget(buttons_group)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        return tab

    def execute_cte_tab(self):
        """Создает вкладку для выполнения CTE"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # Группа выбора CTE
        select_group = QGroupBox("Выбор CTE")
        select_layout = QVBoxLayout(select_group)

        select_layout.addWidget(QLabel("Сохраненные CTE:"))

        # Список CTE
        self.cte_list = QListWidget()
        self.cte_list.itemSelectionChanged.connect(self.on_cte_selected)
        select_layout.addWidget(self.cte_list)

        # Кнопки управления списком
        list_buttons_layout = QHBoxLayout()

        self.refresh_list_button = QPushButton("Обновить список")
        self.refresh_list_button.clicked.connect(self.refresh_cte_list)
        list_buttons_layout.addWidget(self.refresh_list_button)

        self.delete_cte_button = QPushButton("Удалить CTE")
        self.delete_cte_button.clicked.connect(self.delete_selected_cte)
        self.delete_cte_button.setEnabled(False)
        list_buttons_layout.addWidget(self.delete_cte_button)

        list_buttons_layout.addStretch()
        select_layout.addLayout(list_buttons_layout)

        content_layout.addWidget(select_group)

        self.selected_cte_preview = QTextEdit()
        self.selected_cte_preview.setMaximumHeight(150)
        self.selected_cte_preview.setReadOnly(True)

        # Группа выполнения
        execute_group = QGroupBox("Выполнение запроса")
        execute_layout = QVBoxLayout(execute_group)

        # Предпросмотр полного SQL
        execute_layout.addWidget(QLabel("Полный SQL запрос:"))
        self.full_sql_preview = QTextEdit()
        self.full_sql_preview.setMaximumHeight(100)
        self.full_sql_preview.setReadOnly(True)
        execute_layout.addWidget(self.full_sql_preview)

        content_layout.addWidget(execute_group)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        return tab

    def load_tables(self):
        """Загружает список таблиц из базы данных"""
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                tables = [row[0] for row in conn.execute(query)]
                self.table_combo.addItems(tables)

                # Устанавливаем текущую таблицу, если она в списке
                if self.current_table in tables:
                    self.table_combo.setCurrentText(self.current_table)

        except Exception as e:
            print(f"Ошибка загрузки таблиц: {e}")

    def load_table_columns(self):
        """Загружает колонки текущей таблицы"""
        table_name = self.table_combo.currentText()
        if not table_name:
            return

        if hasattr(self, 'column_checkboxes'):
            # Очищаем текущие чекбоксы
            for checkbox in self.column_checkboxes.values():
                checkbox.setParent(None)
            self.column_checkboxes.clear()

        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = :table_name 
                    ORDER BY ordinal_position
                """)
                columns = [row[0] for row in conn.execute(query, {'table_name': table_name})]

                for column in columns:
                    checkbox = QCheckBox(column)
                    checkbox.setChecked(True)
                    self.column_checkboxes[column] = checkbox
                    self.columns_layout.addWidget(checkbox)

        except Exception as e:
            print(f"Ошибка загрузки колонок: {e}")

    def on_table_changed(self, table_name):
        """Обработчик изменения выбранной таблицы"""
        if table_name:
            self.load_table_columns()

    def select_all_columns(self):
        """Выбирает все колонки"""
        for checkbox in self.column_checkboxes.values():
            checkbox.setChecked(True)

    def select_none_columns(self):
        """Снимает выбор со всех колонок"""
        for checkbox in self.column_checkboxes.values():
            checkbox.setChecked(False)

    def generate_cte(self):
        """Генерирует CTE запрос"""
        cte_name = self.cte_name_edit.text().strip()
        table_name = self.table_combo.currentText()

        if not cte_name:
            QMessageBox.warning(self, "Ошибка", "Введите имя CTE")
            return

        if not table_name:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу")
            return

        # Получаем выбранные колонки
        selected_columns = []
        for col_name, checkbox in self.column_checkboxes.items():
            if checkbox.isChecked():
                selected_columns.append(col_name)

        if not selected_columns:
            selected_columns = ["*"]

        columns_str = ", ".join(selected_columns)
        query = f"SELECT {columns_str} FROM {table_name}"

        # Добавляем условия
        where = self.where_edit.text().strip()
        if where:
            query += f" WHERE {where}"

        group_by = self.group_by_edit.text().strip()
        if group_by:
            query += f" GROUP BY {group_by}"

        having = self.having_edit.text().strip()
        if having:
            query += f" HAVING {having}"

        order_by = self.order_by_edit.text().strip()
        if order_by:
            query += f" ORDER BY {order_by}"

        limit = self.limit_edit.text().strip()
        if limit and limit.isdigit():
            query += f" LIMIT {limit}"

        # Формируем полный CTE
        cte_query = f"WITH {cte_name} AS (\n    {query}\n)"

        self.cte_preview.setPlainText(cte_query)
        self.save_button.setEnabled(True)

        # Сохраняем для временного использования
        self.temp_cte_name = cte_name
        self.temp_cte_query = cte_query

    def save_cte(self):
        """Сохраняет CTE"""
        self.generate_cte()
        cte_name = self.cte_name_edit.text().strip()
        cte_query = self.cte_preview.toPlainText().strip()

        if not cte_name or not cte_query:
            QMessageBox.warning(self, "Ошибка", "Сначала сгенерируйте CTE")
            return

        # Проверяем, нет ли CTE с таким именем
        if cte_name in self.cte_queries:
            reply = QMessageBox.question(
                self,
                "CTE существует",
                f"CTE с именем '{cte_name}' уже существует. Заменить?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Сохраняем CTE
        self.cte_queries[cte_name] = cte_query

        # Обновляем список CTE
        self.refresh_cte_list()

        # Выбираем только что созданный CTE
        items = self.cte_list.findItems(cte_name, Qt.MatchFlag.MatchExactly)
        if items:
            self.cte_list.setCurrentItem(items[0])

        QMessageBox.information(self, "Успех", f"CTE '{cte_name}' сохранен")

        # Очищаем форму
        self.clear_form()

    def clear_form(self):
        """Очищает форму создания CTE"""
        self.cte_name_edit.clear()
        self.where_edit.clear()
        self.group_by_edit.clear()
        self.having_edit.clear()
        self.order_by_edit.clear()
        self.limit_edit.clear()
        self.cte_preview.clear()
        self.save_button.setEnabled(False)

    def refresh_cte_list(self):
        """Обновляет список CTE"""
        self.cte_list.clear()

        for cte_name in sorted(self.cte_queries.keys()):
            item = QListWidgetItem(cte_name)
            item.setData(Qt.ItemDataRole.UserRole, cte_name)
            self.cte_list.addItem(item)

    def on_cte_selected(self):
        """Обработчик выбора CTE в списке"""
        selected_items = self.cte_list.selectedItems()

        if not selected_items:
            self.selected_cte_name = None
            self.selected_cte_query = None
            self.selected_cte_preview.clear()
            self.delete_cte_button.setEnabled(False)
            self.apply_button.setEnabled(False)
            return

        cte_name = selected_items[0].text()
        self.selected_cte_name = cte_name

        # Получаем запрос CTE
        if cte_name in self.cte_queries:
            cte_query = self.cte_queries[cte_name]
            self.selected_cte_query = cte_query
            self.selected_cte_preview.setPlainText(cte_query)

            self.delete_cte_button.setEnabled(True)
            self.update_full_sql_preview()

            # Включаем кнопки если есть основной запрос
            main_query = self.selected_cte_preview.toPlainText().strip()
            if main_query:
                self.apply_button.setEnabled(True)

    def delete_selected_cte(self):
        """Удаляет выбранный CTE"""
        selected_items = self.cte_list.selectedItems()
        if not selected_items:
            return

        cte_name = selected_items[0].text()

        reply = QMessageBox.question(
            self,
            "Удаление CTE",
            f"Удалить CTE '{cte_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Удаляем из словаря
            if cte_name in self.cte_queries:
                del self.cte_queries[cte_name]

            # Обновляем список
            self.refresh_cte_list()

            # Очищаем предпросмотры
            self.selected_cte_name = None
            self.selected_cte_query = None
            self.selected_cte_preview.clear()
            self.full_sql_preview.clear()

            self.delete_cte_button.setEnabled(False)
            self.apply_button.setEnabled(False)

            QMessageBox.information(self, "Успех", f"CTE '{cte_name}' удален")

    def set_main_query(self, query_template):
        """Устанавливает шаблон основного запроса"""
        if not self.selected_cte_name:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите CTE")
            return

        query = query_template.replace("  ", f" {self.selected_cte_name} ")
        self.selected_cte_preview.setPlainText(query)
        self.on_main_query_changed()

    def on_main_query_changed(self):
        """Обработчик изменения основного запроса"""
        main_query = self.selected_cte_preview.toPlainText().strip()

        if main_query and self.selected_cte_name:
            self.update_full_sql_preview()
            self.apply_button.setEnabled(True)
        else:
            self.full_sql_preview.clear()
            self.apply_button.setEnabled(False)

    def update_full_sql_preview(self):
        """Обновляет предпросмотр полного SQL запроса"""
        if not self.selected_cte_name or not self.selected_cte_query:
            return

        main_query = self.selected_cte_preview.toPlainText().strip()
        if not main_query:
            return

        # Формируем полный запрос: CTE + основной запрос
        full_sql = f"{main_query}\n SELECT * FROM {self.selected_cte_name};"
        self.full_sql_preview.setPlainText(full_sql)

    def test_cte_query(self):
        """Тестирует SQL запрос с CTE"""
        sql = self.full_sql_preview.toPlainText().strip()
        if not sql:
            QMessageBox.warning(self, "Ошибка", "Сначала создайте полный запрос")
            return

        try:
            with self.engine.connect() as conn:
                # Пробуем выполнить запрос
                result = conn.execute(text(sql))

                # Получаем первую запись для проверки
                first_row = result.fetchone()

                if first_row:
                    QMessageBox.information(
                        self,
                        "Тест успешен",
                        f"Запрос выполнен успешно.\n"
                        f"Колонки: {', '.join(result.keys())}\n"
                        f"Первая запись: {dict(zip(result.keys(), first_row))}"
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Тест успешен",
                        "Запрос выполнен успешно (нет данных)."
                    )

        except Exception as e:
            QMessageBox.critical(self, "Ошибка выполнения", f"Ошибка при выполнении запроса:\n{str(e)}")

    def execute_cte_query(self):
        """Выполняет SQL запрос с CTE и показывает результаты"""
        sql = self.full_sql_preview.toPlainText().strip()
        if not sql:
            QMessageBox.warning(self, "Ошибка", "Сначала создайте полный запрос")
            return

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))

                # Создаем диалог для отображения результатов
                result_dialog = QDialog(self)
                result_dialog.setWindowTitle(f"Результаты CTE: {self.selected_cte_name}")
                result_dialog.setMinimumSize(800, 600)

                layout = QVBoxLayout(result_dialog)

                # Текст запроса
                query_label = QLabel("Выполненный запрос:")
                layout.addWidget(query_label)

                query_text = QTextEdit()
                query_text.setPlainText(sql)
                query_text.setReadOnly(True)
                query_text.setMaximumHeight(100)
                layout.addWidget(query_text)

                # Таблица результатов
                from PySide6.QtWidgets import QTableView
                from PySide6.QtGui import QStandardItemModel, QStandardItem

                result_label = QLabel("Результаты:")
                layout.addWidget(result_label)

                result_table = QTableView()

                # Создаем модель для таблицы
                model = QStandardItemModel()

                # Устанавливаем заголовки колонок
                columns = result.keys()
                model.setHorizontalHeaderLabels(columns)

                # Получаем все строки
                rows = result.fetchall()

                # Заполняем модель данными
                for row in rows:
                    row_items = []
                    for value in row:
                        item = QStandardItem(str(value) if value is not None else "")
                        row_items.append(item)
                    model.appendRow(row_items)

                # Устанавливаем модель в таблицу
                result_table.setModel(model)

                # Настраиваем отображение
                result_table.horizontalHeader().setStretchLastSection(True)
                result_table.setAlternatingRowColors(True)

                layout.addWidget(result_table)

                # Информация о количестве строк
                count_label = QLabel(f"Найдено записей: {len(rows)}")
                layout.addWidget(count_label)

                # Кнопка закрытия
                close_button = QPushButton("Закрыть")
                close_button.clicked.connect(result_dialog.accept)
                layout.addWidget(close_button)

                result_dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка выполнения", f"Ошибка при выполнении запроса:\n{str(e)}")

    def on_tab_changed(self, index):
        """Обработчик изменения вкладки"""
        if index == 1:  # Вкладка выполнения
            self.refresh_cte_list()

    def apply_cte(self):
        """Применяет CTE запрос (возвращает его родительскому окну)"""
        if not self.full_sql_preview:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите CTE")
            return

        full_sql = self.full_sql_preview.toPlainText().strip()
        if not full_sql:
            QMessageBox.warning(self, "Ошибка", "Введите основной запрос")
            return

        self.accept()

    def get_cte_query(self):
        """Возвращает подготовленный CTE запрос"""
        return self.full_sql_preview.toPlainText().strip()