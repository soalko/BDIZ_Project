# ===== PySide6 =====
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
    QComboBox, QTextEdit, QGroupBox, QSpacerItem, QSizePolicy
)

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont  # Добавляем импорт QFont

# ===== SQLAlchemy =====
from sqlalchemy.exc import SQLAlchemyError

# ===== Files =====
from db.config import PgConfig
from db.session import (
    make_engine
)
from db.models import (
    build_metadata, insert_demo_data_sa, drop_and_create_schema_sa
)
from templates.modes import AppMode


# -------------------------------
# Вкладка «Подключение и схема БД»
# -------------------------------
class SetupTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.driver_cb = QComboBox()
        self.driver_cb.addItem("psycopg2 (binary)", "psycopg2")
        self.driver_cb.addItem("psycopg (v3, binary)", "psycopg")
        self.driver_cb.addItem("pg8000 (pure Python)", "pg8000")

        self.host_edit = QLineEdit("localhost")
        self.port_edit = QLineEdit("5432")
        self.db_edit = QLineEdit("airport")
        self.user_edit = QLineEdit("postgres")
        self.pw_edit = QLineEdit("12345")
        self.pw_edit.setEchoMode(QLineEdit.Password)
        self.ssl_edit = QLineEdit("prefer")

        # Кнопки подключения/отключения
        self.connect_btn = QPushButton("Подключиться к БД")
        self.connect_btn.clicked.connect(self.do_connect)

        self.disconnect_btn = QPushButton("Отключиться от БД")
        self.disconnect_btn.clicked.connect(self.do_disconnect)
        self.disconnect_btn.setEnabled(False)

        # Кнопки управления БД
        self.create_btn = QPushButton("Сбросить и создать БД (CREATE)")
        self.create_btn.setEnabled(False)
        self.create_btn.clicked.connect(self.reset_db)

        self.demo_btn = QPushButton("Добавить демо-данные (INSERT)")
        self.demo_btn.setEnabled(False)
        self.demo_btn.clicked.connect(self.add_demo)

        # Основной layout
        main_layout = QVBoxLayout(self)

        # Верхняя часть - форма подключения и кнопки
        top_layout = QHBoxLayout()

        # Левая часть - только форма подключения
        left_layout = QVBoxLayout()

        conn_form = QFormLayout()
        conn_form.addRow("Driver:", self.driver_cb)
        conn_form.addRow("Host:", self.host_edit)
        conn_form.addRow("Port:", self.port_edit)
        conn_form.addRow("DB name:", self.db_edit)
        conn_form.addRow("User:", self.user_edit)
        conn_form.addRow("Password:", self.pw_edit)
        conn_form.addRow("sslmode:", self.ssl_edit)

        conn_box = QGroupBox("Параметры подключения (SQLAlchemy)")
        conn_box.setLayout(conn_form)
        conn_box.setMaximumWidth(600)

        left_layout.addWidget(conn_box)
        left_layout.addStretch()

        # Центральная часть - кнопки в GroupBox с рамкой
        center_layout = QVBoxLayout()

        # Добавляем растягивающийся спейсер сверху
        center_layout.addStretch()

        # Создаем GroupBox для кнопок с рамкой без названия
        buttons_box = QGroupBox()
        buttons_box.setMaximumWidth(300)  # Ограничиваем ширину GroupBox
        buttons_layout = QVBoxLayout(buttons_box)

        # Добавляем кнопки в GroupBox
        buttons_layout.addWidget(self.connect_btn)
        buttons_layout.addWidget(self.disconnect_btn)
        buttons_layout.addWidget(self.create_btn)
        buttons_layout.addWidget(self.demo_btn)
        buttons_layout.addStretch()  # Растягивающееся пространство между кнопками

        # Добавляем GroupBox с кнопками в центральный layout
        center_layout.addWidget(buttons_box)
        center_layout.addStretch()  # Добавляем растягивающийся спейсер снизу

        # Объединяем все части
        top_layout.addLayout(left_layout)
        top_layout.addLayout(center_layout)

        # Основной layout
        main_layout.addLayout(top_layout)
        main_layout.addWidget(QLabel("Лог:"))
        main_layout.addWidget(self.log)

    def current_cfg(self) -> PgConfig:
        try:
            port = int(self.port_edit.text().strip())
        except ValueError:
            port = 5432
        return PgConfig(
            host=self.host_edit.text().strip() or "localhost",
            port=port,
            dbname=self.db_edit.text().strip() or "airport",
            user=self.user_edit.text().strip() or "postgres",
            password=self.pw_edit.text(),
            sslmode=self.ssl_edit.text().strip() or "prefer",
            driver=self.driver_cb.currentData(),
        )

    def do_connect(self):
        main = self.window()
        if getattr(main, "engine", None) is not None:
            self.log.append("Уже подключено. Нажмите «Отключиться» для переподключения.")
            return

        cfg = self.current_cfg()
        try:
            engine = make_engine(cfg)
            md, tables = build_metadata()
            main.attach_engine(engine, md, tables)
            self.log.append(
                f"Успешное подключение: {cfg.driver} → {cfg.host}:{cfg.port}/{cfg.dbname} (user={cfg.user})"
            )
            self.create_btn.setEnabled(True)
            self.demo_btn.setEnabled(True)
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
        except SQLAlchemyError as e:
            self.log.append(f"Ошибка подключения: {e}")
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def do_disconnect(self):
        main = self.window()
        main.disconnect_db()
        self.create_btn.setEnabled(False)
        self.demo_btn.setEnabled(False)
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.log.append("Соединение закрыто.")

    def reset_db(self):
        main = self.window()
        if getattr(main, "engine", None) is None:
            QMessageBox.warning(self, "Схема", "Нет подключения к БД.")
            return
        if drop_and_create_schema_sa(main.engine, main.md):
            self.log.append("Схема БД создана: aircraft, flights, passengers, crew, crew_member.")
            main.refresh_all_models()
        else:
            QMessageBox.critical(self, "Схема", "Ошибка при создании схема. См. консоль/лог.")

    def add_demo(self):
        main = self.window()
        if getattr(main, "engine", None) is None:
            QMessageBox.warning(self, "Демо", "Нет подключения к БД.")
            return
        if insert_demo_data_sa(main.engine, main.tables):
            self.log.append("Добавлены демонстрационные данные (INSERT).")
            main.refresh_all_models()
        else:
            QMessageBox.warning(self, "Демо", "Часть данных не добавлена. См. консоль.")
