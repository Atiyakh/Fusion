from PyQt5.QtGui import QMouseEvent, QResizeEvent
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class ChatFooter(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path1 = QPainterPath()
        r = self.rect()
        path1.addRoundedRect(r.x(), r.y(), r.width(), r.height(), 14, 14)
        painter.setBrush(QColor(204, 204, 204))
        painter.setPen(Qt.NoPen)
        painter.fillPath(path1, painter.brush())
        path2 = QPainterPath()
        path2.addRect(r.x(), r.y()-20, r.width(), r.height())
        painter.setBrush(QColor(204, 204, 204))
        painter.setPen(Qt.NoPen)
        painter.fillPath(path2, painter.brush())
    
    def __init__(self, parent_):
        super().__init__()
        # setting the header
        self.setFixedHeight(60)
        self.header_layout = QHBoxLayout(self)

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
        image = ProfilePicture(contact_image_path, 40)
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
        self.close_button.clicked.connect(lambda _: self.parent().hide())
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.setStyleSheet("color: #e0e0e0; background-color: transparent;")
        self.close_button.setFixedWidth(30)
        self.close_button.setFont(QFont("Arial", 20))
        self.header_layout.addWidget(self.close_button)

class ChatWindow(QWidget):
    def mousePressEvent_(self, event):
        self.raise_()
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.pos()
    
    def mousePressEvent(self, event):
        self.raise_()
        super().mousePressEvent(event)

    def mouseMoveEvent_(self, event):
        if self.dragging:
            new_position = self.mapToParent(event.pos() - self.offset)
            self.move(new_position)

    def mouseReleaseEvent_(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

    def __init__(self, contact_name, contact_image_path, parent=None):
        super().__init__(parent)
        self.raise_()
        # chat window setup
        self.setFixedSize(500, 600)
        self.chat_window_layout = QVBoxLayout(self)
        self.chat_window_layout.setContentsMargins(0,0,0,0)
        # chat header setup
        self.chat_header = ChatHeader(self, contact_name, contact_image_path)
        self.chat_window_layout.addWidget(self.chat_header)
        self.chat_window_layout.addStretch(1)
        # chat itself
        self.chat_sa = QScrollArea()
        self.chat_sa_widget = QWidget()
        self.chat_sa_widget_layout = QVBoxLayout(self.chat_sa_widget)
        self.chat_sa_widget_layout.setContentsMargins(0,0,0,0)
        self.chat_sa.setWidget(self.chat_sa_widget)
        self.chat_sa.setWidgetResizable(True)
        self.chat_sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_sa.setStyleSheet("""
            QScrollBar:vertical {
                margin: 3px;
                border: 0px solid #1e1e1e;
                background-color: #fff;
                width: 12px;
            }
            QScrollBar:horizontal {
                margin: 3px;
                border: 0px solid #1e1e1e;
                background-color: #fff;
                height: 12px;
            }
            QScrollBar::handle {
                background-color: #444;
                min-height: 25px;
                border: none;
                border-radius: 3px;
            }
            QScrollBar::handle:hover {
                background-color: #4f4f4f;
                min-height: 25px;
                border: none;
                border-radius: 3px;
            }
            QScrollBar::add-line {
                border: 0px solid #1e1e1e;
                background-color: #1e1e1e;
                height: 0px;
                width: 0px;
            }
            QScrollBar::sub-line {
                border: 0px solid #1e1e1e;
                background-color: #1e1e1e;
                height: 0px;
                width: 0px;
            }
            QScrollArea {border: none;}
        """)
        self.chat_window_layout.addWidget(self.chat_sa)
        # footer
        self.chat_footer = ChatFooter(self)
        self.chat_window_layout.addWidget(self.chat_footer)

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().x(), self.rect().y(), self.rect().width(), self.rect().height(), 14, 14)
        painter.setBrush(QColor(232, 236, 242 ))
        painter.setPen(Qt.NoPen)
        painter.fillPath(path, painter.brush())
        painter.setPen(QPen(QColor(102, 102, 102), 1))
        painter.drawPath(path)

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

class SearchIconLabel(QLabel):
    def set_foreign_events(self):
        def override_moveEvent(_):
            point = self.line_edit.mapTo(self.parent().window(), self.line_edit.pos())
            y_pos = point.y() + (self.line_edit.height() - self.height()) // 2  +self.offset_y
            x_pos = point.x() - self.width() - self.offset_x
            self.move(x_pos, y_pos)
            self.raise_()
        self.line_edit.showEvent = lambda _: self.show()
        self.line_edit.hideEvent = lambda _: self.hide()
        self.line_edit.moveEvent = override_moveEvent

    def __init__(self, line_edit:QLineEdit, parent, offset_x, offset_y):
        super().__init__(parent.window())
        self.offset_x, self.offset_y = offset_x, offset_y
        parent.chasers.append(self)
        self.line_edit = line_edit
        self.show()
        pixmap = QPixmap(r"C:\Users\skhodari\Desktop\Fusion\Fusion\search_icon.png")
        self.setPixmap(pixmap)
        self.setFixedSize(pixmap.size())
        self.set_foreign_events()

class GradientLabel(QLabel):
    def __init__(self, text="Welcome,", parent=None):
        super().__init__(parent)
        self.text = text
        self.font = QFont("Arial", 72)
        self.setFont(self.font)  # Set the font so it reflects in the size hint

    def sizeHint(self):
        # Calculate the size of the text based on the font metrics
        metrics = QFontMetrics(self.font)
        text_width = metrics.horizontalAdvance(self.text)
        text_height = metrics.height()
        self.setFixedWidth(text_width)
        # Add some padding to ensure proper display
        return QSize(text_width, text_height)

    def setText(self, text):
        # Update the text and recalculate the size
        self.text = text
        self.updateGeometry()  # Notify the layout system about size changes
        self.repaint()

    def paintEvent(self, _):
        painter = QPainter(self)
        font = QFont("Arial", 72)
        painter.setFont(font)
        rect = self.rect()
        gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        gradient.setColorAt(0, QColor(0, 11, 212))
        gradient.setColorAt(1, QColor(164, 252, 226))
        pen = QPen()
        pen.setBrush(gradient)
        painter.setPen(pen)
        painter.drawText(QRectF(rect), "Welcome,", QTextOption(Qt.AlignLeft))

class LeftTabPanel(QWidget):
    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.x(), self.y(), self.width(), self.height(), 15, 15)  # Rounded rect with 15px for each corner

        painter.setBrush(QBrush(QColor("#144080")))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

        second_rect = QRect(self.x() + 15, self.y(), self.width() - 15, self.height())
        painter.setBrush(QBrush(QColor("#144080")))
        painter.setPen(Qt.NoPen)
        painter.drawRect(second_rect)

        painter.end()

class Workbench(QWidget):
    def resizeEvent(self, _):
        for chaser in self.chasers:
            chaser.line_edit.moveEvent(None)
        return super().resizeEvent(_)
    def moveEvent(self, _):
        for chaser in self.chasers:
            chaser.line_edit.moveEvent(None)
        return super().resizeEvent(None)

    def run_chat_with(self, contact_name, contact_image_path):
        chat = ChatWindow(contact_name, contact_image_path, self)
        chat.move(self.width()-chat.width()-20, self.height()-chat.height()-20)
        chat.show()

    def add_contacts(self, contact_name, contact_image_path, contacts_layout:QLayout):
        # contact layout
        contact_widget = QWidget()
        contact_widget.setCursor(Qt.PointingHandCursor)
        def override_mousePressEvent():
            contact_widget.setStyleSheet("background-color: #adbcd0; border: none; border-radius: 6px;")
        def override_mouseReleaseEvent():
            contact_widget.setStyleSheet("background-color: #bbcadf; border: none; border-radius: 6px;")
            self.run_chat_with(contact_name, contact_image_path)
        def override_enterEvent():
            contact_widget.setStyleSheet("background-color: #bbcadf; border: none; border-radius: 6px;")
        def override_leaveEvent():
            contact_widget.setStyleSheet("background-color: transparent; border: none; border-radius: 6px;")
        contact_widget.mousePressEvent = lambda _: override_mousePressEvent()
        contact_widget.mouseReleaseEvent = lambda _: override_mouseReleaseEvent()
        contact_widget.enterEvent = lambda _: override_enterEvent()
        contact_widget.leaveEvent = lambda _: override_leaveEvent()
        contact_layout = QHBoxLayout(contact_widget)
        contact_layout.setSpacing(0)
        contact_layout.setContentsMargins(25, 0,0,0)
        contact_widget.setFixedHeight(100)
        # contact image
        picture = ProfilePicture(
            image_path=contact_image_path, size=60
        )
        contact_layout.addWidget(picture)
        # contact name
        contact_name_label = QLabel(contact_name)
        contact_name_label.setFont(QFont("Arial", 16))
        contact_name_label.setStyleSheet("color: #6a7585;")

        contact_layout.addWidget(contact_name_label)
        contacts_layout.addWidget(contact_widget)

        
    def __init__(self, stacked_widget:QStackedWidget, progress_bar, main):
        super().__init__()
        self.contacts_list = []
        self.stacked_widget = stacked_widget
        self.progress_bar = progress_bar
        self.main = main
        # workbench page
        self.workbench_page = QWidget()
        self.workbench_page.setMinimumSize(QSize(1350, 650))
        self.workbench_page.setObjectName("workbench-container")
        self.workbench_page_layout = QHBoxLayout(self.workbench_page)
        self.workbench_page_layout.setSpacing(0)
        self.chasers = []
        self.workbench_page_layout.setContentsMargins(0,0,0,0)
        self.workbench_page.setStyleSheet("""
        #workbench-container {
            background-color: #ebf2fc;
            border: none;
            border-radius: 15px;
        }
        #right_container, #recent-activities-widget {
            background-color: #fff;
            border: none;
            border-radius: 15px;
        }
        #search_input{
            border: none;
            border-radius: 19px;
            background-color: #fff;
            color: #004d54;
            padding: 5px;
            padding-right: 13px; padding-left: 13px;
        }
        """)
        # set shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(5, 5)
        self.workbench_page.setGraphicsEffect(shadow)
        # left side tab panel
        self.workbench_page_side_tab_panel_widget = LeftTabPanel()
        self.workbench_page_side_tab_panel_layout = QVBoxLayout(self.workbench_page_side_tab_panel_widget)
        self.workbench_page_side_tab_panel_layout.setAlignment(Qt.AlignCenter)
        self.workbench_page_side_tab_panel_layout.setContentsMargins(0,0,0,0)
        self.workbench_page_side_tab_panel_widget.setFixedWidth(250)
        # spacer 1
        self.workbench_page_side_tab_panel_layout.addItem(QSpacerItem(20, 40))
        # avatar
        self.avatar_icon = QLabel()
        self.avatar_icon.setAlignment(Qt.AlignCenter)
        self.avatar_icon.setFixedHeight(110)
        pixmap = QPixmap(r"C:\Users\skhodari\Desktop\Fusion\Fusion\avatar.png").scaled(110, 110, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.avatar_icon.setPixmap(pixmap)
        self.workbench_page_side_tab_panel_layout.addWidget(self.avatar_icon)
        # username label
        self.username_label = QLabel("AtiyaKh")
        self.username_label.setAlignment(Qt.AlignCenter)
        self.username_label.setStyleSheet("color: #fff;")
        self.username_label.setFont(QFont("Segoe UI", 15))
        self.workbench_page_side_tab_panel_layout.addWidget(self.username_label)
        # spacer 2
        self.workbench_page_side_tab_panel_layout.addItem(QSpacerItem(20, 25))
        ############ tabs
        def override_enterEvent(self:QWidget):
            self.setStyleSheet("QWidget {background-color: #103770;}")
        def override_leaveEvent(self:QWidget):
            self.setStyleSheet("QWidget {background-color: #144080;}")
        tab_height = 45
        self.tabs_widget = QWidget()
        self.tabs_widget_layout = QVBoxLayout(self.tabs_widget)
        self.tabs_widget_layout.setSpacing(0)
        self.tabs_widget_layout.setContentsMargins(0,0,0,0)
        ### Home
        self.home_tab_widget = QWidget()
        self.home_tab_widget.enterEvent = lambda _: override_enterEvent(self.home_tab_widget)
        self.home_tab_widget.leaveEvent = lambda _: override_leaveEvent(self.home_tab_widget)
        self.home_tab_widget.setCursor(Qt.PointingHandCursor)
        self.home_tab_widget.setFixedHeight(tab_height)
        self.home_tab_widget.setStyleSheet("QWidget {background-color: #0b3066;}")
        self.home_tab_layout = QHBoxLayout(self.home_tab_widget)
        self.home_tab_layout.setContentsMargins(20,0,0,0)
        # pixmap label
        self.home_pixmap_label = QLabel()
        self.home_pixmap = QPixmap(r"C:\Users\skhodari\Desktop\Fusion\Fusion\home_icon.png").scaled(25,25, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.home_pixmap_label.setPixmap(self.home_pixmap)
        self.home_tab_layout.addWidget(self.home_pixmap_label)
        # text label
        self.home_text_label = QLabel("Home")
        self.home_text_label.setStyleSheet("color: #fff;")
        self.home_text_label.setFont(QFont("Segoe UI", 12))
        self.home_tab_layout.addWidget(self.home_text_label)
        self.home_tab_layout.addStretch(1)

        self.tabs_widget_layout.addWidget(self.home_tab_widget)
        ### Manage data
        self.data_tab_widget = QWidget()
        self.data_tab_widget.enterEvent = lambda _: override_enterEvent(self.data_tab_widget)
        self.data_tab_widget.leaveEvent = lambda _: override_leaveEvent(self.data_tab_widget)
        self.data_tab_widget.setCursor(Qt.PointingHandCursor)
        self.data_tab_widget.setFixedHeight(tab_height)
        self.data_tab_layout = QHBoxLayout(self.data_tab_widget)
        self.data_tab_layout.setContentsMargins(20,0,0,0)
        # pixmap label
        self.data_pixmap_label = QLabel()
        self.data_pixmap = QPixmap(r"C:\Users\skhodari\Desktop\Fusion\Fusion\assets_icon.png").scaled(25,25, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.data_pixmap_label.setPixmap(self.data_pixmap)
        self.data_tab_layout.addWidget(self.data_pixmap_label)
        # text label
        self.data_text_label = QLabel("Data Management")
        self.data_text_label.setStyleSheet("color: #fff;")
        self.data_text_label.setFont(QFont("Segoe UI", 12))
        self.data_tab_layout.addWidget(self.data_text_label)
        self.data_tab_layout.addStretch(1)

        self.tabs_widget_layout.addWidget(self.data_tab_widget)
        ### Data Visualization
        self.dv_tab_widget = QWidget()
        self.dv_tab_widget.enterEvent = lambda _: override_enterEvent(self.dv_tab_widget)
        self.dv_tab_widget.leaveEvent = lambda _: override_leaveEvent(self.dv_tab_widget)
        self.dv_tab_widget.setCursor(Qt.PointingHandCursor)
        self.dv_tab_widget.setFixedHeight(tab_height)
        self.dv_tab_layout = QHBoxLayout(self.dv_tab_widget)
        self.dv_tab_layout.setContentsMargins(20,0,0,0)
        # pixmap label
        self.dv_pixmap_label = QLabel()
        self.dv_pixmap = QPixmap(r"C:\Users\skhodari\Desktop\Fusion\Fusion\dv_icon.png").scaled(25,25, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.dv_pixmap_label.setPixmap(self.dv_pixmap)
        self.dv_tab_layout.addWidget(self.dv_pixmap_label)
        # text label
        self.dv_text_label = QLabel("Data Visualization")
        self.dv_text_label.setStyleSheet("color: #fff;")
        self.dv_text_label.setFont(QFont("Segoe UI", 12))
        self.dv_tab_layout.addWidget(self.dv_text_label)
        self.dv_tab_layout.addStretch(1)

        self.tabs_widget_layout.addWidget(self.dv_tab_widget)
        ### Model Training
        self.mt_tab_widget = QWidget()
        self.mt_tab_widget.enterEvent = lambda _: override_enterEvent(self.mt_tab_widget)
        self.mt_tab_widget.leaveEvent = lambda _: override_leaveEvent(self.mt_tab_widget)
        self.mt_tab_widget.setCursor(Qt.PointingHandCursor)
        self.mt_tab_widget.setFixedHeight(tab_height)
        self.mt_tab_layout = QHBoxLayout(self.mt_tab_widget)
        self.mt_tab_layout.setContentsMargins(20,0,0,0)
        # pixmap label
        self.mt_pixmap_label = QLabel()
        self.mt_pixmap = QPixmap(r"C:\Users\skhodari\Desktop\Fusion\Fusion\mt_icon.png").scaled(25,25, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.mt_pixmap_label.setPixmap(self.mt_pixmap)
        self.mt_tab_layout.addWidget(self.mt_pixmap_label)
        # text label
        self.mt_text_label = QLabel("Model Training")
        self.mt_text_label.setStyleSheet("color: #fff;")
        self.mt_text_label.setFont(QFont("Segoe UI", 12))
        self.mt_tab_layout.addWidget(self.mt_text_label)
        self.mt_tab_layout.addStretch(1)

        self.tabs_widget_layout.addWidget(self.mt_tab_widget)
        #############
        self.workbench_page_side_tab_panel_layout.addWidget(self.tabs_widget)
        self.workbench_page_side_tab_panel_layout.addStretch(1)
        
        self.workbench_page_layout.addWidget(self.workbench_page_side_tab_panel_widget)
        # content widget
        self.content_widget = QStackedWidget()
        self.workbench_page_layout.addWidget(self.content_widget)
        # Home page:
        #########################################
        #########################################
        self.home_page = QWidget()
        self.home_page_layout = QHBoxLayout(self.home_page)

        # left container
        self.home_left_container = QWidget()
        self.home_left_container_layout = QVBoxLayout(self.home_left_container)

        # Welcome
        self.welcome_label_widget = QWidget()
        self.welcome_label_layout = QVBoxLayout(self.welcome_label_widget)
        self.welcome_label_layout.setContentsMargins(22,0,0,0)
        self.welcome_label = GradientLabel()
        self.welcome_label_layout.addWidget(self.welcome_label)
        self.home_left_container_layout.addWidget(self.welcome_label_widget)

        # username label
        self.username_greeting_label = QLabel("Atiya".capitalize()+"!")
        self.username_greeting_label.setStyleSheet("color: #6a7585; margin-left: 10px;")
        self.username_greeting_label.setFont(QFont("Arial", 55))
        self.username_greeting_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.home_left_container_layout.addWidget(self.username_greeting_label)
        self.home_left_container_layout.setContentsMargins(0,0,0,0)

        # recent activities:
        self.recent_activities_widget = QWidget()
        self.recent_activities_widget.setObjectName("recent-activities-widget")
        self.recent_activities_widget.setStyleSheet("background-color: #d4e1f4; margin: 12px;")
        self.recent_activities_layout = QVBoxLayout(self.recent_activities_widget)

        self.recent_activities_label = QLabel("Recent Activities")
        self.recent_activities_label.setStyleSheet("color: #6a7585; margin: 6px; margin-top: 14px;")
        self.recent_activities_label.setFont(QFont("Arial", 35))

        self.home_left_container_layout.addItem(QSpacerItem(100, 200))
        self.recent_activities_layout.addWidget(self.recent_activities_label)
        self.recent_activities_layout.addStretch(1)

        self.home_left_container_layout.addWidget(self.recent_activities_widget)
        self.home_page_layout.addWidget(self.home_left_container)

        #### right container
        self.home_right_container = QWidget()
        self.home_right_container.setStyleSheet("background-color: #d4e1f4; margin: 12px;")
        self.home_right_container.setFixedWidth(450)
        self.home_right_container.setObjectName("right_container")
        self.home_right_container_layout = QVBoxLayout(self.home_right_container)

        # contacts label
        self.contacts_label = QLabel("My Contacts")
        self.contacts_label.setAlignment(Qt.AlignCenter)
        self.contacts_label.setFixedHeight(90)
        self.contacts_label.setFont(QFont("Arial", 30))
        self.contacts_label.setStyleSheet("color: #6a7585; margin-top:20px;")

        self.home_right_container_layout.addWidget(self.contacts_label)

        # search contacts
        self.search_contacts_input = QLineEdit()
        self.search_contacts_input_chaser = SearchIconLabel(self.search_contacts_input, self, -33, -107)
        self.search_contacts_input.setObjectName("search_input")
        self.search_contacts_input.setFont(QFont("Arial", 14))
        self.search_contacts_input.setPlaceholderText("Search Contacts")
        self.search_contacts_input.setFixedHeight(65)
        self.search_contacts_input.setStyleSheet(f"color: #6a7585; background-color: #fff; border: none; border-radius: 20px; padding-left: 35px")

        self.home_right_container_layout.addWidget(self.search_contacts_input)

        # contacts scroll area
        self.contact_sa = QScrollArea()
        self.contact_sa_widget = QWidget()
        self.contact_sa_widget_layout = QVBoxLayout(self.contact_sa_widget)
        self.contact_sa_widget_layout.setContentsMargins(0,0,0,0)
        self.contact_sa.setWidget(self.contact_sa_widget)
        self.contact_sa.setWidgetResizable(True)
        self.contact_sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.contact_sa.setStyleSheet("""
            QScrollBar:vertical {
                margin: 3px;
                border: 0px solid #1e1e1e;
                background-color: #fff;
                width: 12px;
            }
            QScrollBar:horizontal {
                margin: 3px;
                border: 0px solid #1e1e1e;
                background-color: #fff;
                height: 12px;
            }
            QScrollBar::handle {
                background-color: #444;
                min-height: 25px;
                border: none;
                border-radius: 3px;
            }
            QScrollBar::handle:hover {
                background-color: #4f4f4f;
                min-height: 25px;
                border: none;
                border-radius: 3px;
            }
            QScrollBar::add-line {
                border: 0px solid #1e1e1e;
                background-color: #1e1e1e;
                height: 0px;
                width: 0px;
            }
            QScrollBar::sub-line {
                border: 0px solid #1e1e1e;
                background-color: #1e1e1e;
                height: 0px;
                width: 0px;
            }
            QScrollArea {border: none;}
        """)

        self.home_right_container_layout.addWidget(self.contact_sa)

        self.home_page_layout.addWidget(self.home_right_container)
        self.content_widget.addWidget(self.home_page)

        # test
        for _ in range(10):
            self.add_contacts(
            contact_name="MichaelJackson",
            contact_image_path=r"C:\Users\skhodari\Downloads\pexels-thatguycraig000-1563356.jpg",
            contacts_layout=self.contact_sa_widget_layout
        )
        ############################################################
        ############################################################
        # load workbench page
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(40,40,40,40)
        self.layout().addWidget(self.workbench_page)

if __name__ == '__main__':
    app = QApplication([])
    workbench = Workbench(None, None, None)
    workbench.showMaximized()
    workbench.show()
    app.exec_()
