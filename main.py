import sys
import os
from PySide6.QtWidgets import QApplication

# Добавляем пути для импорта
sys.path.append(os.path.join(os.path.dirname(__file__), 'db'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'templates'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'styles'))

from templates.MainWindow import MainWindow
from styles.styles import connect_styles


def main():
    app = QApplication(sys.argv)

    # Применяем стили
    connect_styles(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()