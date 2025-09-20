from PySide6.QtGui import QFont
import os


def connect_styles(app):
    # Загрузка шрифтов
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Загрузка стилей
    try:
        style_path = os.path.join(os.path.dirname(__file__), "style.qss")
        with open(style_path, "r", encoding="utf-8") as f:
            style = f.read()
            app.setStyleSheet(style)
    except FileNotFoundError:
        print("Файл стилей не найден, используется стандартный стиль")
    except Exception as e:
        print(f"Ошибка загрузки стилей: {e}")