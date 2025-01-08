from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
from Fluxon import Endpoint

class CustomFileBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Custom File Browser")
        self.setGeometry(100, 100, 600, 400)

        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Create a layout
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(30,30,30,30)

        # Create a tree view
        self.tree = QTreeView()
        self.tree.header().hide()
        self.tree.setStyleSheet("""
    /* Styling for the QTreeView itself */
    QTreeView {
        padding: 2px;
        border: none;
        border-radius: 9px;
        background-color: white;  /* Background color */
        color: black;             /* Text color */
        border: 1px solid lightblue; /* Border color */
        font: 14px Arial;         /* Font style and size */
        outline: none;            /* Remove outline */
    }

    /* Styling for the items within the tree view */
    QTreeView::item {
        color: #013c4a;
        margin: 1px;
        background-color: white;  /* Item background color */
        padding: 5px;
        border-radius: 4px;
    }

    /* Hover effect for items */
    QTreeView::item:hover {
        background-color: #e6e6e6;
        color: #013c4a;
        margin: 1px;
        border-radius: 4px;
    }

    /* Selected item styling */
    QTreeView::item:selected {
        background-color: #d6d6d6;  /* Selected item color */
        color: #013c4a;
        margin: 1px;               /* Text color when selected */
        border-radius: 4px;
    }

    /* Styling for the scrollbar */
    QScrollBar:vertical, QScrollBar:horizontal {
        border: none; margin-top:2px;
        background: #f2f2f2; /* Light gray background */
        width: 8px;           /* Slim scrollbar width */
        height: 8px;          /* Slim scrollbar height */
        border-radius: 10px;  /* Rounded corners for the scrollbar */
    }

    /* Handle of the vertical scrollbar */
    QScrollBar::handle:vertical {
        background:rgb(63, 158, 214);   /* Handle color */
        border-radius: 4px;     /* Rounded corners for handle */
    }

    /* Handle of the horizontal scrollbar */
    QScrollBar::handle:horizontal {
        background:rgb(76, 121, 235);   /* Handle color */
        border-radius: 4px;     /* Rounded corners for handle */
    }

    /* Hover effect for the scrollbar handle */
    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
        background:rgb(75, 139, 212);   /* Darker color on hover */
    }

    /* Arrow buttons removal from scrollbars */
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        border: none;
        background: none;
        height: 0px;
        width: 0px;
    }

    /* Remove the scrollbars when not in use */
    QScrollBar:vertical:disabled, QScrollBar:horizontal:disabled {
        background: none; margin-top:2px;
    }
        """)
        layout.addWidget(self.tree)

        # Create a model to hold the tree structure
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Name"])

        # Initialize the extension icon lookup table
        self.extension_icon_lookup = {
            'txt': QIcon(r"C:\Users\lenovo\Desktop\tree\file.png"),
            'jpg': QIcon(r"C:\Users\lenovo\Desktop\tree\image.png"),
            'jpeg': QIcon(r"C:\Users\lenovo\Desktop\tree\image.png"),
            'png': QIcon(r"C:\Users\lenovo\Desktop\tree\image.png"),
            'csv': QIcon(r"C:\Users\lenovo\Desktop\tree\spreadsheet.png"),
            'db': QIcon(r"C:\Users\lenovo\Desktop\tree\database.png"),
            'sqlite': QIcon(r"C:\Users\lenovo\Desktop\tree\database.png"),
            'sqlite3': QIcon(r"C:\Users\lenovo\Desktop\tree\database.png"),
            'mysql': QIcon(r"C:\Users\lenovo\Desktop\tree\database.png"),
            'svg': QIcon(r"C:\Users\lenovo\Desktop\tree\image.png"),
            'zip': QIcon(r"C:\Users\lenovo\Desktop\tree\compressed.png"),
            'mp4': QIcon(r"C:\Users\lenovo\Desktop\tree\video.png"),
            'avi': QIcon(r"C:\Users\lenovo\Desktop\tree\video.png"),
            'mov': QIcon(r"C:\Users\lenovo\Desktop\tree\video.png"),
            'mkv': QIcon(r"C:\Users\lenovo\Desktop\tree\video.png"),
            'mp3': QIcon(r"C:\Users\lenovo\Desktop\tree\audio.png"),
            'wav': QIcon(r"C:\Users\lenovo\Desktop\tree\audio.png"),
            'flac': QIcon(r"C:\Users\lenovo\Desktop\tree\audio.png"),
            'py': QIcon(r"C:\Users\lenovo\Desktop\tree\code.png"),
            'cpp': QIcon(r"C:\Users\lenovo\Desktop\tree\code.png"),
            'html': QIcon(r"C:\Users\lenovo\Desktop\tree\code.png"),
            'c': QIcon(r"C:\Users\lenovo\Desktop\tree\code.png"),
            'cs': QIcon(r"C:\Users\lenovo\Desktop\tree\code.png"),
            'r': QIcon(r"C:\Users\lenovo\Desktop\tree\code.png"),
            'js': QIcon(r"C:\Users\lenovo\Desktop\tree\code.png"),
            'dart': QIcon(r"C:\Users\lenovo\Desktop\tree\code.png"),
        }

        # Create icons for folders
        self.folder_icon = QIcon(r"C:\Users\lenovo\Desktop\tree\open-folder.png")

        # Populate the tree view with file/folder structure
        self.populate_tree({
            "hello.txt": 0,
            "Images": {
                "image1.png": 0,
                "image2.jpg": 0,
                "More Images": {
                    "more_images1.jpg": 0,
                    "more_images2.jpeg": 0,
                    "more_more_images": {
                        "img.png": 0,
                        "svg.svg": 0,
                        "image3.jpg": 0,
                    }
                },
            },
            "SpreadSheets": {
                "DataSet1.csv": 0,
                "DataSet2.csv": 0,
                "DataSet3.csv": 0,
                "DatabasesFiles": {
                    "database1.db": 0,
                    "database2.sqlite": 0,
                    "database3.mysql": 0,
                    "database4.sqlite3": 0,
                    "Archived": {
                        "Backup.zip": 0,
                        "Old Data.zip": 0
                    }
                }
            },
            "AudioFiles": {
                "track1.mp3": 0,
                "track2.wav": 0,
                "album": {
                    "song1.flac": 0,
                    "song2.mp3": 0
                }
            },
            "Code": {
                "project": {
                    "main.py": 0,
                    "module.py": 0,
                    "test.py": 0,
                    "CCode": {
                        "file1.c": 0,
                        "file2.c": 0
                    },
                    "cpp_files": {
                        "cpp1.cpp": 0,
                        "cpp2.cpp": 0
                    },
                    "Web": {
                        "index.html": 0,
                        "style.css": 0,
                        "app.js": 0
                    }
                }
            },
            "Videos": {
                "movie.mp4": 0,
                "clip.mkv": 0,
                "trailer.avi": 0
            },
            "Miscellaneous": {
                "Readme.txt": 0,
                "Info.pdf": 0,
                "another_file.zip": 0
            },
        })        # Set the model to the tree view
        self.tree.setModel(self.model)
        self.tree.setColumnWidth(0, 200)  # Adjust column width

    def lookup_file_icon(self, name):
        # Check if the file has an extension
        if '.' in name:
            # Extract the file extension
            file_extension = name.split('.')[-1].lower()
            # Return the corresponding icon from the lookup table, or a default icon
            return self.extension_icon_lookup.get(file_extension, self.extension_icon_lookup['txt'])
        return self.extension_icon_lookup['txt']  # Default to folder icon if no extension

    def append_layer(self, structure, parent):
        for name in structure:
            if structure[name] == 0:  # file
                file = QStandardItem(name)
                file.setIcon(self.lookup_file_icon(name))
                parent.appendRow([file])
            else:  # folder
                folder = QStandardItem(name)
                folder.setIcon(self.folder_icon)
                self.append_layer(structure[name], folder)
                parent.appendRow([folder])

    def populate_tree(self, structure):
        self.append_layer(structure, self.model)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CustomFileBrowser()
    window.show()
    sys.exit(app.exec_())
