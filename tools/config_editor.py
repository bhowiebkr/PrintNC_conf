import sys
import logging
import os
from tkinter import HORIZONTAL, dialog

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from linuxcnc_config import LinuxCNCConfig


DEBUG = False


class TableModel(QAbstractTableModel):
    def __init__(self, data, section):
        super(TableModel, self).__init__()

        self.horizontalHeaders = [""] * 3
        self.setHeaderData(0, Qt.Horizontal, "Variable")
        self.setHeaderData(1, Qt.Horizontal, "Value")
        self.setHeaderData(2, Qt.Horizontal, "Comment")

        self._data = data
        self.section = section

    def setHeaderData(self, section, orientation, data, role=Qt.EditRole):
        if orientation == Qt.Horizontal and role in (Qt.DisplayRole, Qt.EditRole):
            try:
                self.horizontalHeaders[section] = data
                return True
            except:
                return False
        return super().setHeaderData(section, orientation, data, role)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            try:
                return self.horizontalHeaders[section]
            except:
                pass
        return super().headerData(section, orientation, role)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self._data.get_variables(self.section)[index.row()][index.column()]
        if role == Qt.TextAlignmentRole:

            if index.column() == 0:
                return Qt.AlignVCenter | Qt.AlignRight
            elif index.column() == 1:
                return Qt.AlignCenter
            elif index.column() == 2:
                return Qt.AlignVCenter | Qt.AlignLeft

    def rowCount(self, index):
        return len(self._data.get_variables(self.section))

    def columnCount(self, index):
        return 3


class SectionTab(QWidget):
    def __init__(self, name, config, parent=None):
        super(SectionTab, self).__init__(parent)
        self.name = name
        self.config = config

        self.model = TableModel(self.config, section=name)

        # layouts
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Widgets
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.verticalHeader().setVisible(False)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.table.horizontalHeader().setStretchLastSection(True)

        # add widgets
        main_layout.addWidget(self.table)

        # self.load_values()

    @staticmethod
    def nice_name(name):
        return name[1:-1].replace("_", " ")

    def get_nice_name(self):
        return self.nice_name(self.name)


class Editor(QWidget):
    def __init__(self, parent=None):
        super(Editor, self).__init__(parent)
        self.setWindowTitle("LinuxCNC Config Editor")

        self.settings = QSettings("LinuxCNC_editor", "LinuxCNC_editor")
        self.config = None

        # Layout
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)
        btn_layout = QVBoxLayout()
        data_layout = QVBoxLayout()

        try:
            self.restoreGeometry(self.settings.value("geometry"))
        except Exception as e:
            logging.warning(
                "Unable to load settings. First time opening the tool?\n" + str(e)
            )

        # Widgets
        load_btn = QPushButton("Load Config (INI)")
        save_btn = QPushButton("Save Config (INI)")
        self.tabs = QTabWidget()
        self.filter_line = QLineEdit()
        filter_Layout = QHBoxLayout()
        filter_Layout.addWidget(QLabel("Filter Sections"))
        filter_Layout.addWidget(self.filter_line)

        btns = [load_btn, save_btn]

        for btn in btns:
            btn.setFixedHeight(40)

        # Add Widgets
        main_layout.addLayout(btn_layout)
        main_layout.addLayout(data_layout)
        data_layout.addLayout(filter_Layout)
        data_layout.addWidget(self.tabs)

        for btn in btns:
            btn_layout.addWidget(btn)

        btn_layout.addStretch()

        # Logic
        load_btn.clicked.connect(self.load_config)
        save_btn.clicked.connect(self.save_config)
        self.filter_line.textChanged.connect(self.upate_section_filter)

    def upate_section_filter(self):
        f = self.filter_line.text().upper().split(",")
        f = [x.strip() for x in f]
        self.build_tabs(filter=f)

    def save_config(self):

        if DEBUG:
            self.config.write(save_path="PrintNC\PrintNC_DEBUG.ini")

        else:
            dialog = QFileDialog.getSaveFileName(
                self,
                "Save Config File",
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "LinuxCNC Config File (*.INI)",
            )
            save_path = dialog[0]
            if not save_path:
                return

            self.config.write(save_path=save_path)

    def load_config(self):

        # Open the configuration file
        if DEBUG:
            self.config = LinuxCNCConfig("PrintNC\PrintNC.ini")

        else:
            dialog = QFileDialog.getOpenFileName(
                self,
                "Open Config File",
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "LinuxCNC Config File (*.INI)",
            )
            config_path = dialog[0]
            self.config = LinuxCNCConfig(config_path)

        # Build the GUI
        self.build_tabs(filter="")

    def build_tabs(self, filter):
        if not self.config:
            return

        self.tabs.clear()
        for section in self.config.sections():
            if not filter:
                tab = SectionTab(name=section, config=self.config)
                self.tabs.addTab(tab, tab.get_nice_name())
                continue

            nice_name = SectionTab.nice_name(section)

            for f in filter:
                if f in nice_name:
                    tab = SectionTab(name=section, config=self.config)
                    self.tabs.addTab(tab, tab.get_nice_name())

    def closeEvent(self, event):
        self.settings = QSettings("LinuxCNC_editor", "LinuxCNC_editor")
        self.settings.setValue("geometry", self.saveGeometry())
        QWidget.closeEvent(self, event)


palette = QPalette()
palette.setColor(QPalette.Window, QColor(27, 35, 38))
palette.setColor(QPalette.WindowText, QColor(234, 234, 234))
palette.setColor(QPalette.Base, QColor(27, 35, 38))
palette.setColor(QPalette.Disabled, QPalette.Base, QColor(27 + 5, 35 + 5, 38 + 5))
palette.setColor(QPalette.AlternateBase, QColor(12, 15, 16))
palette.setColor(QPalette.ToolTipBase, QColor(27, 35, 38))
palette.setColor(QPalette.ToolTipText, Qt.white)
palette.setColor(QPalette.Text, QColor(200, 200, 200))
palette.setColor(QPalette.Disabled, QPalette.Text, QColor(100, 100, 100))
palette.setColor(QPalette.Button, QColor(27, 35, 38))
palette.setColor(QPalette.ButtonText, Qt.white)
palette.setColor(QPalette.BrightText, QColor(100, 215, 222))
palette.setColor(QPalette.Link, QColor(126, 71, 130))
palette.setColor(QPalette.Highlight, QColor(126, 71, 130))
palette.setColor(QPalette.HighlightedText, Qt.white)
palette.setColor(QPalette.Disabled, QPalette.Light, Qt.black)
palette.setColor(QPalette.Disabled, QPalette.Shadow, QColor(12, 15, 16))

dark_palette = QPalette()
dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
dark_palette.setColor(QPalette.WindowText, Qt.white)
dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
dark_palette.setColor(QPalette.ToolTipText, Qt.white)
dark_palette.setColor(QPalette.Text, Qt.white)
dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
dark_palette.setColor(QPalette.ButtonText, Qt.white)
dark_palette.setColor(QPalette.BrightText, Qt.red)
dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
dark_palette.setColor(QPalette.HighlightedText, QColor(35, 35, 35))
dark_palette.setColor(QPalette.Active, QPalette.Button, QColor(53, 53, 53))
dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, Qt.darkGray)
dark_palette.setColor(QPalette.Disabled, QPalette.WindowText, Qt.darkGray)
dark_palette.setColor(QPalette.Disabled, QPalette.Text, Qt.darkGray)
dark_palette.setColor(QPalette.Disabled, QPalette.Light, QColor(53, 53, 53))


def main():
    app = QApplication(sys.argv)
    app.setPalette(dark_palette)
    editor = Editor()
    editor.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
