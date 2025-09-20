# -*- coding: utf-8 -*-
"""
PySide6 + SQLAlchemy (PostgreSQL) — стабильная версия:
- Без QtSql / PyQt.
- QAbstractTableModel с beginResetModel/endResetModel.
- Кнопки: Подключиться/Отключиться, CREATE schema, INSERT demo.
- Переключатель драйвера: psycopg2 / psycopg (v3) / pg8000 (pure Python).
- Вместо parent().parent() используем self.window() для доступа к MainWindow.
"""


# ===== Base =====
import sys
import faulthandler

faulthandler.enable()


# ===== PySide6 =====
from PySide6.QtWidgets import QApplication


# ===== Files =====
from templates.MainWindow import MainWindow





# -------------------------------
# Точка входа
# -------------------------------
def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
