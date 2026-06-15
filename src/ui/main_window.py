from PySide6.QtWidgets import QMainWindow, QLabel, QWidget, QVBoxLayout


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mileage Tracker")
        self.setMinimumSize(800, 600)

        central_widget = QWidget()
        layout = QVBoxLayout()

        label = QLabel("Mileage Tracker is running")
        layout.addWidget(label)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)