from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QMainWindow,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from services import visit_service
from services import distance_service
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
        self.pending_route = []

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.stores_tab = QWidget()
        self.today_tab = QWidget()

        self.tabs.addTab(self.stores_tab, "Stores")
        self.tabs.addTab(self.today_tab, "Today's Visits")

        self.build_stores_tab()
        self.build_today_tab()

        self.refresh_store_list()
        self.refresh_today_cards()
        self.refresh_today_route_display()

    def build_stores_tab(self):
        main_layout = QVBoxLayout(self.stores_tab)

        title = QLabel("Mileage Tracker")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        subtitle = QLabel("Add stores and track when they were last visited.")
        main_layout.addWidget(subtitle)

        search_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search stores")
        self.search_input.setMinimumHeight(40)
        self.search_input.setStyleSheet("font-size: 16px;")
        self.search_input.textChanged.connect(lambda _text: self.refresh_store_list())
        search_row.addWidget(self.search_input)

        main_layout.addLayout(search_row)

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

        self.store_list = QListWidget()
        self.store_list.setSpacing(6)
        self.store_list.itemDoubleClicked.connect(self.start_edit_store)
        main_layout.addWidget(self.store_list)

    def build_today_tab(self):
        layout = QVBoxLayout(self.today_tab)

        title = QLabel("Today's Visits")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("Click stores below to build today's route.")
        layout.addWidget(subtitle)

        route_header_row = QHBoxLayout()

        route_title = QLabel("Today's Route")
        route_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        route_header_row.addWidget(route_title)

        route_header_row.addStretch()

        self.route_total_label = QLabel("Total miles: 0.00")
        self.route_total_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        route_header_row.addWidget(self.route_total_label)

        
        save_route_button = QPushButton("Save Route")
        save_route_button.setMinimumSize(140, 40)
        save_route_button.clicked.connect(self.save_today_route)
        route_header_row.addWidget(save_route_button)

        self.delete_last_stop_button = QPushButton("Delete Last Stop")
        self.delete_last_stop_button.setMinimumSize(160, 40)
        self.delete_last_stop_button.clicked.connect(self.delete_last_stop)
        route_header_row.addWidget(self.delete_last_stop_button)

        clear_route_button = QPushButton("Clear Route")
        clear_route_button.setMinimumSize(140, 40)
        clear_route_button.clicked.connect(self.clear_today_route)
        route_header_row.addWidget(clear_route_button)
        layout.addLayout(route_header_row)

        self.route_scroll = QScrollArea()
        self.route_scroll.setWidgetResizable(True)
        self.route_scroll.setFixedHeight(90)
        self.route_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.route_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.route_container = QWidget()
        self.route_layout = QHBoxLayout(self.route_container)
        self.route_layout.setSpacing(10)
        self.route_layout.setContentsMargins(0, 0, 0, 0)

        self.route_scroll.setWidget(self.route_container)
        layout.addWidget(self.route_scroll)

        cards_title = QLabel("Stores")
        cards_title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(cards_title)

        self.today_cards_scroll = QScrollArea()
        self.today_cards_scroll.setWidgetResizable(True)

        self.today_cards_container = QWidget()
        self.today_cards_grid = QGridLayout(self.today_cards_container)
        self.today_cards_grid.setHorizontalSpacing(12)
        self.today_cards_grid.setVerticalSpacing(12)
        self.today_cards_grid.setContentsMargins(0, 0, 0, 0)
        self.today_cards_grid.setColumnStretch(0, 1)
        self.today_cards_grid.setColumnStretch(1, 1)

        self.today_cards_scroll.setWidget(self.today_cards_container)
        layout.addWidget(self.today_cards_scroll)

    def save_today_route(self):
        if not self.pending_route:
            QMessageBox.information(self, "Save Route", "There is no route to save.")
            return

        for index, step in enumerate(self.pending_route, start=1):
            visit_service.add_visit(
                store_id=step["store_id"],
                sequence_number=index,
                miles_from_previous=step["miles_from_previous"],
            )

        QMessageBox.information(self, "Save Route", "Route saved successfully.")
        self.clear_today_route()
        self.refresh_store_list()
        self.refresh_today_cards()

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

    def refresh_today_cards(self):
        while self.today_cards_grid.count():
            item = self.today_cards_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        stores = store_service.get_all_stores()

        for index, store in enumerate(stores):
            row = index // 2
            col = index % 2

            card = QPushButton(store["name"])
            card.setMinimumHeight(90)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            card.setStyleSheet(
                """
                QPushButton {
                    font-size: 18px;
                    font-weight: bold;
                    text-align: left;
                    padding: 12px 16px;
                    border: 1px solid #ccc;
                    border-radius: 12px;
                    background-color: #f7f7f7;
                }
                QPushButton:hover {
                    background-color: #ececec;
                }
                QPushButton:pressed {
                    background-color: #dddddd;
                }
                """
            )
            card.clicked.connect(
                lambda checked=False, store_id=store["id"]: self.add_to_today_route(store_id)
            )

            self.today_cards_grid.addWidget(card, row, col)

    def refresh_today_route_display(self):
        while self.route_layout.count():
            item = self.route_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.delete_last_stop_button.setEnabled(bool(self.pending_route))

        total_miles = 0.0

        if not self.pending_route:
            self.route_total_label.setText("Total miles: 0.00")
            empty_label = QLabel("No stops yet")
            empty_label.setStyleSheet(
                """
                QLabel {
                    font-size: 16px;
                    color: #666;
                    padding: 10px 16px;
                    border: 1px dashed #bbb;
                    border-radius: 10px;
                    background-color: #fafafa;
                }
                """
            )
            if hasattr(self, "delete_last_stop_button"):
                self.delete_last_stop_button.setEnabled(bool(self.pending_route))
            self.route_layout.addWidget(empty_label)
            self.route_layout.addStretch()
            return

        for index, step in enumerate(self.pending_route):
            store = store_service.get_store_by_id(step["store_id"])
            if store is None:
                continue

            if step["miles_from_previous"] is not None:
                total_miles += step["miles_from_previous"]

            chip = QLabel(f"{index + 1}. {store['name']}")
            chip.setMinimumHeight(44)
            chip.setStyleSheet(
                """
                QLabel {
                    font-size: 16px;
                    font-weight: bold;
                    padding: 10px 14px;
                    border: 1px solid #ccc;
                    border-radius: 10px;
                    background-color: #f7f7f7;
                }
                """
            )
            chip.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            chip.adjustSize()
            self.route_layout.addWidget(chip)

        self.route_total_label.setText(f"Total miles: {total_miles:.2f}")
        self.route_layout.addStretch()

    def add_to_today_route(self, store_id: int):
        if not self.pending_route:
            self.pending_route.append(
                {"store_id": store_id, "miles_from_previous": None}
            )
            self.refresh_today_route_display()
            return

        previous_store_id = self.pending_route[-1]["store_id"]
        distance = distance_service.get_distance(previous_store_id, store_id)

        if distance is None:
            miles, ok = QInputDialog.getDouble(
                self,
                "Missing distance",
                "No recorded distance exists between these locations.\nEnter miles:",
                0.0,
                0.0,
                10000.0,
                2,
            )
            if not ok:
                return

            distance_service.save_distance(previous_store_id, store_id, miles)
            distance = miles

        self.pending_route.append(
            {"store_id": store_id, "miles_from_previous": distance}
        )
        self.refresh_today_route_display()

    def clear_today_route(self):
        self.pending_route = []
        self.refresh_today_route_display()

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
            self.refresh_today_cards()
            self.refresh_today_route_display()
            return

        try:
            store_service.update_store_name(store_id, new_name)
        except ValueError as exc:
            QMessageBox.warning(self, "Could not rename store", str(exc))
            self.refresh_store_list()
            self.refresh_today_cards()
            self.refresh_today_route_display()
            return

        self.refresh_store_list()
        self.refresh_today_cards()
        self.refresh_today_route_display()

    def add_store(self):
        try:
            store_service.add_store(self.name_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Could not add store", str(exc))
            return

        self.name_input.clear()
        self.refresh_store_list()
        self.refresh_today_cards()
        self.name_input.setFocus()

    def delete_last_stop(self):
        if not self.pending_route:
            QMessageBox.information(self, "Delete Last Stop", "There is no stop to delete.")
            return

        self.pending_route.pop()
        self.refresh_today_route_display()

    def delete_store(self, store_id: int, store_name: str):
        confirm = QMessageBox.question(
            self,
            "Delete Store",
            f"Delete '{store_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        store_service.delete_store(store_id)
        self.pending_route = [
            step for step in self.pending_route if step["store_id"] != store_id
        ]
        self.refresh_store_list()
        self.refresh_today_cards()
        self.refresh_today_route_display()