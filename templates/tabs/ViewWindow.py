from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit,
    QTextEdit, QPushButton, QComboBox,
    QMessageBox, QTabWidget, QWidget,
    QCheckBox, QScrollArea, QFormLayout
)

from sqlalchemy import text


class ViewWindow(QDialog):
    def __init__(self, engine, current_table, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.current_table = current_table
        self.view_query = None

        self.setWindowTitle("Управление VIEW запросами")
        self.setMinimumSize(1000, 700)
        self.setup_ui()
        self.load_existing_views()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Создаем вкладки
        self.tabs = QTabWidget()

        # Вкладка создания VIEW
        create_tab = self.create_view_tab()
        self.tabs.addTab(create_tab, "Создание VIEW")

        # Вкладка управления VIEW
        manage_tab = self.manage_view_tab()
        self.tabs.addTab(manage_tab, "Управление VIEW")

        layout.addWidget(self.tabs)

        # Кнопки внизу
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.apply_button = QPushButton("Применить VIEW")
        self.apply_button.clicked.connect(self.apply_view)
        self.apply_button.setEnabled(False)

        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.reject)

        buttons_layout.addWidget(self.apply_button)
        buttons_layout.addWidget(self.close_button)

        layout.addLayout(buttons_layout)

    def create_view_tab(self):
        """Создает вкладку для создания VIEW"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # Группа типа VIEW
        type_group = QGroupBox("Тип представления")
        type_layout = QHBoxLayout(type_group)
        type_layout.addWidget(QLabel("Тип:"))
        self.view_type_combo = QComboBox()
        self.view_type_combo.addItems(["VIEW", "MATERIALIZED VIEW", "TEMPORARY VIEW"])
        type_layout.addWidget(self.view_type_combo)
        content_layout.addWidget(type_group)

        # Группа имени VIEW
        name_group = QGroupBox("Имя представления")
        name_layout = QHBoxLayout(name_group)
        name_layout.addWidget(QLabel("Имя:"))
        self.view_name_edit = QLineEdit()
        self.view_name_edit.setPlaceholderText("например: v_aircraft_info")
        name_layout.addWidget(self.view_name_edit)
        content_layout.addWidget(name_group)

        # Группа базовой таблицы
        base_table_group = QGroupBox("Базовая таблица")
        base_table_layout = QHBoxLayout(base_table_group)
        base_table_layout.addWidget(QLabel("Таблица:"))
        self.base_table_edit = QLineEdit()
        self.base_table_edit.setText(self.current_table)
        self.base_table_edit.setReadOnly(True)
        base_table_layout.addWidget(self.base_table_edit)
        content_layout.addWidget(base_table_group)

        # Группа выбора колонок
        columns_group = QGroupBox("Выбор колонок")
        columns_layout = QVBoxLayout(columns_group)

        # Загружаем колонки из таблицы
        columns = self.get_table_columns(self.current_table)
        self.column_checkboxes = {}

        for column in columns:
            checkbox = QCheckBox(column)
            checkbox.setChecked(True)
            self.column_checkboxes[column] = checkbox
            columns_layout.addWidget(checkbox)

        # Кнопка выбора всех/ни одного
        select_buttons_layout = QHBoxLayout()
        self.select_all_button = QPushButton("Выбрать все")
        self.select_all_button.clicked.connect(self.select_all_columns)
        self.select_none_button = QPushButton("Снять все")
        self.select_none_button.clicked.connect(self.select_none_columns)
        select_buttons_layout.addWidget(self.select_all_button)
        select_buttons_layout.addWidget(self.select_none_button)
        select_buttons_layout.addStretch()
        columns_layout.addLayout(select_buttons_layout)

        content_layout.addWidget(columns_group)

        # Группа условий
        conditions_group = QGroupBox("Условия (опционально)")
        conditions_form = QFormLayout(conditions_group)

        self.where_edit = QLineEdit()
        self.where_edit.setPlaceholderText("WHERE condition, например: year > 2018")
        conditions_form.addRow("WHERE:", self.where_edit)

        self.group_by_edit = QLineEdit()
        self.group_by_edit.setPlaceholderText("GROUP BY columns, например: model, year")
        conditions_form.addRow("GROUP BY:", self.group_by_edit)

        self.having_edit = QLineEdit()
        self.having_edit.setPlaceholderText("HAVING condition, например: COUNT(*) > 1")
        conditions_form.addRow("HAVING:", self.having_edit)

        self.order_by_edit = QLineEdit()
        self.order_by_edit.setPlaceholderText("ORDER BY columns, например: year DESC")
        conditions_form.addRow("ORDER BY:", self.order_by_edit)

        content_layout.addWidget(conditions_group)

        self.sql_preview = QTextEdit()

        # Кнопка создания VIEW
        self.create_button = QPushButton("Создать VIEW")
        self.create_button.clicked.connect(self.create_view)
        content_layout.addWidget(self.create_button)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        return tab

    def manage_view_tab(self):
        """Создает вкладку для управления существующими VIEW"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # Группа выбора VIEW
        select_group = QGroupBox("Выбор VIEW")
        select_layout = QHBoxLayout(select_group)
        select_layout.addWidget(QLabel("VIEW:"))
        self.view_combo = QComboBox()
        self.view_combo.setEditable(True)
        self.view_combo.setMinimumWidth(200)
        select_layout.addWidget(self.view_combo)

        self.refresh_button = QPushButton("Обновить список")
        self.refresh_button.clicked.connect(self.load_existing_views)
        select_layout.addWidget(self.refresh_button)

        select_layout.addStretch()
        content_layout.addWidget(select_group)

        # Группа действий
        actions_group = QGroupBox("Действия с VIEW")
        actions_layout = QHBoxLayout(actions_group)

        self.select_button = QPushButton("Выбрать из VIEW")
        self.select_button.clicked.connect(self.select_from_view)
        actions_layout.addWidget(self.select_button)

        self.drop_button = QPushButton("Удалить VIEW")
        self.drop_button.clicked.connect(self.drop_view)
        actions_layout.addWidget(self.drop_button)

        self.refresh_mv_button = QPushButton("Обновить MATERIALIZED VIEW")
        self.refresh_mv_button.clicked.connect(self.refresh_materialized_view)
        actions_layout.addWidget(self.refresh_mv_button)

        actions_layout.addStretch()
        content_layout.addWidget(actions_group)

        # Группа SQL запроса из VIEW
        query_group = QGroupBox("SQL запрос из VIEW")
        query_layout = QVBoxLayout(query_group)
        self.view_query_text = QTextEdit()
        self.view_query_text.setMaximumHeight(300)
        self.view_query_text.setReadOnly(True)
        query_layout.addWidget(self.view_query_text)

        content_layout.addWidget(query_group)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        return tab

    def get_table_columns(self, table_name):
        """Получает список колонок таблицы"""
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = :table_name 
                    ORDER BY ordinal_position
                """)
                result = conn.execute(query, {'table_name': table_name})
                return [row[0] for row in result]
        except:
            # Возвращаем демо-колонки в случае ошибки
            return ["id", "name", "created_at", "updated_at"]

    def select_all_columns(self):
        """Выбирает все колонки"""
        for checkbox in self.column_checkboxes.values():
            checkbox.setChecked(True)

    def select_none_columns(self):
        """Снимает выбор со всех колонок"""
        for checkbox in self.column_checkboxes.values():
            checkbox.setChecked(False)

    def generate_sql(self):
        """Генерирует SQL для создания VIEW"""
        view_name = self.view_name_edit.text().strip()
        view_type = self.view_type_combo.currentText()

        if not view_name:
            QMessageBox.warning(self, "Ошибка", "Введите имя VIEW")
            return

        # Получаем выбранные колонки
        selected_columns = []
        for col_name, checkbox in self.column_checkboxes.items():
            if checkbox.isChecked():
                selected_columns.append(col_name)

        if not selected_columns:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы одну колонку")
            return

        # Формируем базовый SELECT
        columns_str = ", ".join(selected_columns)
        base_query = f"SELECT {columns_str} FROM {self.current_table}"

        # Добавляем условия
        where = self.where_edit.text().strip()
        if where:
            base_query += f" WHERE {where}"

        group_by = self.group_by_edit.text().strip()
        if group_by:
            base_query += f" GROUP BY {group_by}"

        having = self.having_edit.text().strip()
        if having:
            base_query += f" HAVING {having}"

        order_by = self.order_by_edit.text().strip()
        if order_by:
            base_query += f" ORDER BY {order_by}"

        # Формируем полный CREATE запрос
        if view_type == "VIEW":
            sql = f"CREATE OR REPLACE VIEW {view_name} AS\n{base_query};"
        elif view_type == "MATERIALIZED VIEW":
            sql = f"CREATE MATERIALIZED VIEW IF NOT EXISTS {view_name} AS\n{base_query};"
        else:  # TEMPORARY VIEW
            sql = f"CREATE OR REPLACE TEMPORARY VIEW {view_name} AS\n{base_query};"

        self.sql_preview.setPlainText(sql)
        return 1

    def create_view(self):
        """Создает VIEW"""
        if not self.generate_sql():
            return
        sql = self.sql_preview.toPlainText().strip()

        try:
            with self.engine.begin() as conn:
                conn.execute(text(sql))
                QMessageBox.information(self, "Успех", "VIEW успешно создан")
                self.load_existing_views()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать VIEW:\n{str(e)}")

    def load_existing_views(self):
        """Загружает список существующих VIEW"""
        try:
            with self.engine.connect() as conn:
                # Получаем обычные VIEW
                query = text("""
                    SELECT table_name 
                    FROM information_schema.views 
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY table_name
                """)
                views = [row[0] for row in conn.execute(query)]

                # Получаем MATERIALIZED VIEW
                query = text("""
                    SELECT matviewname 
                    FROM pg_matviews 
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY matviewname
                """)
                materialized_views = [row[0] for row in conn.execute(query)]

                # Обновляем комбобокс
                self.view_combo.clear()
                for view in views:
                    self.view_combo.addItem(f"VIEW: {view}", view)
                for mv in materialized_views:
                    self.view_combo.addItem(f"MATERIALIZED VIEW: {mv}", mv)

        except Exception as e:
            print(f"Ошибка загрузки VIEW: {e}")

    def select_from_view(self):
        """Создает SELECT запрос из выбранного VIEW"""
        view_name = self.view_combo.currentData()
        if not view_name:
            QMessageBox.warning(self, "Ошибка", "Выберите VIEW")
            return

        sql = f"SELECT * FROM {view_name}"
        self.view_query_text.setPlainText(sql)
        self.view_query = sql
        self.apply_button.setEnabled(True)

        QMessageBox.information(self, "Готово",
                                f"SELECT запрос для VIEW '{view_name}' подготовлен.\nНажмите 'Применить VIEW' для выполнения.")

    def drop_view(self):
        """Удаляет выбранный VIEW"""
        view_name = self.view_combo.currentData()
        if not view_name:
            QMessageBox.warning(self, "Ошибка", "Выберите VIEW")
            return

        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Вы уверены, что хотите удалить '{view_name}'?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                # Определяем тип VIEW
                with self.engine.connect() as conn:
                    # Проверяем, является ли это MATERIALIZED VIEW
                    query = text("""
                                            SELECT 
                                                CASE 
                                                    WHEN EXISTS (SELECT 1 FROM pg_matviews WHERE matviewname = :name) 
                                                    THEN 'MATERIALIZED VIEW' 
                                                    ELSE 'VIEW' 
                                                END as type,
                                                schemaname
                                            FROM (
                                                SELECT 'VIEW' as obj_type, table_schema as schemaname
                                                FROM information_schema.views 
                                                WHERE table_name = :name
                                                UNION ALL
                                                SELECT 'MATERIALIZED VIEW', schemaname
                                                FROM pg_matviews 
                                                WHERE matviewname = :name
                                            ) as view_info
                                        """)

                    result = conn.execute(query, {'name': view_name}).fetchone()

                    if not result:
                        QMessageBox.warning(self, "Ошибка", f"VIEW '{view_name}' не найден")
                        return

                    view_type = result[0]
                    schema = result[1]

                    # Формируем полное имя со схемой
                    full_view_name = f"{schema}.{view_name}" if schema else view_name

                    if view_type == 'MATERIALIZED VIEW':
                        sql = f"DROP MATERIALIZED VIEW IF EXISTS {full_view_name} CASCADE"
                    else:
                        sql = f"DROP VIEW IF EXISTS {full_view_name} CASCADE"

                    with self.engine.begin() as conn_trans:
                        conn_trans.execute(text(sql))
                    QMessageBox.information(self, "Успех", "VIEW успешно удален")
                    self.load_existing_views()
                    self.view_query_text.clear()

            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить VIEW:\n{str(e)}")

    def refresh_materialized_view(self):
        """Обновляет MATERIALIZED VIEW"""
        view_name = self.view_combo.currentData()
        if not view_name:
            QMessageBox.warning(self, "Ошибка", "Выберите VIEW")
            return

        try:
            with self.engine.begin() as conn:
                # Проверяем, что это MATERIALIZED VIEW
                query = text("SELECT 1 FROM pg_matviews WHERE matviewname = :name")
                result = conn.execute(query, {'name': view_name}).fetchone()

                if not result:
                    QMessageBox.warning(self, "Ошибка",
                                        f"'{view_name}' не является MATERIALIZED VIEW")
                    return

                sql = f"REFRESH MATERIALIZED VIEW {view_name}"
                conn.execute(text(sql))
                QMessageBox.information(self, "Успех", "MATERIALIZED VIEW обновлен")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить VIEW:\n{str(e)}")

    def use_view_query(self):
        """Использует SQL запрос из текстового поля"""
        sql = self.view_query_text.toPlainText().strip()
        if sql:
            self.view_query = sql
            self.apply_button.setEnabled(True)
            QMessageBox.information(self, "Готово", "SQL запрос подготовлен")

    def apply_view(self):
        """Применяет выбранный VIEW запрос"""
        if self.view_query:
            self.accept()

    def get_view_query(self):
        """Возвращает подготовленный VIEW запрос"""
        return self.view_query