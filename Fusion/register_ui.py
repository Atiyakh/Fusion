from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class LoginWindow(QWidget):
    def set_window_title(self):
        self.window().setWindowTitle("Fusion - login page")

    def switch_page(self):
        current_idx = self.stacked_widget.currentIndex()
        new_idx = (current_idx + 1) % self.parentWidget().count()  # circular switching
        self.stacked_widget.setCurrentIndex(new_idx)
        self.stacked_widget.currentWidget().set_window_title()

    def send_form(self):
        self.main.run_progress_bar()
        def handle_response(response):
            if response:
                self.main.load_workbench()
            self.main.stop_progress_bar()
        self.main.send_request('login', {
            'username': self.username_edit.text(),
            'password': self.password_edit.text()
        }, handle_response)

    def __init__(self, stacked_widget:QStackedWidget, progress_bar, main):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.progress_bar = progress_bar
        self.main = main
        # login page
        self.login_page = QWidget()
        self.login_page.setMinimumSize(QSize(340, 450))
        self.login_page.setObjectName("login-container")
        self.login_page.setStyleSheet("""
        #login-container{
            background-color: #fff;
            border: none;
            border-radius: 15px;
        }          
        QLineEdit{
            border: none;
            color: #004d54;
            padding: 8px;
            margin:2px;
            padding-left:3px;
            padding-right:3px;
            background-color: transparent;
            border-bottom: 4px solid lightblue;
        }
        QLineEdit:focus {
            border: none;
            color: #004d54;
            padding: 8px;
            margin:2px;
            padding-left:3px;
            padding-right:3px;
            background-color: transparent;
            border-bottom: 4px solid #1ac7d8;
        }
        #login_button{
            color: white;
            background-color: #1ac7d8;
            border: none;
            border-radius: 14px;
            padding: 7px;
        }
        #forgot_password_button{
            color:#1ac7d8;
            text-align: left;
            background-color: transparent;
        }
        #switch_signup_button{
            color: #1ac7d8;
            padding-left: 3px;
            padding-right: 3px;
            background-color: transparent;
        }
        """)
        self.login_page_layout = QVBoxLayout()
        self.login_page_layout.setContentsMargins(25,25,25,25)
        self.login_page.setLayout(self.login_page_layout)
        # set shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(5, 5)
        self.login_page.setGraphicsEffect(shadow)
        # login label
        self.login_label = QLabel("Login")
        self.login_label.setStyleSheet("color: #004d54;")
        self.login_label.setAlignment(Qt.AlignCenter|Qt.AlignTop)
        login_label_font = QFont("Segoe UI", 19)
        login_label_font.setWeight(64)
        self.login_label.setFont(login_label_font)
        self.login_page_layout.addWidget(self.login_label)
        # logo label
        self.logo_label = QLabel()
        self.logo_label.setMinimumHeight(180)
        self.logo_pixmap = QPixmap(r"C:\Users\skhodari\Desktop\Fusion\Fusion\fusion_logo.png").scaled(225, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(self.logo_pixmap)
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.login_page_layout.addWidget(self.logo_label)
        self.login_page_layout.addStretch(1)
        # username field
        self.username_edit = QLineEdit()
        self.username_edit.setFont(QFont("Segoe UI", 12))
        self.username_edit.setPlaceholderText("Username")
        self.login_page_layout.addWidget(self.username_edit)
        # password field
        self.password_edit = QLineEdit()
        self.password_edit.setFont(QFont("Segoe UI", 12))
        self.password_edit.setPlaceholderText("Password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.login_page_layout.addWidget(self.password_edit)
        # forgot password?
        self.forgot_password_button = QPushButton("forgot password?")
        self.forgot_password_button.setCursor(Qt.PointingHandCursor)
        self.forgot_password_button.setObjectName("forgot_password_button")
        self.forgot_password_button.setFont(QFont("Segoe UI", 9))
        self.login_page_layout.addWidget(self.forgot_password_button)
        # login button
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(lambda _: self.send_form())
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.setObjectName("login_button")
        self.login_button.setFont(QFont("Segoe UI", 12))
        self.login_page_layout.addWidget(self.login_button)
        # don't have an account
        self.dont_have_account_container = QWidget()
        self.dont_have_account_layout = QHBoxLayout()
        self.dont_have_account_layout.addStretch(1)
        self.dont_have_account_container.setLayout(self.dont_have_account_layout)
        # label
        self.dont_have_account_label = QLabel("Don't have an account?")
        self.dont_have_account_label.setFont(QFont("Segoe UI", 9))
        self.dont_have_account_layout.addWidget(self.dont_have_account_label)
        # button
        self.switch_signup_button = QPushButton("Sign up")
        self.switch_signup_button.clicked.connect(lambda _: self.switch_page())
        self.switch_signup_button.setCursor(Qt.PointingHandCursor)
        self.switch_signup_button.setObjectName("switch_signup_button")
        self.switch_signup_button.setFont(QFont("Segoe UI", 9))
        self.dont_have_account_layout.addWidget(self.switch_signup_button)
        self.dont_have_account_layout.addStretch(1)

        self.login_page_layout.addWidget(self.dont_have_account_container)
        #accessibility
        self.username_edit.returnPressed.connect(lambda: self.password_edit.setFocus())
        self.password_edit.returnPressed.connect(lambda: self.send_form())
        # load login page
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(40,40,40,40)
        self.layout().addWidget(self.login_page)

class SignupWindow(QWidget):
    def set_window_title(self):
        self.window().setWindowTitle("Fusion - sign up page")

    def switch_page(self):
        current_idx = self.stacked_widget.currentIndex()
        new_idx = (current_idx + 1) % self.parentWidget().count()
        self.stacked_widget.setCurrentIndex(new_idx)
        self.stacked_widget.currentWidget().set_window_title()
    
    def send_form(self):
        self.main.run_progress_bar()
        def handle_response(response):
            if response:
                self.main.load_workbench()
            self.main.stop_progress_bar()
        self.main.send_request('signup', {
            'first_name': self.first_name_edit.text(),
            'last_name': self.last_name_edit.text(),
            'email': self.email_edit.text(),
            'username': self.username_edit.text(),
            'password': self.password_edit.text()
        }, handle_response)

    def __init__(self, stacked_widget:QStackedWidget, progress_bar, main):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.progress_bar = progress_bar
        self.main = main
        # login page
        self.signup_page = QWidget()
        self.signup_page.setMinimumSize(QSize(340, 530))
        self.signup_page.setObjectName("signup-container")
        self.signup_page.setStyleSheet("""
        #signup-container{
            background-color: #fff;
            border: none;
            border-radius: 15px;
        }          
        QLineEdit{
            border: none;
            color: #004d54;
            padding: 8px;
            margin:2px;
            padding-left:3px;
            padding-right:3px;
            background-color: transparent;
            border-bottom: 4px solid lightblue;
        }
        QLineEdit:focus {
            border: none;
            color: #004d54;
            padding: 8px;
            margin:2px;
            padding-left:3px;
            padding-right:3px;
            background-color: transparent;
            border-bottom: 4px solid #1ac7d8;
        }
        #signup_button{
            color: white;
            background-color: #1ac7d8;
            border: none;
            border-radius: 14px;
            padding: 7px;
        }
        #forgot_password_button{
            color: #1ac7d8;
            text-align: left;
            background-color: transparent;
        }
        #switch_login_button{
            color: #1ac7d8;
            padding-left: 3px;
            padding-right: 3px;
            background-color: transparent;
        }
        """)
        self.signup_page_layout = QVBoxLayout()
        self.signup_page_layout.setContentsMargins(25,25,25,25)
        self.signup_page.setLayout(self.signup_page_layout)
        # set shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(5, 5)
        self.signup_page.setGraphicsEffect(shadow)
        # signup label
        self.signup_label = QLabel("Signup")
        self.signup_label.setStyleSheet("color: #004d54;")
        self.signup_label.setAlignment(Qt.AlignCenter|Qt.AlignTop)
        signup_label_font = QFont("Segoe UI", 19)
        signup_label_font.setWeight(64)
        self.signup_label.setFont(signup_label_font)
        self.signup_page_layout.addWidget(self.signup_label)
        # logo label
        self.logo_label = QLabel()
        self.logo_pixmap = QPixmap(r"C:\Users\skhodari\Desktop\Fusion\Fusion\fusion_logo.png").scaled(225, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(self.logo_pixmap)
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.signup_page_layout.addWidget(self.logo_label)
        self.signup_page_layout.addStretch(1)
        # first name | last name
        self.first_name_last_name_contianer = QWidget()
        self.first_name_last_name_layout = QHBoxLayout()
        self.first_name_last_name_layout.setSpacing(5)
        self.first_name_last_name_layout.setContentsMargins(0,0,0,0)
        self.first_name_last_name_contianer.setLayout(self.first_name_last_name_layout)
        # first name field
        self.first_name_edit = QLineEdit()
        self.first_name_edit.setFont(QFont("Segoe UI", 12))
        self.first_name_edit.setPlaceholderText("First name")
        self.first_name_last_name_layout.addWidget(self.first_name_edit)
        # last name field
        self.last_name_edit = QLineEdit()
        self.last_name_edit.setFont(QFont("Segoe UI", 12))
        self.last_name_edit.setPlaceholderText("Last name")
        self.first_name_last_name_layout.addWidget(self.last_name_edit)

        self.signup_page_layout.addWidget(self.first_name_last_name_contianer)
        # email field
        self.email_edit = QLineEdit()
        self.email_edit.setFont(QFont("Segoe UI", 12))
        self.email_edit.setPlaceholderText("Email")
        self.signup_page_layout.addWidget(self.email_edit)
        # username field
        self.username_edit = QLineEdit()
        self.username_edit.setFont(QFont("Segoe UI", 12))
        self.username_edit.setPlaceholderText("Username")
        self.signup_page_layout.addWidget(self.username_edit)
        # password field
        self.password_edit = QLineEdit()
        self.password_edit.setFont(QFont("Segoe UI", 12))
        self.password_edit.setPlaceholderText("Password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.signup_page_layout.addWidget(self.password_edit)
        # signup button
        self.signup_button = QPushButton("Sign up")
        self.signup_button.clicked.connect(lambda _: self.send_form())
        self.signup_button.setCursor(Qt.PointingHandCursor)
        self.signup_button.setObjectName("signup_button")
        self.signup_button.setFont(QFont("Segoe UI", 12))
        self.signup_page_layout.addWidget(self.signup_button)
        # don't have an account
        self.have_account_container = QWidget()
        self.dont_have_account_layout = QHBoxLayout()
        self.dont_have_account_layout.addStretch(1)
        self.have_account_container.setLayout(self.dont_have_account_layout)
        # label
        self.already_have_account_label = QLabel("Already have an account?")
        self.already_have_account_label.setFont(QFont("Segoe UI", 9))
        self.dont_have_account_layout.addWidget(self.already_have_account_label)
        # button
        self.switch_signup_button = QPushButton("Login")
        self.switch_signup_button.clicked.connect(lambda _: self.switch_page())
        self.switch_signup_button.setCursor(Qt.PointingHandCursor)
        self.switch_signup_button.setObjectName("switch_login_button")
        self.switch_signup_button.setFont(QFont("Segoe UI", 9))
        self.dont_have_account_layout.addWidget(self.switch_signup_button)
        self.dont_have_account_layout.addStretch(1)

        self.signup_page_layout.addWidget(self.have_account_container)
        # accessibility
        self.first_name_edit.returnPressed.connect(lambda: self.last_name_edit.setFocus())
        self.last_name_edit.returnPressed.connect(lambda: self.email_edit.setFocus())
        self.email_edit.returnPressed.connect(lambda: self.username_edit.setFocus())
        self.username_edit.returnPressed.connect(lambda: self.password_edit.setFocus())
        self.password_edit.returnPressed.connect(lambda: self.send_form())
        # load signup page
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(40,40,40,40)
        self.layout().addWidget(self.signup_page)
