from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import QAbstractItemView
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QMainWindow,
    QWidget,
    QVBoxLayout,
)

from services import store_service


class StoreNameEditor(QLineEdit):
    def __init__(self, store_id: int, save_callback, initial_text: str):
        super().__init__(initial_text)
        self.store_id = store_id
        self.save_callback = save_callback
        self._committed = False
        self._commit_scheduled = False

        self.setMinimumHeight(40)
        self.setStyleSheet("font-size: 18px;")

        self.returnPressed.connect(self.schedule_commit)

        QTimer.singleShot(0, self.setFocus)
        QTimer.singleShot(0, self.selectAll)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.schedule_commit()

    def schedule_commit(self):
        if self._commit_scheduled or self._committed:
            return

        self._commit_scheduled = True
        QTimer.singleShot(0, self.commit)

    def commit(self):
        if self._committed:
            return

        self._committed = True
        self.save_callback(self.store_id, self.text())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mileage Tracker")
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)

        self.editing_store_id = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        title = QLabel("Mileage Tracker")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        subtitle = QLabel("Add stores and track when they were last visited.")
        main_layout.addWidget(subtitle)

        form_layout = QHBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setMinimumHeight(60)
        self.name_input.setStyleSheet("font-size: 16px;")
        self.name_input.setPlaceholderText("Store name")
        self.name_input.returnPressed.connect(self.add_store)
        form_layout.addWidget(self.name_input)

        self.add_button = QPushButton("Add Store")
        self.add_button.clicked.connect(self.add_store)
        self.add_button.setMinimumSize(180, 60)
        self.add_button.setStyleSheet("font-size: 16px;")
        form_layout.addWidget(self.add_button)

        main_layout.addLayout(form_layout)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search stores")
        self.search_input.setMinimumHeight(40)
        self.search_input.setStyleSheet("font-size: 16px;")
        self.search_input.textChanged.connect(self.refresh_store_list)
        main_layout.addWidget(self.search_input)

        self.store_list = QListWidget()
        self.store_list.itemDoubleClicked.connect(self.start_edit_store)
        main_layout.addWidget(self.store_list)

        self.refresh_store_list()

    def refresh_store_list(self, editing_store_id=None):
        self.editing_store_id = editing_store_id
        current_scroll = self.store_list.verticalScrollBar().value()
        search_text = self.search_input.text().strip().lower()

        self.store_list.clear()

        stores = store_service.get_all_stores()
        editing_item = None

        for store in stores:
            if search_text and search_text not in store["name"].lower():
                continue

            item = QListWidgetItem()
            item.setData(Qt.UserRole, store["id"])

            if store["id"] == self.editing_store_id:
                row_widget = self.build_edit_row(store)
                editing_item = item
            else:
                row_widget = self.build_display_row(store)

            item.setSizeHint(row_widget.sizeHint())
            self.store_list.addItem(item)
            self.store_list.setItemWidget(item, row_widget)

        if editing_item is not None:
            QTimer.singleShot(
                0,
                lambda item=editing_item: self.store_list.scrollToItem(
                    item, QAbstractItemView.PositionAtCenter
                ),
            )
        else:
            QTimer.singleShot(
                0,
                lambda value=current_scroll: self.store_list.verticalScrollBar().setValue(value),
            )

    def build_display_row(self, store):
        row_widget = QWidget()
        row_layout = QVBoxLayout(row_widget)
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        name_label = QLabel(store["name"])
        name_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        top_row.addWidget(name_label)
        top_row.addStretch()

        delete_button = QPushButton("Delete")
        delete_button.setMinimumSize(100, 40)
        delete_button.clicked.connect(
            lambda checked=False, store_id=store["id"], store_name=store["name"]: self.delete_store(store_id, store_name)
        )
        top_row.addWidget(delete_button)

        row_layout.addLayout(top_row)

        if store["last_visited"]:
            last_visited_text = f"Last visited: {store['last_visited']}"
        else:
            last_visited_text = "Last visited: never"

        last_visited_label = QLabel(last_visited_text)
        last_visited_label.setStyleSheet("font-size: 14px; color: #666;")
        row_layout.addWidget(last_visited_label)

        return row_widget

    def build_edit_row(self, store):
        row_widget = QWidget()
        row_layout = QVBoxLayout(row_widget)
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        name_edit = StoreNameEditor(store["id"], self.save_edit, store["name"])
        top_row.addWidget(name_edit)

        delete_button = QPushButton("Delete")
        delete_button.setMinimumSize(100, 40)
        delete_button.clicked.connect(
            lambda checked=False, store_id=store["id"], store_name=store["name"]: self.delete_store(store_id, store_name)
        )
        top_row.addWidget(delete_button)

        row_layout.addLayout(top_row)

        if store["last_visited"]:
            last_visited_text = f"Last visited: {store['last_visited']}"
        else:
            last_visited_text = "Last visited: never"

        last_visited_label = QLabel(last_visited_text)
        last_visited_label.setStyleSheet("font-size: 14px; color: #666;")
        row_layout.addWidget(last_visited_label)

        return row_widget

    def start_edit_store(self, item: QListWidgetItem):
        store_id = item.data(Qt.UserRole)
        self.refresh_store_list(editing_store_id=store_id)

    def save_edit(self, store_id: int, new_name: str):
        new_name = new_name.strip()

        if not new_name:
            self.refresh_store_list()
            return

        try:
            store_service.update_store_name(store_id, new_name)
        except ValueError as exc:
            QMessageBox.warning(self, "Could not rename store", str(exc))
            self.refresh_store_list()
            return

        self.refresh_store_list()

    def add_store(self):
        try:
            store_service.add_store(self.name_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Could not add store", str(exc))
            return

        self.name_input.clear()
        self.refresh_store_list()
        self.name_input.setFocus()

    def delete_store(self, store_id: int, store_name: str):
        confirm = QMessageBox.question(
            self,
            "Delete Store",
            f"Delete '{store_name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if confirm != QMessageBox.Yes:
            return

        store_service.delete_store(store_id)
        self.refresh_store_list()