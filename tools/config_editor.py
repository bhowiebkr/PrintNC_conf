import sys
import logging
import os
from tkinter import dialog

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from linuxcnc_config import LinuxCNCConfig


DEBUG = True


class M(dict):
    def __setitem__(self, key, value):
        if key in self:
            items = self[key]
            new = value[0]
            if new not in items:
                items.append(new)
        else:
            super(M, self).__setitem__(key, value)


class Editor(QWidget):
    def __init__(self, parent=None):
        super(Editor, self).__init__(parent)
        self.setWindowTitle("PrintNC Config Editor")

        self.settings = QSettings("cnc_editor", "cnc_editor")

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

        btns = [load_btn, save_btn]

        for btn in btns:
            btn.setFixedHeight(40)

        # Add Widgets
        main_layout.addLayout(btn_layout)
        main_layout.addLayout(data_layout)

        for btn in btns:
            btn_layout.addWidget(btn)

        btn_layout.addStretch()

        # Logic
        load_btn.clicked.connect(self.load_config)
        save_btn.clicked.connect(self.save_config)

    def save_config(self):

        if DEBUG:
            self.config.write(
                save_path="/home/howard/linuxcnc/configs/PrintNC/PrintNC_DEBUG.ini"
            )

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

        if DEBUG:
            self.config = LinuxCNCConfig(
                "/home/howard/linuxcnc/configs/PrintNC/PrintNC.ini"
            )

        else:
            dialog = QFileDialog.getOpenFileName(
                self,
                "Open Config File",
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "LinuxCNC Config File (*.INI)",
            )
            config_path = dialog[0]
            self.config = LinuxCNCConfig(config_path)

    def closeEvent(self, event):
        self.settings = QSettings("cnc_editor", "cnc_editor")
        self.settings.setValue("geometry", self.saveGeometry())
        QWidget.closeEvent(self, event)


def main():
    app = QApplication(sys.argv)
    editor = Editor()
    editor.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
