# styles.py
import os
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QHeaderView

# Текущая тема по умолчанию
_current_theme = "dark"  # можно  "light" или "dark"

def _qss_path_for(theme: str) -> str:
    base = os.path.dirname(__file__)
    fname = "light.qss" if theme == "light" else "style.qss"
    return os.path.join(base, fname)

def _apply_qss(app: QApplication, theme: str) -> None:
    path = _qss_path_for(theme)
    try:
        with open(path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        # если QSS не найден — используем дефолтный стиль (пустой)
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
        # на некоторых системах этот шрифт может отсутствовать — игнорируем
        pass
    _apply_qss(app, _current_theme)

def switch_theme(theme: str) -> None:
    """
    Переключить тему на 'light' или 'dark'.
    Вызывается из SetupWindow.toggle_theme(new_theme).
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
        # скрываем сетку для более компактного вида
        if hasattr(table_widget, "setShowGrid"):
            table_widget.setShowGrid(False)
        # горизонтальный заголовок: подгонять размеры под содержимое
        header = table_widget.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
    except Exception:
        # не критично, если не QTableView или методы отличаются
        pass
