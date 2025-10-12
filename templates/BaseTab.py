from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLineEdit
from PySide6.QtCore import QSortFilterProxyModel, Qt
from templates.modes import AppMode


class BaseTab(QWidget):
    def __init__(self, engine, tables, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.t = tables
        self.current_mode = AppMode.READ

        # Панель инструментов для всех режимов
        self.tool_panel = QWidget()
        self.tool_layout = QHBoxLayout(self.tool_panel)
        self.tool_layout.setContentsMargins(0, 0, 0, 0)

        # Элементы для режима чтения
        self.sort_combo = QComboBox()
        self.register_combo = QComboBox()
        self.join_btn = QPushButton("JOIN")
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Фильтр...")

        # Элементы для режима редактирования
        self.add_column_btn = QPushButton("Добавить столбец")
        self.change_type_btn = QPushButton("Изменить тип данных")
        self.add_relation_btn = QPushButton("Добавить связи")
        self.edit_btn = QPushButton("Редактировать запись")
        self.save_edit_btn = QPushButton("Сохранить изменения")
        self.cancel_edit_btn = QPushButton("Отменить редактирование")

        # Элементы для режима добавления
        self.add_record_btn = QPushButton("Добавить запись")
        self.clear_form_btn = QPushButton("Очистить форму")
        self.delete_record_btn = QPushButton("Удалить запись")

        self.read_widgets = QWidget()
        self.read_layout = QHBoxLayout(self.read_widgets)
        self.read_layout.setContentsMargins(0, 0, 0, 0)

        self.edit_widgets = QWidget()
        self.edit_layout = QHBoxLayout(self.edit_widgets)
        self.edit_layout.setContentsMargins(0, 0, 0, 0)

        self.add_widgets = QWidget()
        self.add_layout = QHBoxLayout(self.add_widgets)
        self.add_layout.setContentsMargins(0, 0, 0, 0)

        self.setup_ui()
        self.setup_tool_widgets()

    def setup_ui(self):
        self.sort_combo.addItems(["По ID", "По имени", "По дате", "По рейсу"])
        self.register_combo.addItems(["Оригинал", "Верхний регистр", "Нижний регистр"])

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.tool_panel)

    def setup_tool_widgets(self):
        self.read_layout.addWidget(self.sort_combo)
        self.read_layout.addWidget(self.register_combo)
        self.read_layout.addWidget(self.join_btn)
        self.read_layout.addWidget(self.filter_edit)
        self.read_layout.addStretch()

        self.edit_layout.addWidget(self.add_column_btn)
        self.edit_layout.addWidget(self.change_type_btn)
        self.edit_layout.addWidget(self.add_relation_btn)
        self.edit_layout.addWidget(self.edit_btn)
        self.edit_layout.addWidget(self.save_edit_btn)
        self.edit_layout.addWidget(self.cancel_edit_btn)
        self.edit_layout.addStretch()

        self.add_layout.addWidget(self.add_record_btn)
        self.add_layout.addWidget(self.clear_form_btn)
        self.add_layout.addWidget(self.delete_record_btn)
        self.add_layout.addStretch()

    def set_mode(self, mode: AppMode):
        self.current_mode = mode
        self.update_ui_for_mode()

    def update_ui_for_mode(self):
        for i in reversed(range(self.tool_layout.count())):
            widget = self.tool_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if self.current_mode == AppMode.READ:
            self.tool_layout.addWidget(self.read_widgets)
        elif self.current_mode == AppMode.EDIT:
            self.tool_layout.addWidget(self.edit_widgets)
        elif self.current_mode == AppMode.ADD:
            self.tool_layout.addWidget(self.add_widgets)

        self.tool_panel.setVisible(self.current_mode in [AppMode.READ, AppMode.EDIT, AppMode.ADD])