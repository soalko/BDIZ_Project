# styles.py
import os
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QHeaderView

# Текущая тема по умолчанию
_current_theme = "dark"  # можно  "light" или "dark"


def _qss_path_for(theme: str) -> str:
    base = os.path.dirname(__file__)
    fname = "light.qss" if theme == "light" else "dark.qss"
    return os.path.join(base, fname)


def _layout_qss_path() -> str:
    """Путь к файлу layout.qss"""
    base = os.path.dirname(__file__)
    return os.path.join(base, "layout.qss")


def _apply_qss(app: QApplication, theme: str) -> None:
    path = _qss_path_for(theme)
    layout_path = _layout_qss_path()

    try:
        # Загружаем layout.qss (отступы, размеры, скругления)
        layout_style = ""
        if os.path.exists(layout_path):
            with open(layout_path, "r", encoding="utf-8") as f:
                layout_style = f.read()
        else:
            print(f"[styles] layout.qss not found: {layout_path}")

        # Загружаем тему (colors)
        theme_style = ""
        with open(path, "r", encoding="utf-8") as f:
            theme_style = f.read()

        # Объединяем: сначала layout, потом theme
        combined_style = layout_style + "\n" + theme_style
        app.setStyleSheet(combined_style)

    except FileNotFoundError:
        print(f"[styles] QSS not found: {path}. Using default style.")
        app.setStyleSheet("")
    except Exception as e:
        print(f"[styles] Error loading QSS '{path}': {e}")


def connect_styles(app: QApplication) -> None:
    """
    Устанавливает шрифт и применяет текущую тему (QSS).
    Вызывается из main: connect_styles(app)
    """
    global _current_theme
    try:
        font = QFont("Segoe UI", 10)
        app.setFont(font)
    except Exception:
        pass
    _apply_qss(app, _current_theme)


def switch_theme(theme: str) -> None:
    """
    Переключить тему на 'light' или 'dark'.
    """
    global _current_theme
    if not isinstance(theme, str):
        return
    theme = theme.lower()
    if theme not in ("light", "dark"):
        raise ValueError("theme must be 'light' or 'dark'")
    _current_theme = theme
    app = QApplication.instance()
    if app is not None:
        _apply_qss(app, _current_theme)


def get_current_theme() -> str:
    """Вернуть текущую тему: 'light' или 'dark'."""
    return _current_theme


def apply_compact_table_view(table_widget) -> None:
    """
    Небольшая "заглушка" для компактного оформления таблиц.
    Можно расширить по желанию.
    """
    try:
        table_widget.setAlternatingRowColors(True)
        if hasattr(table_widget, "setShowGrid"):
            table_widget.setShowGrid(False)
        header = table_widget.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
    except Exception:
        pass