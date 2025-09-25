# ===== PySide6 =====
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
    QComboBox, QTextEdit, QGroupBox
)


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



# -------------------------------
# Вкладка «Подключение и схема БД»
# -------------------------------
class SetupTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log = QTextEdit();
        self.log.setReadOnly(True)

        self.driver_cb = QComboBox()
        self.driver_cb.addItem("psycopg2 (binary)", "psycopg2")
        self.driver_cb.addItem("psycopg (v3, binary)", "psycopg")
        self.driver_cb.addItem("pg8000 (pure Python)", "pg8000")

        self.host_edit = QLineEdit("localhost")
        self.port_edit = QLineEdit("5432")
        self.db_edit = QLineEdit("airport")
        self.user_edit = QLineEdit("postgres")
        self.pw_edit = QLineEdit("");
        self.pw_edit.setEchoMode(QLineEdit.Password)
        self.ssl_edit = QLineEdit("prefer")

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

        self.connect_btn = QPushButton("Подключиться")
        self.connect_btn.clicked.connect(self.do_connect)

        self.disconnect_btn = QPushButton("Отключиться")
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.clicked.connect(self.do_disconnect)

        self.create_btn = QPushButton("Сбросить и создать БД (CREATE)")
        self.create_btn.setEnabled(False)
        self.create_btn.clicked.connect(self.reset_db)

        self.demo_btn = QPushButton("Добавить демо-данные (INSERT)")
        self.demo_btn.setEnabled(False)
        self.demo_btn.clicked.connect(self.add_demo)

        top_btns = QHBoxLayout()
        top_btns.addWidget(self.connect_btn)
        top_btns.addWidget(self.disconnect_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(conn_box)
        layout.addLayout(top_btns)
        layout.addWidget(self.create_btn)
        layout.addWidget(self.demo_btn)
        layout.addWidget(QLabel("Лог:"))
        layout.addWidget(self.log)

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
        main = self.window()  # <-- было parent().parent()
        # если уже подключены — просим отключиться
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
            main.ensure_data_tabs()
        except SQLAlchemyError as e:
            self.log.append(f"Ошибка подключения: {e}")

    def do_disconnect(self):
        main = self.window()  # <-- было parent().parent()
        main.disconnect_db()
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.create_btn.setEnabled(False)
        self.demo_btn.setEnabled(False)
        self.log.append("Соединение закрыто.")

    def reset_db(self):
        main = self.window()  # <-- было parent().parent()
        if getattr(main, "engine", None) is None:
            QMessageBox.warning(self, "Схема", "Нет подключения к БД.")
            return
        if drop_and_create_schema_sa(main.engine, main.md):
            self.log.append("Схема БД создана: aircraft, flights, passengers, crew, crew_member.")
            main.refresh_all_models()
            main.refresh_combos()
        else:
            QMessageBox.critical(self, "Схема", "Ошибка при создании схемы. См. консоль/лог.")

    def add_demo(self):
        main = self.window()  # <-- было parent().parent()
        if getattr(main, "engine", None) is None:
            QMessageBox.warning(self, "Демо", "Нет подключения к БД.")
            return
        if insert_demo_data_sa(main.engine, main.tables):
            self.log.append("Добавлены демонстрационные данные (INSERT).")
            main.refresh_all_models()
            main.refresh_combos()
        else:
            QMessageBox.warning(self, "Демо", "Часть данных не добавлена. См. консоль.")