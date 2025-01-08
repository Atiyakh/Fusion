from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from register_ui import LoginWindow, SignupWindow
from workbench_ui import Workbench
import Fluxon.Connect
import sys, socket

class CircleProgressBar(QLabel):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.move(0,0)
        self.start_angle = 0

        self.setAlignment(Qt.AlignCenter)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_angle)
        self.timer.start(10)

    def update_angle(self):
        self.start_angle -= 16 * 10
        self.start_angle %= 16 * 360
        self.update()

    def resizeEvent(self, event):
        size = min(self.parent().width(), self.parent().height())
        self.setGeometry(
            (self.parent().width() - size) // 2,
            (self.parent().height() - size) // 2,
            size,
            size
        )
        super().resizeEvent(event)

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen(QColor(222, 222, 222), 7)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        radius = self.width() // 4
        ellipse_width = radius * 2
        ellipse_height = radius * 2
        x = (self.width() - ellipse_width) // 2
        y = (self.height() - ellipse_height) // 2

        painter.drawEllipse(x, y, ellipse_width, ellipse_height)

        pen = QPen(QColor(26, 199, 216), 7)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        rect = (x, y, ellipse_width, ellipse_height)
        span_angle = 16 * 180

        painter.drawArc(*rect, self.start_angle, span_angle)

class SendForm(QObject):
    drop_form = pyqtSignal()
    redirect_response = pyqtSignal(object)
    def __init__(self, view, payload, connection:Fluxon.Connect.ConnectionHandler):
        self.payload = payload
        self.connection = connection
        self.view = view
        super().__init__()

    def send_request(self):
        self.response = self.connection.send_request(view=self.view, data=self.payload)
        self.redirect_response.emit(self.response)
        self.drop_form.emit()

class Fusion(QMainWindow):
    def send_request(self, view, data, handle_response):
        self.thread_ = QThread()
        # SendForm setup
        self.send_form = SendForm(view, data, self.connection)
        self.send_form.moveToThread(self.thread_)
        self.send_form.redirect_response.connect(handle_response)
        self.send_form.drop_form.connect(self.thread_.quit)
        self.send_form.drop_form.connect(self.send_form.deleteLater)
        # Connect signals
        self.thread_.started.connect(self.send_form.send_request)
        self.thread_.finished.connect(self.thread_.deleteLater)
        self.thread_.start()
    
    def center_window(self):
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(QDesktopWidget().availableGeometry().center())
        self.move(window_geometry.topLeft())

    def __init__(self):
        super().__init__()
        # central widget
        self.setWindowIcon(QIcon(r"C:\Users\skhodari\Desktop\Fusion\Fusion\fusion_window_icon.png"))
        self.setWindowTitle("Fusion - login page")
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        # circle progress bar
        self.progress_bar = CircleProgressBar(self)
        self.progress_bar.hide()
        self.blur_screen = QLabel(self)
        self.blur_screen.setStyleSheet("background-color: rgba(240, 240, 240, 140);")
        self.blur_screen.hide()
        # connect to server
        self.connection = Fluxon.Connect.ConnectionHandler(
            socket.gethostbyname(socket.gethostname()), 8080
        )
        # workbench
        self.workbench_page = Workbench(
            self.central_widget, self.progress_bar, self
        )
        # login page
        self.login_page = LoginWindow(
            self.central_widget, self.progress_bar, self
        )
        self.central_widget.addWidget(self.login_page)
        # sign up page
        self.signup_page = SignupWindow(
            self.central_widget, self.progress_bar, self
        )
        self.central_widget.addWidget(self.signup_page)

    def load_workbench(self):
        # hide register
        self.signup_page.hide()
        self.login_page.hide()
        # show workbench
        self.central_widget.addWidget(self.workbench_page)
        self.central_widget.setCurrentIndex(2)
        self.workbench_page.show()
        self.center_window()
        self.setWindowTitle("Fusion - workbench")

    def run_progress_bar(self):
        self.blur_screen.show()
        self.progress_bar.show()
        self.blur_screen.raise_()
        self.progress_bar.raise_()

    def stop_progress_bar(self):
        self.blur_screen.hide()
        self.progress_bar.hide()

    def resizeEvent(self, event):
        self.progress_bar.resize(self.size())
        self.blur_screen.resize(self.size())
        return super().resizeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    fusion = Fusion()
    fusion.show()
    fusion.center_window()
    app.exec()