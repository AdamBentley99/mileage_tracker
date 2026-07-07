from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QSpinBox,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QMainWindow,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from datetime import datetime, date, timedelta
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

class StoreCardWidget(QWidget):
    def __init__(self, store_id: int, double_click_callback=None):
        super().__init__()
        self.store_id = store_id
        self.double_click_callback = double_click_callback
        self.setObjectName("storeCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setCursor(Qt.PointingHandCursor)

    def mouseDoubleClickEvent(self, event):
        if callable(self.double_click_callback):
            self.double_click_callback(self.store_id)
        super().mouseDoubleClickEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mileage Tracker")
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)

        self.editing_store_id = None
        self.pending_route = []
        self.route_manual_adjustment = 0.0

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                min-width: 120px;
                min-height: 30px;
                padding: 8px 20px;
                font-size: 16px;
                font-weight: 600;
                border: 1px solid #c9d6ea;
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                background: #edf2fb;
                color: #374151;
            }

            QTabBar::tab:selected {
                background: #1f5fd6;
                color: white;
            }

            QTabBar::tab:hover:!selected {
                background: #dce9ff;
            }

            QTabWidget::pane {
                border: 1px solid #c9d6ea;
                top: -1px;
            }
            """)
        self.setCentralWidget(self.tabs)

        self.stores_tab = QWidget()
        self.today_tab = QWidget()

        self.tabs.addTab(self.today_tab, "Today's Visits")
        self.tabs.addTab(self.stores_tab, "Stores")

        self.build_stores_tab()
        self.build_today_tab()

        self.refresh_store_list()
        self.refresh_today_cards()
        self.refresh_today_route_display()

    def build_stores_tab(self):
        main_layout = QVBoxLayout(self.stores_tab)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        title = QLabel("Mileage Tracker")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        subtitle = QLabel("Add stores and track when they were last visited.")
        main_layout.addWidget(subtitle)

        search_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search stores")
        self.search_input.setMinimumHeight(40)
        self.search_input.setStyleSheet(
            """
            QLineEdit {
                font-size: 16px;
                padding: 10px 14px;
                border: 1px solid #d6dbe6;
                border-radius: 10px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #2f6fdd;
            }
            """
        )
        self.search_input.textChanged.connect(lambda _text: self.refresh_store_list())
        search_row.addWidget(self.search_input)

        main_layout.addLayout(search_row)

        form_layout = QHBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setMinimumHeight(60)
        self.name_input.setStyleSheet(
            """
            QLineEdit {
                font-size: 16px;
                padding: 10px 14px;
                border: 1px solid #d6dbe6;
                border-radius: 10px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #2f6fdd;
            }
            """
        )
        self.name_input.setPlaceholderText("Store name")
        self.name_input.returnPressed.connect(self.add_store)
        form_layout.addWidget(self.name_input)

        self.add_button = QPushButton("Add Store")
        self.add_button.clicked.connect(self.add_store)
        self.add_button.setMinimumSize(180, 60)
        self.add_button.setStyleSheet(
            """
            QPushButton {
                font-size: 16px;
                font-weight: 600;
                color: white;
                background-color: #1f5fd6;
                border: none;
                border-radius: 10px;
                padding: 10px 18px;
            }
            QPushButton:hover {
                background-color: #164db0;
            }
            QPushButton:pressed {
                background-color: #133f91;
            }
            """
        )
        form_layout.addWidget(self.add_button)

        main_layout.addLayout(form_layout)

        self.store_scroll = QScrollArea()
        self.store_scroll.setWidgetResizable(True)
        self.store_scroll.setFrameShape(QScrollArea.NoFrame)
        self.store_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.store_container = QWidget()
        self.store_container.setStyleSheet("background: transparent;")
        self.store_grid = QGridLayout(self.store_container)
        self.store_grid.setHorizontalSpacing(16)
        self.store_grid.setVerticalSpacing(16)
        self.store_grid.setContentsMargins(2, 2, 2, 2)
        self.store_grid.setColumnStretch(0, 1)
        self.store_grid.setColumnStretch(1, 1)
        self.store_grid.setColumnStretch(2, 1)
        self.store_grid.setColumnStretch(3, 1)

        self.store_scroll.setWidget(self.store_container)
        main_layout.addWidget(self.store_scroll)

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

        adjustment_row = QHBoxLayout()

        adjust_label = QLabel("Adjust")
        adjust_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        adjustment_row.addWidget(adjust_label)

        self.miles_adjustment_spin = QSpinBox()
        self.miles_adjustment_spin.setRange(2, 100)
        self.miles_adjustment_spin.setValue(2)
        self.miles_adjustment_spin.setSingleStep(2)
        self.miles_adjustment_spin.setFixedSize(100, 40)
        self.miles_adjustment_spin.setStyleSheet("font-size: 16px;")
        adjustment_row.addWidget(self.miles_adjustment_spin)

        plus_button = QPushButton("+")
        plus_button.setMinimumSize(50, 40)
        plus_button.clicked.connect(lambda: self.adjust_route_total(1))
        adjustment_row.addWidget(plus_button)

        minus_button = QPushButton("-")
        minus_button.setMinimumSize(50, 40)
        minus_button.clicked.connect(lambda: self.adjust_route_total(-1))
        adjustment_row.addWidget(minus_button)

        route_header_row.addLayout(adjustment_row)

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
        self.today_cards_grid.setColumnStretch(2, 1)
        self.today_cards_grid.setColumnStretch(3, 1)

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

    def start_edit_store(self, store_id: int):
        self.refresh_store_list(editing_store_id=store_id)

    def refresh_store_list(self, editing_store_id=None):
        self.editing_store_id = editing_store_id
        current_scroll = self.store_scroll.verticalScrollBar().value()
        search_text = self.search_input.text().strip().lower()

        while self.store_grid.count():
            item = self.store_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        stores = store_service.get_all_stores()
        editing_widget = None

        visible_index = 0
        for store in stores:
            if search_text and search_text not in store["name"].lower():
                continue

            if store["id"] == self.editing_store_id:
                row_widget = self.build_edit_row(store)
                editing_widget = row_widget
            else:
                row_widget = self.build_display_row(store)

            row = visible_index // 4
            col = visible_index % 4
            visible_index += 1

            self.store_grid.addWidget(row_widget, row, col)

        if editing_widget is not None:
            QTimer.singleShot(
                0,
                lambda widget=editing_widget: self.store_scroll.ensureWidgetVisible(widget),
            )
        else:
            QTimer.singleShot(
                0,
                lambda value=current_scroll: self.store_scroll.verticalScrollBar().setValue(value),
            )
        
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

    def mark_store_visited_today(self, store_id: int):
        store_service.update_store_last_visited(store_id, date.today().isoformat())
        self.refresh_store_list(self.editing_store_id)
        self.refresh_today_cards()

    def mark_store_visited_days_ago(self, store_id: int, store_name: str):
        days_ago, ok = QInputDialog.getInt(
            self,
            "Set last visited",
            f"How many days ago was '{store_name}' visited?",
            1,
            0,
            36500,
            1,
        )
        if not ok:
            return

        visited_date = date.today() - timedelta(days=days_ago)
        store_service.update_store_last_visited(store_id, visited_date.isoformat())
        self.refresh_store_list(self.editing_store_id)
        self.refresh_today_cards()

    def adjust_route_total(self, direction: int):
        amount = self.miles_adjustment_spin.value()
        adjustment = amount * direction
        self.route_manual_adjustment += adjustment
        self.refresh_today_route_display()

    def get_base_route_total(self) -> float:
        total = 0.0
        for step in self.pending_route:
            if step["miles_from_previous"] is not None:
                total += step["miles_from_previous"]
        return total

    def get_route_total(self) -> float:
        return self.get_base_route_total() + self.route_manual_adjustment

    def refresh_today_cards(self):
        while self.today_cards_grid.count():
            item = self.today_cards_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        stores = store_service.get_all_stores()

        for index, store in enumerate(stores):
            row = index // 4
            col = index % 4

            card = QPushButton(store["name"])
            card.setMinimumHeight(90)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            card.setStyleSheet(
                """
                QPushButton {
                    font-size: 18px;
                    font-weight: 700;
                    text-align: left;
                    padding: 14px 18px;
                    border: 2px solid #3f79e0;
                    border-radius: 14px;
                    background-color: #eef5ff;
                    color: #1F2937;
                }

                QPushButton:hover {
                    background-color: #E8F1FF;
                    border: 2px solid #8FB9FF;
                }

                QPushButton:pressed {
                    background-color: #DCEAFF;
                    border: 2px solid #6FA0F5;
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
            self.route_layout.addWidget(empty_label)
            self.route_layout.addStretch()
            return

        total_miles = self.get_base_route_total() + self.route_manual_adjustment
        self.route_total_label.setText(f"Total miles: {total_miles:.2f}")

        for index, step in enumerate(self.pending_route):
            store = store_service.get_store_by_id(step["store_id"])
            if store is None:
                continue

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
        self.route_manual_adjustment = 0.0
        self.refresh_today_route_display()

    def delete_last_stop(self):
        if not self.pending_route:
            QMessageBox.information(self, "Delete Last Stop", "There is no stop to delete.")
            return

        self.pending_route.pop()
        self.refresh_today_route_display()

    def build_display_row(self, store):
        row_widget = StoreCardWidget(store["id"], self.start_edit_store)
        row_widget.setObjectName("storeCard")
        row_widget.setMinimumHeight(185)
        row_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row_widget.setStyleSheet(
            """
            QWidget#storeCard {
                background-color: #eef5ff;
                border: 2px solid #3f79e0;
                border-radius: 14px;
            }
            QWidget#storeCard:hover {
                background-color: #e3efff;
                border: 2px solid #2f6fdd;
            }
            """
        )

        row_layout = QVBoxLayout(row_widget)
        row_layout.setContentsMargins(14, 14, 14, 14)
        row_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        name_label = QLabel(store["name"])
        name_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #111827;")
        name_label.setWordWrap(True)
        top_row.addWidget(name_label)
        top_row.addStretch()

        delete_button = QPushButton("Delete")
        delete_button.setMinimumHeight(38)
        delete_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        delete_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 14px;
                border-radius: 10px;
                border: 1px solid #d1d5db;
                background-color: #ffffff;
                color: #1f2937;
            }
            QPushButton:hover {
                background-color: #f8fafc;
            }
            """
        )
        delete_button.clicked.connect(
            lambda checked=False, store_id=store["id"], store_name=store["name"]: self.delete_store(store_id, store_name)
        )
        top_row.addWidget(delete_button)

        row_layout.addLayout(top_row)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        visited_today_button = QPushButton("Visited today")
        visited_today_button.setMinimumHeight(40)
        visited_today_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        visited_today_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 12px;
                border-radius: 10px;
                border: 1px solid #1f5fd6;
                background-color: #1f5fd6;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #164db0;
                border-color: #164db0;
            }
            QPushButton:pressed {
                background-color: #133f91;
                border-color: #133f91;
            }
            """
        )
        visited_today_button.clicked.connect(
            lambda checked=False, store_id=store["id"]: self.mark_store_visited_today(store_id)
        )
        button_row.addWidget(visited_today_button)

        visited_days_ago_button = QPushButton("Visited # days ago")
        visited_days_ago_button.setMinimumHeight(40)
        visited_days_ago_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        visited_days_ago_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 12px;
                border-radius: 10px;
                border: 1px solid #2f6fdd;
                background-color: rgba(255, 255, 255, 0.85);
                color: #1f5fd6;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #eff5ff;
            }
            QPushButton:pressed {
                background-color: #dfeaff;
            }
            """
        )
        visited_days_ago_button.clicked.connect(
            lambda checked=False, store_id=store["id"], store_name=store["name"]: self.mark_store_visited_days_ago(store_id, store_name)
        )
        button_row.addWidget(visited_days_ago_button)

        row_layout.addLayout(button_row)

        last_visited_text = self.format_days_since_last_visited(store["last_visited"])
        last_visited_label = QLabel(last_visited_text)
        last_visited_label.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #374151;
                padding-top: 1px;
            }
            """
        )
        row_layout.addWidget(last_visited_label)

        return row_widget

    def build_edit_row(self, store):
        row_widget = StoreCardWidget(store["id"], None)
        row_widget.setObjectName("storeCard")
        row_widget.setMinimumHeight(205)
        row_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row_widget.setStyleSheet(
            """
            QWidget#storeCard {
                background-color: #eef5ff;
                border: 2px solid #3f79e0;
                border-radius: 14px;
            }
            QWidget#storeCard:hover {
                background-color: #e3efff;
                border: 2px solid #2f6fdd;
            }
            """
        )

        row_layout = QVBoxLayout(row_widget)
        row_layout.setContentsMargins(14, 14, 14, 14)
        row_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        name_edit = StoreNameEditor(store["id"], self.save_edit, store["name"])
        name_edit.setStyleSheet(
            """
            QLineEdit {
                font-size: 18px;
                font-weight: 600;
                padding: 10px 12px;
                border: 1px solid #d1d9ea;
                border-radius: 10px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #2f6fdd;
            }
            """
        )
        top_row.addWidget(name_edit)

        delete_button = QPushButton("Delete")
        delete_button.setMinimumHeight(38)
        delete_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        delete_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 14px;
                border-radius: 10px;
                border: 1px solid #d1d5db;
                background-color: #ffffff;
                color: #1f2937;
            }
            QPushButton:hover {
                background-color: #f8fafc;
            }
            """
        )
        delete_button.clicked.connect(
            lambda checked=False, store_id=store["id"], store_name=store["name"]: self.delete_store(store_id, store_name)
        )
        top_row.addWidget(delete_button)

        row_layout.addLayout(top_row)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        visited_today_button = QPushButton("Visited today")
        visited_today_button.setMinimumHeight(40)
        visited_today_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        visited_today_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 12px;
                border-radius: 10px;
                border: 1px solid #1f5fd6;
                background-color: #1f5fd6;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #164db0;
                border-color: #164db0;
            }
            QPushButton:pressed {
                background-color: #133f91;
                border-color: #133f91;
            }
            """
        )
        visited_today_button.clicked.connect(
            lambda checked=False, store_id=store["id"]: self.mark_store_visited_today(store_id)
        )
        button_row.addWidget(visited_today_button)

        visited_days_ago_button = QPushButton("Visited # days ago")
        visited_days_ago_button.setMinimumHeight(40)
        visited_days_ago_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        visited_days_ago_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 12px;
                border-radius: 10px;
                border: 1px solid #2f6fdd;
                background-color: rgba(255, 255, 255, 0.85);
                color: #1f5fd6;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #eff5ff;
            }
            QPushButton:pressed {
                background-color: #dfeaff;
            }
            """
        )
        visited_days_ago_button.clicked.connect(
            lambda checked=False, store_id=store["id"], store_name=store["name"]: self.mark_store_visited_days_ago(store_id, store_name)
        )
        button_row.addWidget(visited_days_ago_button)

        row_layout.addLayout(button_row)

        last_visited_text = self.format_days_since_last_visited(store["last_visited"])
        last_visited_label = QLabel(last_visited_text)
        last_visited_label.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #374151;
                padding-top: 1px;
            }
            """
        )
        row_layout.addWidget(last_visited_label)

        return row_widget

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
        
    def format_days_since_last_visited(self, last_visited):
        if not last_visited:
            return "Last visited: never"

        try:
            visited_date = datetime.fromisoformat(str(last_visited)).date()
        except ValueError:
            try:
                visited_date = date.fromisoformat(str(last_visited))
            except ValueError:
                return "Last visited: unknown"

        days_ago = (date.today() - visited_date).days

        if days_ago == 0:
            return "Last visited: today"
        if days_ago == 1:
            return "Last visited: 1 day ago"
        return f"Last visited: {days_ago} days ago"