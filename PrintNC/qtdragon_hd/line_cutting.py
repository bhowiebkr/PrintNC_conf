import os
import json
import tempfile
import math
from PyQt5 import QtWidgets, QtCore, QtGui
from qtvcp.core import Status, Action, Info

STATUS = Status()
ACTION = Action()
INFO = Info()


class LineCutView(QtWidgets.QWidget):
    """Side-profile preview showing depth passes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self.cut_length = 0
        self.material_height = 0
        self.depth_per_pass = 0
        self.num_passes = 0

    def set_params(self, cut_length, material_height, depth_per_pass, num_passes):
        self.cut_length = cut_length
        self.material_height = material_height
        self.depth_per_pass = depth_per_pass
        self.num_passes = num_passes
        self.update()

    def paintEvent(self, event):
        if self.cut_length <= 0 or self.material_height <= 0 or self.num_passes <= 0:
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Dark background
        painter.fillRect(self.rect(), QtGui.QColor(30, 30, 30))

        w = self.width()
        h = self.height()
        margin_l = 60
        margin_r = 30
        margin_t = 30
        margin_b = 40

        draw_w = w - margin_l - margin_r
        draw_h = h - margin_t - margin_b

        # The view shows: X axis = cut length, Y axis = Z height (0 at spoilboard, material_height at top)
        # Add some headroom above material
        total_z = self.material_height * 1.3
        scale_x = draw_w / self.cut_length
        scale_y = draw_h / total_z
        scale = min(scale_x, scale_y)

        actual_w = self.cut_length * scale
        actual_h = total_z * scale

        # Position: spoilboard at bottom
        origin_x = margin_l
        origin_y = margin_t + actual_h  # bottom = Z0 (spoilboard)

        def tx(x):
            return origin_x + x * scale

        def tz(z):
            return origin_y - z * scale

        # Draw spoilboard
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(60, 40, 20))
        painter.drawRect(QtCore.QRectF(tx(0), tz(0), actual_w, 20))

        # Draw material block
        painter.setBrush(QtGui.QColor(80, 80, 100, 180))
        painter.setPen(QtGui.QPen(QtGui.QColor(120, 120, 140), 2))
        mat_top = tz(self.material_height)
        mat_h = self.material_height * scale
        painter.drawRect(QtCore.QRectF(tx(0), mat_top, actual_w, mat_h))

        # Draw each pass
        for p in range(self.num_passes):
            z_level = self.material_height - (p + 1) * self.depth_per_pass
            if z_level < 0:
                z_level = 0

            # Color passes from light to dark green
            alpha = 80 + int(175 * (p + 1) / self.num_passes)
            green = 255 - int(150 * p / max(self.num_passes - 1, 1))
            pen = QtGui.QPen(QtGui.QColor(0, green, 0, alpha), 2)
            painter.setPen(pen)

            y_line = tz(z_level)
            painter.drawLine(QtCore.QPointF(tx(self.cut_length), y_line),
                             QtCore.QPointF(tx(0), y_line))

            # Pass label on the right
            painter.setPen(QtGui.QColor(150, 150, 150))
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(QtCore.QPointF(tx(self.cut_length) + 4, y_line + 4),
                             "Z{:.1f}".format(z_level))

        # Draw Z axis labels
        painter.setPen(QtGui.QColor(120, 120, 120))
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)

        # Z0 label (spoilboard)
        painter.drawText(QtCore.QPointF(origin_x - 50, tz(0) + 4), "Z0 (bed)")

        # Material top label
        painter.drawText(QtCore.QPointF(origin_x - 50, mat_top + 4),
                         "Z{:.0f}".format(self.material_height))

        # Cut length label
        painter.drawText(QtCore.QPointF(tx(self.cut_length / 2) - 20, tz(0) + 30),
                         "{:.0f} mm".format(self.cut_length))

        # Draw Z axis line
        painter.setPen(QtGui.QPen(QtGui.QColor(80, 80, 80), 1))
        painter.drawLine(QtCore.QPointF(tx(0), tz(0)),
                         QtCore.QPointF(tx(0), tz(self.material_height * 1.15)))

        # Draw origin marker
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 50, 50), 2))
        ox, oy = tx(0), tz(0)
        painter.drawLine(QtCore.QPointF(ox - 8, oy), QtCore.QPointF(ox + 8, oy))
        painter.drawLine(QtCore.QPointF(ox, oy - 8), QtCore.QPointF(ox, oy + 8))

        painter.end()


LINE_CUTTING_CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'line_cutting.conf')


class LineCutting(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_params()
        self._connect_signals()
        self._update_preview()

    def _build_ui(self):
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(12)

        # Left side: parameters
        params_group = QtWidgets.QGroupBox("Line Cutting Parameters")
        params_layout = QtWidgets.QFormLayout(params_group)
        params_layout.setSpacing(10)
        params_layout.setContentsMargins(12, 20, 12, 12)

        float_val = QtGui.QDoubleValidator(0.001, 99999.0, 3)
        int_val = QtGui.QIntValidator(1, 99999)

        def make_input(default, validator=float_val):
            le = QtWidgets.QLineEdit(str(default))
            le.setValidator(validator)
            le.setMinimumHeight(30)
            return le

        self.input_cut_length = make_input(100)
        params_layout.addRow("Cut Length (mm):", self.input_cut_length)

        pos_val = QtGui.QDoubleValidator(-99999.0, 99999.0, 3)
        self.input_cut_position = make_input(0, pos_val)
        params_layout.addRow("Cut Position (mm):", self.input_cut_position)

        self.input_material_height = make_input(20)
        params_layout.addRow("Material Height (mm):", self.input_material_height)

        self.input_depth_per_pass = make_input(1)
        params_layout.addRow("Depth Per Pass (mm):", self.input_depth_per_pass)

        self.input_rpm = make_input(22000, int_val)
        params_layout.addRow("Spindle Speed (RPM):", self.input_rpm)

        self.input_feed = make_input(6000, int_val)
        params_layout.addRow("Feed Rate (mm/min):", self.input_feed)

        self.input_plunge_feed = make_input(1000, int_val)
        params_layout.addRow("Plunge Feed (mm/min):", self.input_plunge_feed)

        # Direction radio buttons
        dir_group = QtWidgets.QGroupBox("Cut Direction")
        dir_layout = QtWidgets.QVBoxLayout(dir_group)
        self.radio_x = QtWidgets.QRadioButton("Along X")
        self.radio_y = QtWidgets.QRadioButton("Along Y")
        self.radio_x.setChecked(True)
        dir_layout.addWidget(self.radio_x)
        dir_layout.addWidget(self.radio_y)
        params_layout.addRow(dir_group)

        main_layout.addWidget(params_group, 1)

        # Right side: visual preview and buttons
        right_layout = QtWidgets.QVBoxLayout()
        right_layout.setSpacing(8)

        # Visual preview (side profile)
        preview_group = QtWidgets.QGroupBox("Side Profile Preview")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(4, 16, 4, 4)
        self.preview = LineCutView()
        preview_layout.addWidget(self.preview)
        right_layout.addWidget(preview_group, 1)

        # Info label
        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        right_layout.addWidget(self.lbl_info)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()

        self.btn_save = QtWidgets.QPushButton("Save G-code")
        self.btn_save.setMinimumHeight(40)
        btn_layout.addWidget(self.btn_save)

        self.btn_send = QtWidgets.QPushButton("Send to LinuxCNC")
        self.btn_send.setMinimumHeight(40)
        self.btn_send.setStyleSheet("QPushButton { font-weight: bold; }")
        btn_layout.addWidget(self.btn_send)

        right_layout.addLayout(btn_layout)
        main_layout.addLayout(right_layout, 2)

    def _connect_signals(self):
        self.btn_save.clicked.connect(self._save_gcode)
        self.btn_send.clicked.connect(self._send_to_linuxcnc)
        for w in [self.input_cut_length, self.input_cut_position,
                  self.input_material_height,
                  self.input_depth_per_pass, self.input_rpm,
                  self.input_feed, self.input_plunge_feed]:
            w.textChanged.connect(self._update_preview)
            w.textChanged.connect(self._save_params)
        self.radio_x.toggled.connect(self._update_preview)
        self.radio_x.toggled.connect(self._save_params)

    def _param_widgets(self):
        return {
            'cut_length': self.input_cut_length,
            'cut_position': self.input_cut_position,
            'material_height': self.input_material_height,
            'depth_per_pass': self.input_depth_per_pass,
            'rpm': self.input_rpm,
            'feed': self.input_feed,
            'plunge_feed': self.input_plunge_feed,
        }

    def _save_params(self):
        data = {}
        for key, w in self._param_widgets().items():
            data[key] = w.text()
        data['along_x'] = self.radio_x.isChecked()
        try:
            with open(LINE_CUTTING_CONF, 'w') as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def _load_params(self):
        try:
            with open(LINE_CUTTING_CONF, 'r') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        for key, w in self._param_widgets().items():
            if key in data:
                w.setText(str(data[key]))
        if 'along_x' in data:
            self.radio_x.setChecked(data['along_x'])
            self.radio_y.setChecked(not data['along_x'])

    def _get_float(self, widget, fallback=1.0):
        try:
            v = float(widget.text())
            return v if v > 0 else fallback
        except (ValueError, ZeroDivisionError):
            return fallback

    def _compute_passes(self):
        material_height = self._get_float(self.input_material_height, 20)
        depth_per_pass = self._get_float(self.input_depth_per_pass, 1)
        num_passes = math.ceil(material_height / depth_per_pass)
        return num_passes, depth_per_pass

    def _update_preview(self):
        cut_length = self._get_float(self.input_cut_length, 100)
        material_height = self._get_float(self.input_material_height, 20)
        num_passes, depth_per_pass = self._compute_passes()

        self.preview.set_params(cut_length, material_height, depth_per_pass, num_passes)

        direction = "X" if self.radio_x.isChecked() else "Y"
        self.lbl_info.setText(
            "Passes: {}  |  Depth/pass: {:.1f} mm  |  Total depth: {:.1f} mm  |  Direction: {}".format(
                num_passes, depth_per_pass, material_height, direction))

    def _generate_gcode(self):
        cut_length = self._get_float(self.input_cut_length, 100)
        try:
            cut_pos = float(self.input_cut_position.text())
        except ValueError:
            cut_pos = 0
        material_height = self._get_float(self.input_material_height, 20)
        depth_per_pass = self._get_float(self.input_depth_per_pass, 1)
        rpm = int(self._get_float(self.input_rpm, 22000))
        feed = int(self._get_float(self.input_feed, 6000))
        plunge_feed = int(self._get_float(self.input_plunge_feed, 1000))
        along_x = self.radio_x.isChecked()
        num_passes = math.ceil(material_height / depth_per_pass)

        cut_axis = "X" if along_x else "Y"
        pos_axis = "Y" if along_x else "X"

        lines = []
        lines.append("%")
        lines.append("(Line cutting operation)")
        lines.append("(Length={:.1f} Position {}{:.1f} Material Height={:.1f} Depth/Pass={:.1f})".format(
            cut_length, pos_axis, cut_pos, material_height, depth_per_pass))
        lines.append("(Passes={} RPM={} Feed={})".format(num_passes, rpm, feed))
        lines.append("")
        lines.append("G21 (metric)")
        lines.append("G90 (absolute positioning)")
        lines.append("G40 (cancel cutter comp)")
        lines.append("G49 (cancel tool length offset)")
        lines.append("G64 P0.03 (path blending)")
        lines.append("G17 (XY plane)")
        lines.append("")
        lines.append("G53 G0 Z-5 (retract to safe machine Z)")
        lines.append("G0 {}{:.1f} {}{:.1f} (rapid to start)".format(
            cut_axis, cut_length, pos_axis, cut_pos))
        lines.append("S{} M3 (start spindle)".format(rpm))
        lines.append("G4 P2 (wait for spindle)")
        lines.append("")

        for p in range(num_passes):
            z_level = material_height - (p + 1) * depth_per_pass
            if z_level < 0:
                z_level = 0

            lines.append("(Pass {} of {} - Z{:.2f})".format(p + 1, num_passes, z_level))
            lines.append("G0 {}{:.1f}".format(cut_axis, cut_length))
            lines.append("G1 Z{:.2f} F{}".format(z_level, plunge_feed))
            lines.append("G1 {}0 F{}".format(cut_axis, feed))
            lines.append("G0 Z{:.1f}".format(material_height + 5))

        lines.append("")
        lines.append("G53 G0 Z-5 (retract to safe machine Z)")
        lines.append("M5 (stop spindle)")
        lines.append("G0 X0 Y0 (return to origin)")
        lines.append("M2 (end program)")
        lines.append("%")

        return "\n".join(lines)

    def _save_gcode(self):
        gcode = self._generate_gcode()
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Line Cutting G-code", os.path.expanduser("~/GCODE/line_cutting.ngc"),
            "G-code Files (*.ngc *.nc *.gcode);;All Files (*)")
        if fname:
            with open(fname, 'w') as f:
                f.write(gcode + "\n")
            self.lbl_info.setText("Saved to: " + fname)

    def _send_to_linuxcnc(self):
        gcode = self._generate_gcode()
        tmp = os.path.join(tempfile.gettempdir(), "line_cutting_op.ngc")
        with open(tmp, 'w') as f:
            f.write(gcode + "\n")
        ACTION.OPEN_PROGRAM(tmp)
        self.lbl_info.setText(self.lbl_info.text() + "  |  Loaded into LinuxCNC")
