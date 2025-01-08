from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys, sqlite3 as sql

def clear_layout(layout:QLayout):
    for widget in range(layout.count()):
        layout.itemAt(widget).widget().deleteLater()

class QCustomHeaderView(QHeaderView):
    def resizeEvent(self, _):
        self.filter_sa.setFixedSize(self.width(), self.height() - 50)
    def moveEvent(self, _):
        self.filter_sa.setFixedSize(self.width(), self.height() - 50)
    def __init__(self, main_, filter_sa):
        self.main_ = main_
        self.filter_sa = filter_sa
        super().__init__(Qt.Orientation.Horizontal)
        self.filter_sa.setParent(self)
        self.setStyleSheet(
            """
            QHeaderView::section {background-color: #e0e0e0; color: #545454; border: 1px solid #dbdbdb; padding-left: 10px; margin:1px; margin-bottom: 37px; padding-top:8px; padding-bottom: 6px}
            """
        )
        self.filter_sa.raise_()
        self.filter_sa.setFixedSize(self.width(), self.height() - 50)
        self.filter_sa.move(0, 47)

class DatabaseView(QWidget):
    def save_changes_button_f(self):
        cur = self.db.cursor()
        cur.execute(f"DELETE FROM {self.current_table};")
        self.db.commit()
        data = self.retrieve_data()
        len_row = data[0].__len__()
        columns = str(self.headers)[1:-1].replace('"', '').replace("'", '')
        for row_num, row in enumerate(data):
            try:
                cur.execute(f"INSERT INTO {self.current_table} ({columns}) VALUES({('?,'*len_row)[:-1]});", row)
            except sql.IntegrityError:
                msg_box = QMessageBox()
                msg_box.setWindowIcon(self.windowIcon())
                msg_box.setStyleSheet('''
                    QWidget { background-color:#222; color:#303030; }
                    QPushButton {
                        border-color: #666;
                        border-width: 2px;
                        border-style: solid;
                        border-radius: 5px;
                        padding: 6px;
                    }''')
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText(f"IntegrityError: Data in row {row_num+1} is in a wrong data type.")
                msg_box.setWindowTitle("Astroid DatabaseViewer Error:")
                msg_box.addButton("OK", QMessageBox.AcceptRole)
                msg_box.exec_()
        self.db.commit()
        cur.close()

    def filterTable(self, column, text):
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, column)
            if text.lower() in item.text().lower():
                self.table_widget.setRowHidden(row, False)
            else:
                self.table_widget.setRowHidden(row, True)

    def get_column_names(self, table_name):
        cursor = self.db.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        column_names = [column[1] for column in columns_info]
        self.tables_columns[table_name] = column_names
    
    def get_tables_names(self):
        cur = self.db.cursor()
        cur.execute('SELECT sql, tbl_name FROM "main".sqlite_master WHERE type=?;', ('table',))
        for table_code, table_name in cur.fetchall():
            self.tables_names.append(table_name)
            self.tables_code[table_name] = table_code
        cur.close()
    
    def fetch_data(self, table_name):
        cur = self.db.cursor()
        cur.execute(f"SELECT * FROM {table_name}")
        data = cur.fetchall()
        cur.close()
        return data

    def __init__(self, database_path):
        super().__init__()
        # table setup
        self.current_table = None
        self.cells = []
        self.tables_names = []
        self.tables_code = dict()
        self.tables_columns = dict()
        self.db = sql.connect(database_path)
        # get tables
        self.get_tables_names()
        # get columns names
        for table_name in self.tables_names:
            self.get_column_names(table_name)
        self.initUI()
    
    def clear_table(self):
        self.table_widget.clear()
        self.table_widget.clearSpans()
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(0)

    def insert_data(self, table):
        # clean up previous table
        self.cells.clear()
        self.clear_table()
        # set headers
        self.headers = self.tables_columns[table]
        clear_layout(self.filtering_layout) # delete filters
        # make new filters
        for col in range(self.headers.__len__()):
            obj = QLineEdit()
            obj.textChanged.connect(lambda text, col=col: self.filterTable(col, text))
            obj.setFixedHeight(35)
            obj.setMinimumWidth(200)
            obj.setPlaceholderText('filter')
            obj.setStyleSheet("color: #303030; background-color: #e5e5e5; border-width: 0px; border-radius: 4px; font-family: Arial; font-size: 16px; padding: 2px; margin: 1px;")
            self.filtering_layout.addWidget(obj)
        data = self.fetch_data(table)
        self.table_widget.setColumnCount(len(self.headers))
        self.table_widget.setHorizontalHeaderLabels(self.headers)
        for row, rowData in enumerate(data):
            self.table_widget.insertRow(row)
            row_ = []
            for col, value in enumerate(rowData):
                item = QTableWidgetItem(str(value))
                row_.append(item)
                self.table_widget.setItem(row, col, item)
            self.cells.append(row_)

    def retrieve_data(self):
        data_ = []
        col_num = self.headers.__len__()
        for row in range(self.cells.__len__()):
            row_ = [self.cells[row][col].text() for col in range(col_num)]
            data_.append(row_)
        return data_

    def initUI(self):
        self.widget_layout = QVBoxLayout(self)
        self.widget_layout.setContentsMargins(5,5,5,5)
        self.widget_layout.setSpacing(2)

        self.table_widget = QTableWidget(self)

        self.filtering_widget_sa = QScrollArea(self)
        self.filtering_widget_sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.filtering_widget_sa.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.filtering_widget_sa.setFixedHeight(50)

        self.custom_h_header = QCustomHeaderView(self, self.filtering_widget_sa)
        self.table_widget.setHorizontalHeader(self.custom_h_header)
        self.table_widget.setShowGrid(False)

        def bind_table_widget_h_scroll_to_filters(_):
            self.filtering_widget_sa.horizontalScrollBar().setValue(self.table_widget.horizontalScrollBar().value()*200)
        
        self.table_widget.horizontalScrollBar().valueChanged.connect(bind_table_widget_h_scroll_to_filters)
        self.filtering_widget_sa.wheelEvent = lambda _: None # remove filters weel scroll

        self.filtering_widget_sa.setStyleSheet("border-color: #dbdbdb; border-width: 0px; border-style: solid; border-radius: 10px; margin: 0px;")
        self.filtering_widget = QWidget()
        self.filtering_widget_sa.setWidget(self.filtering_widget)
        self.filtering_widget_sa.setWidgetResizable(True)
        self.filtering_widget.setObjectName('uw')
        self.filtering_widget.setStyleSheet("#uw { background-color: #eee; border-width: 0px; border-radius: 0px; }")
        self.filtering_layout = QHBoxLayout(self.filtering_widget)
        self.filtering_layout.setContentsMargins(0,0,0,0)
        self.filtering_layout.setSpacing(0)

        self.widget_layout.addWidget(self.table_widget)

        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_widget.horizontalHeader().setMinimumSectionSize(200)

        f = QFont("Arial", 10)
        f.setBold(True)
        self.table_widget.verticalHeader().setFont(f)
        self.table_widget.horizontalHeader().setFont(f)

        self.table_widget.verticalHeader().setStyleSheet(
            "QHeaderView::section { background-color: #e0e0e0; color: #545454; border: 1px solid #dbdbdb; padding-left: 10px; margin:1px; }"
        )

        self.table_widget.setStyleSheet(
            """
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
            QLineEdit {
                background-color: #eee;
                color: #303030;
                border: none;
                font-family: arial;
                font-size: 17px;
            }
            QScrollBar::sub-line {
                border: 0px solid #1e1e1e;
                background-color: #1e1e1e;
                height: 0px;
                width: 0px;
            }
            QTableView QTableCornerButton::section {
                background-color: #e0e0e0; 
                border: 1px solid #dbdbdb;
                border-radius: 3px;
                margin:1px;
            }
            QTableView {
                padding: 3px;
                background-color: #eee;
                color: #303030;
                border: 1px solid #dbdbdb;
                border-radius: 10px;
                selection-background-color: #3a3a3a;
            }
            QTableView::item:selected:focus {
                border: 1px solid #009ACF
            }
            QTableView::item {
                color: #303030;
                border-radius: 3px;
                padding: 2px;
                border: 1px solid #dbdbdb;
                margin: 1px;
            }
            QTableView::item:selected {
                background-color: #eee;
                color: #303030;
            }
            QHeaderView {
                border-radius: 3px;
            }
            QHeaderView::section {
                padding: 2px;
                background-color: #eee;
                color: #303030;
                border: 1px solid #dbdbdb;
                border-radius: 3px;
            }
            QTableView {
                outline: 0;
            }
            """
        )
        self.setGeometry(100, 100, 600, 400)
        self.setWindowTitle('Fusion - Data Visualization')
        self.setWindowIcon(QIcon(r"C:\Users\skhodari\Desktop\Fusion\Fusion\fusion_window_icon.png"))

        self.num = 0

def initiate():
    app = QApplication(sys.argv)
    window = DatabaseView(r"C:\Users\skhodari\Desktop\chinook.db")
    window.insert_data(window.tables_names[3])
    window.show()
    app.exec_()

initiate()
