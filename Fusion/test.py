from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPainter, QPixmap, QPainterPath
from PyQt5.QtCore import Qt, QRect

from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter, QPainterPath, QPen, QColor
from PyQt5.QtWidgets import QWidget, QApplication

class ProfilePicture(QLabel):
    def __init__(self, image_path, size=20, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.image_path = image_path

        self.pixmap = QPixmap(self.image_path)
        if self.pixmap.height() < self.pixmap.width():
            self.pixmap = self.pixmap.scaled(QSize(int(self.pixmap.width()*(size/self.pixmap.height())), size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            self.pixmap = self.pixmap.scaled(QSize(size, int(self.pixmap.height()*(size/self.pixmap.width()))), Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        rect = QRectF(0, 0, self.width(), self.height())
        path.addEllipse(rect)
        painter.setClipPath(path)
        offset_x = (self.width() - self.pixmap.width()) // 2
        offset_y = (self.height() - self.pixmap.height()) // 2
        painter.drawPixmap(offset_x, offset_y, self.pixmap)
        painter.end()

class ChatHeader(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path1 = QPainterPath()
        r = self.rect()
        path1.addRoundedRect(r.x(), r.y(), r.width(), r.height(), 14, 14)
        painter.setBrush(QColor(95,95,95))
        painter.setPen(Qt.NoPen)
        painter.fillPath(path1, painter.brush())
        path2 = QPainterPath()
        path2.addRect(r.x(), r.y()+20, r.width(), r.height())
        painter.setBrush(QColor(95,95,95))
        painter.setPen(Qt.NoPen)
        painter.fillPath(path2, painter.brush())

    def __init__(self, parent_, contact_name, contact_image_path):
        super().__init__()
        # setting the header
        self.setFixedHeight(60)
        self.header_layout = QHBoxLayout(self)
        # set foreign events
        self.mousePressEvent = lambda event: parent_.mousePressEvent_(event)
        self.mouseMoveEvent = lambda event: parent_.mouseMoveEvent_(event)
        self.mouseReleaseEvent = lambda event: parent_.mouseReleaseEvent_(event)
        # profile picture
        image = ProfilePicture(r"C:\Users\skhodari\Desktop\Fusion\Fusion\avatar.png", 40)
        image.setAlignment(Qt.AlignCenter)
        self.header_layout.addWidget(image)
        # username label
        self.username_label = QLabel(contact_name)
        self.username_label.setFont(QFont("Arial", 12))
        self.username_label.setStyleSheet("color: #e0e0e0;")
        self.header_layout.addWidget(self.username_label)
        self.header_layout.addStretch(1)
        # close button
        self.close_button = QPushButton(text="×")
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.setStyleSheet("color: #e0e0e0; background-color: transparent;")
        self.close_button.setFixedWidth(30)
        self.close_button.setFont(QFont("Arial", 20))
        self.header_layout.addWidget(self.close_button)

class ChatWindow(QWidget):
    def mousePressEvent_(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.pos()

    def mouseMoveEvent_(self, event):
        if self.dragging:
            new_position = self.mapToParent(event.pos() - self.offset)
            self.move(new_position)

    def mouseReleaseEvent_(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
    def __init__(self, contact_name, contact_image_path, parent=None):
        super().__init__(parent)
        # chat window setup
        self.setFixedSize(500, 600)
        self.chat_window_layout = QVBoxLayout(self)
        self.chat_window_layout.setContentsMargins(0,0,0,0)
        # chat header setup
        self.chat_header = ChatHeader(self, contact_name, contact_image_path)
        self.chat_window_layout.addWidget(self.chat_header)
        self.chat_window_layout.addStretch(1)

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().x(), self.rect().y(), self.rect().width(), self.rect().height(), 14, 14)
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(Qt.NoPen)
        painter.fillPath(path, painter.brush())
        painter.setPen(QPen(QColor(102, 102, 102), 1))
        painter.drawPath(path)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    widget = ChatWindow("AtiyaKh", r"C:\Users\skhodari\Downloads\pexels-photo-674010.png")
    widget.show()
    sys.exit(app.exec_())

