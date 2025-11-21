# ===== PySide6 =====
from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QLineEdit, QMessageBox,
    QComboBox, QTableView, QHeaderView
)
from styles.styles import apply_compact_table_view

# ===== SQLAlchemy =====
from sqlalchemy import (
    insert, delete
)

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# ===== Files =====
from db.models import SATableModel
from templates.tabs.AddWindow import AddWindow
from templates.tabs.BaseTab import BaseTab
from templates.tabs.EditWindow import EditWindow
from templates.tabs.ReadWindow import ReadWindow

# -------------------------------
# Вкладка «Члены Экипажа»
# -------------------------------
class CrewMembersTab(BaseTab):
    def __init__(self, engine, tables, parent=None):
        super().__init__(engine, tables, "crew_member", parent)
        self.model = SATableModel(engine, self.tables["crew_member"], self)
        self.update_model()
        self.update_ui_for_mode()

    def create_add_window(self):
        return CrewMembersAddWindow(self.engine, self.tables, self.table, self)


class CrewMembersReadWindow(ReadWindow):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(engine, tables, table, parent)
        self.setup_crew_members_ui()

    def setup_crew_members_ui(self):
        from db.models import SATableModel
        self.model = SATableModel(self.engine, self.tables[self.table], self)

        self.read_table.setModel(self.model)
        self.read_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.read_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        apply_compact_table_view(self.read_table)
        self.read_table.setSortingEnabled(True)


class CrewMembersEditWindow(EditWindow):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(engine, tables, table, parent)
        self.load_table_structure()


class CrewMembersAddWindow(AddWindow):
    def __init__(self, engine, tables, table, parent=None):
        super().__init__(engine, tables, table, parent)
        self.model = SATableModel(self.engine, self.tables[self.table], self)
        self.setup_crew_members_ui()

    def setup_crew_members_ui(self):
        from db.models import SATableModel
        self.model = SATableModel(self.engine, self.tables[self.table], self)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.add_table.setModel(self.proxy_model)
        self.add_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.add_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        apply_compact_table_view(self.add_table)
        self.add_table.setSortingEnabled(True)

        header = self.add_table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.proxy_model.sort(0, Qt.SortOrder.AscendingOrder)

        header.sectionClicked.connect(self.on_header_clicked)

    def on_header_clicked(self, logical_index):
        current_order = self.proxy_model.sortOrder()
        new_order = Qt.SortOrder.DescendingOrder if current_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        self.proxy_model.sort(logical_index, new_order)

    def connect_buttons(self):
        self.add_record_btn.clicked.connect(self.add_crew_member)
        self.clear_form_btn.clicked.connect(self.clear_form)
        self.delete_record_btn.clicked.connect(self.delete_selected)

    def add_crew_member(self):
        # Получаем данные из автоматически созданной формы
        form_data = self.get_form_data()

        # Валидация данных
        job_position = form_data.get('job_position', '')

        if not job_position:
            QMessageBox.warning(self, "Ввод", "Должность обязательна")
            return

        if len(job_position) < 2:
            QMessageBox.warning(self, "Ввод", "Должность должна содержать минимум 2 символа")
            return

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.tables["crew_member"]).values(**form_data))
            self.model.refresh()
            self.clear_form()

            parent_window = self.window()
            if hasattr(parent_window, 'refresh_combos'):
                parent_window.refresh_combos()

        except IntegrityError as e:
            if "foreign key constraint" in str(e.orig).lower():
                QMessageBox.critical(self, "Ошибка INSERT", "Ошибка внешнего ключа (неверный ID экипажа)")
            else:
                QMessageBox.critical(self, "Ошибка INSERT (CHECK constraint)", str(e.orig))
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка INSERT", str(e))

    def delete_selected(self):
        idx = self.add_table.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Удаление", "Выберите члена экипажа")
            return

        source_index = self.proxy_model.mapToSource(idx)
        member_id = self.model.pk_value_at(source_index.row())

        try:
            with self.engine.begin() as conn:
                conn.execute(delete(self.tables["crew_member"]).where(
                    self.tables["crew_member"].c.member_id == member_id
                ))
            self.model.refresh()

            parent_window = self.window()
            if hasattr(parent_window, 'refresh_combos'):
                parent_window.refresh_combos()

        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))