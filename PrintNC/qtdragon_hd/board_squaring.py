import os
import tempfile
import math
from PyQt5 import QtWidgets, QtCore, QtGui
from qtvcp.core import Status, Action, Info

STATUS = Status()
ACTION = Action()
INFO = Info()


class BoardPreview(QtWidgets.QWidget):
    """Top-down + side view of the board showing operation order."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self.board_x = 0
        self.board_y = 0
        self.board_z = 0
        self.ops = []  # list of operation names that are enabled

    def set_params(self, board_x, board_y, board_z, ops, depth_per_pass=1):
        self.board_x = board_x
        self.board_y = board_y
        self.board_z = board_z
        self.ops = ops
        self.depth_per_pass = depth_per_pass
        self.update()

    def paintEvent(self, event):
        if self.board_x <= 0 or self.board_y <= 0 or self.board_z <= 0:
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor(30, 30, 30))

        w = self.width()
        h = self.height()

        # Split into top view (upper) and side view (lower)
        top_h = int(h * 0.6)
        side_h = h - top_h

        # --- TOP VIEW ---
        margin = 50
        top_draw_w = w - 2 * margin
        top_draw_h = top_h - 2 * margin

        scale_x = top_draw_w / self.board_x
        scale_y = top_draw_h / self.board_y
        scale = min(scale_x, scale_y) * 0.85

        actual_w = self.board_x * scale
        actual_h = self.board_y * scale
        ox = margin + (top_draw_w - actual_w) / 2
        oy = margin + (top_draw_h - actual_h) / 2

        def tx(x):
            return ox + x * scale

        def ty(y):
            return oy + actual_h - y * scale

        # Board outline
        painter.setPen(QtGui.QPen(QtGui.QColor(120, 120, 140), 2))
        painter.setBrush(QtGui.QColor(80, 70, 50, 180))
        painter.drawRect(QtCore.QRectF(tx(0), ty(self.board_y), actual_w, actual_h))

        # Label
        painter.setPen(QtGui.QColor(180, 180, 180))
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QtCore.QPointF(margin, 20), "Top View")

        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)

        # Dimension labels
        painter.setPen(QtGui.QColor(150, 150, 150))
        painter.drawText(QtCore.QPointF(tx(self.board_x / 2) - 15, ty(0) + 18),
                         "X: {:.0f}".format(self.board_x))
        painter.save()
        painter.translate(tx(0) - 12, ty(self.board_y / 2) + 10)
        painter.rotate(-90)
        painter.drawText(0, 0, "Y: {:.0f}".format(self.board_y))
        painter.restore()

        # Draw operation indicators
        op_num = 1
        arrow_len = 20

        # Top surface
        if "top" in self.ops:
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 255, 0), 2))
            # Draw surfacing lines
            for i in range(5):
                frac = (i + 1) / 6
                y_line = ty(self.board_y * frac)
                painter.drawLine(QtCore.QPointF(tx(self.board_x), y_line),
                                 QtCore.QPointF(tx(0), y_line))
            painter.setPen(QtGui.QColor(0, 255, 0))
            painter.drawText(QtCore.QPointF(tx(self.board_x / 2) - 20,
                             ty(self.board_y / 2) + 5),
                             "{} TOP".format(op_num))
            op_num += 1

        # +X end (end grain)
        if "+x" in self.ops:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 100, 100), 3))
            x_pos = tx(self.board_x) + 3
            painter.drawLine(QtCore.QPointF(x_pos, ty(self.board_y)),
                             QtCore.QPointF(x_pos, ty(0)))
            painter.setPen(QtGui.QColor(255, 100, 100))
            painter.drawText(QtCore.QPointF(x_pos + 4, ty(self.board_y / 2) + 5),
                             "{} +X".format(op_num))
            op_num += 1

        # -X end (end grain)
        if "-x" in self.ops:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 150, 50), 3))
            x_pos = tx(0) - 3
            painter.drawLine(QtCore.QPointF(x_pos, ty(self.board_y)),
                             QtCore.QPointF(x_pos, ty(0)))
            painter.setPen(QtGui.QColor(255, 150, 50))
            painter.drawText(QtCore.QPointF(x_pos - 35, ty(self.board_y / 2) + 5),
                             "{} -X".format(op_num))
            op_num += 1

        # +Y side
        if "+y" in self.ops:
            painter.setPen(QtGui.QPen(QtGui.QColor(100, 150, 255), 3))
            y_pos = ty(self.board_y) - 3
            painter.drawLine(QtCore.QPointF(tx(0), y_pos),
                             QtCore.QPointF(tx(self.board_x), y_pos))
            painter.setPen(QtGui.QColor(100, 150, 255))
            painter.drawText(QtCore.QPointF(tx(self.board_x / 2) - 10, y_pos - 6),
                             "{} +Y".format(op_num))
            op_num += 1

        # -Y side
        if "-y" in self.ops:
            painter.setPen(QtGui.QPen(QtGui.QColor(200, 100, 255), 3))
            y_pos = ty(0) + 3
            painter.drawLine(QtCore.QPointF(tx(0), y_pos),
                             QtCore.QPointF(tx(self.board_x), y_pos))
            painter.setPen(QtGui.QColor(200, 100, 255))
            painter.drawText(QtCore.QPointF(tx(self.board_x / 2) - 10, y_pos + 14),
                             "{} -Y".format(op_num))
            op_num += 1

        # --- SIDE VIEW ---
        side_margin_l = 60
        side_margin_r = 30
        side_margin_t = 20
        side_margin_b = 25

        side_draw_w = w - side_margin_l - side_margin_r
        side_draw_h = side_h - side_margin_t - side_margin_b

        s_scale_x = side_draw_w / self.board_x
        s_scale_z = side_draw_h / (self.board_z * 1.3)
        s_scale = min(s_scale_x, s_scale_z)

        s_actual_w = self.board_x * s_scale
        s_actual_h = self.board_z * s_scale
        s_ox = side_margin_l
        s_oy = top_h + side_margin_t + self.board_z * 1.2 * s_scale

        def stx(x):
            return s_ox + x * s_scale

        def stz(z):
            return s_oy - z * s_scale

        # Divider line
        painter.setPen(QtGui.QPen(QtGui.QColor(60, 60, 60), 1))
        painter.drawLine(QtCore.QPointF(0, top_h), QtCore.QPointF(w, top_h))

        # Label
        painter.setPen(QtGui.QColor(180, 180, 180))
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QtCore.QPointF(margin, top_h + 16), "Side View")
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)

        # Spoilboard
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(60, 40, 20))
        painter.drawRect(QtCore.QRectF(stx(0) - 10, stz(0), s_actual_w + 20, 15))

        # Board side profile
        painter.setPen(QtGui.QPen(QtGui.QColor(120, 120, 140), 2))
        painter.setBrush(QtGui.QColor(80, 70, 50, 180))
        painter.drawRect(QtCore.QRectF(stx(0), stz(self.board_z), s_actual_w, s_actual_h))

        # Draw depth pass lines for side cuts
        has_sides = any(op in self.ops for op in ["+x", "-x", "+y", "-y"])
        if has_sides and self.depth_per_pass > 0:
            num_passes = math.ceil(self.board_z / self.depth_per_pass)
            for p in range(num_passes):
                z_level = self.board_z - (p + 1) * self.depth_per_pass
                if z_level < 0:
                    z_level = 0
                alpha = 80 + int(175 * (p + 1) / num_passes)
                green = 255 - int(150 * p / max(num_passes - 1, 1))
                painter.setPen(QtGui.QPen(QtGui.QColor(0, green, 0, alpha), 2))
                y_line = stz(z_level)
                painter.drawLine(QtCore.QPointF(stx(0), y_line),
                                 QtCore.QPointF(stx(self.board_x), y_line))

        # Z height label
        painter.setPen(QtGui.QColor(150, 150, 150))
        painter.drawText(QtCore.QPointF(s_ox - 55, stz(self.board_z / 2) + 4),
                         "Z: {:.1f}".format(self.board_z))

        # Origin marker
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 50, 50), 2))
        painter.drawLine(QtCore.QPointF(stx(0) - 6, stz(0)),
                         QtCore.QPointF(stx(0) + 6, stz(0)))
        painter.drawLine(QtCore.QPointF(stx(0), stz(0) - 6),
                         QtCore.QPointF(stx(0), stz(0) + 6))

        painter.end()


class BoardSquaring(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._connect_signals()
        self._update_preview()

    def _build_ui(self):
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(12)

        # Left side: parameters
        left_layout = QtWidgets.QVBoxLayout()

        params_group = QtWidgets.QGroupBox("Board Dimensions")
        params_layout = QtWidgets.QFormLayout(params_group)
        params_layout.setSpacing(8)
        params_layout.setContentsMargins(12, 20, 12, 12)

        float_val = QtGui.QDoubleValidator(0.001, 99999.0, 3)
        int_val = QtGui.QIntValidator(1, 99999)

        def make_input(default, validator=float_val):
            le = QtWidgets.QLineEdit(str(default))
            le.setValidator(validator)
            le.setMinimumHeight(28)
            return le

        self.input_x = make_input(100)
        params_layout.addRow("X Length (mm):", self.input_x)

        self.input_y = make_input(74)
        params_layout.addRow("Y Width (mm):", self.input_y)

        self.input_z = make_input(16.6)
        params_layout.addRow("Z Height (mm):", self.input_z)

        left_layout.addWidget(params_group)

        # Tool & cutting params
        tool_group = QtWidgets.QGroupBox("Cutting Parameters")
        tool_layout = QtWidgets.QFormLayout(tool_group)
        tool_layout.setSpacing(8)
        tool_layout.setContentsMargins(12, 20, 12, 12)

        self.input_tool_dia = make_input(8)
        tool_layout.addRow("Tool Diameter (mm):", self.input_tool_dia)

        self.input_stepover = make_input(5)
        tool_layout.addRow("Surfacing Stepover (mm):", self.input_stepover)

        self.input_depth_per_pass = make_input(1)
        tool_layout.addRow("Side Depth/Pass (mm):", self.input_depth_per_pass)

        self.input_surface_depth = make_input(0.5)
        tool_layout.addRow("Surface Depth (mm):", self.input_surface_depth)

        self.input_rpm = make_input(22000, int_val)
        tool_layout.addRow("Spindle Speed (RPM):", self.input_rpm)

        self.input_feed = make_input(6000, int_val)
        tool_layout.addRow("Feed Rate (mm/min):", self.input_feed)

        self.input_plunge_feed = make_input(1000, int_val)
        tool_layout.addRow("Plunge Feed (mm/min):", self.input_plunge_feed)

        left_layout.addWidget(tool_group)

        # Operations to include
        ops_group = QtWidgets.QGroupBox("Operations (in order)")
        ops_layout = QtWidgets.QVBoxLayout(ops_group)
        ops_layout.setSpacing(4)

        self.chk_top = QtWidgets.QCheckBox("1. Surface top")
        self.chk_top.setChecked(True)
        ops_layout.addWidget(self.chk_top)

        self.chk_plus_x = QtWidgets.QCheckBox("2. Mill +X end (end grain)")
        self.chk_plus_x.setChecked(True)
        ops_layout.addWidget(self.chk_plus_x)

        self.chk_minus_x = QtWidgets.QCheckBox("3. Mill -X end (end grain)")
        self.chk_minus_x.setChecked(True)
        ops_layout.addWidget(self.chk_minus_x)

        self.chk_plus_y = QtWidgets.QCheckBox("4. Mill +Y side")
        self.chk_plus_y.setChecked(True)
        ops_layout.addWidget(self.chk_plus_y)

        self.chk_minus_y = QtWidgets.QCheckBox("5. Mill -Y side")
        self.chk_minus_y.setChecked(True)
        ops_layout.addWidget(self.chk_minus_y)

        left_layout.addWidget(ops_group)
        left_layout.addStretch()

        main_layout.addLayout(left_layout, 1)

        # Right side: preview and buttons
        right_layout = QtWidgets.QVBoxLayout()
        right_layout.setSpacing(8)

        preview_group = QtWidgets.QGroupBox("Board Preview")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(4, 16, 4, 4)
        self.preview = BoardPreview()
        preview_layout.addWidget(self.preview)
        right_layout.addWidget(preview_group, 1)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        right_layout.addWidget(self.lbl_info)

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
        for w in [self.input_x, self.input_y, self.input_z,
                  self.input_tool_dia, self.input_stepover,
                  self.input_depth_per_pass]:
            w.textChanged.connect(self._update_preview)
        for chk in [self.chk_top, self.chk_plus_x, self.chk_minus_x,
                    self.chk_plus_y, self.chk_minus_y]:
            chk.toggled.connect(self._update_preview)

    def _get_float(self, widget, fallback=1.0):
        try:
            v = float(widget.text())
            return v if v > 0 else fallback
        except (ValueError, ZeroDivisionError):
            return fallback

    def _enabled_ops(self):
        ops = []
        if self.chk_top.isChecked():
            ops.append("top")
        if self.chk_plus_x.isChecked():
            ops.append("+x")
        if self.chk_minus_x.isChecked():
            ops.append("-x")
        if self.chk_plus_y.isChecked():
            ops.append("+y")
        if self.chk_minus_y.isChecked():
            ops.append("-y")
        return ops

    def _update_preview(self):
        board_x = self._get_float(self.input_x, 100)
        board_y = self._get_float(self.input_y, 74)
        board_z = self._get_float(self.input_z, 16.6)
        ops = self._enabled_ops()

        depth_per_pass = self._get_float(self.input_depth_per_pass, 1)
        self.preview.set_params(board_x, board_y, board_z, ops, depth_per_pass)

        depth_per_pass = self._get_float(self.input_depth_per_pass, 1)
        side_passes = math.ceil(board_z / depth_per_pass)
        tool_dia = self._get_float(self.input_tool_dia, 8)
        stepover = self._get_float(self.input_stepover, 5)
        padded_y = board_y + tool_dia * 2
        surface_passes = math.ceil(padded_y / stepover)

        info_parts = []
        if "top" in ops:
            info_parts.append("Top: {} passes".format(surface_passes))
        side_count = len([o for o in ops if o != "top"])
        if side_count:
            info_parts.append("Sides: {} passes/side x {} sides".format(
                side_passes, side_count))
        self.lbl_info.setText("  |  ".join(info_parts))

    def _gen_surfacing(self, lines, board_x, board_y, board_z, tool_dia,
                       stepover, depth, feed, safe_z):
        """Surface the top - same logic as surfacing tab."""
        padded_y = board_y + tool_dia * 2
        num_cuts = math.ceil(padded_y / stepover)
        actual_stepover = padded_y / num_cuts

        lines.append("(--- SURFACE TOP ---)")
        for i in range(num_cuts):
            y_pos = i * actual_stepover
            lines.append("G0 X{:.1f} Y{:.2f}".format(board_x, y_pos))
            lines.append("G1 Z{:.2f} F{}".format(board_z - depth, feed))
            lines.append("G1 X0 F{}".format(feed))
            lines.append("G0 Z{:.1f}".format(safe_z))
        lines.append("")

    def _gen_side_cut(self, lines, axis, position, cut_length, board_z,
                      depth_per_pass, feed, plunge_feed, safe_z, climb_positive):
        """Mill one side. climb_positive=True means cut in + direction for climb."""
        num_passes = math.ceil(board_z / depth_per_pass)

        if axis == "X":
            # Cutting along Y at fixed X position
            for p in range(num_passes):
                z_level = board_z - (p + 1) * depth_per_pass
                if z_level < 0:
                    z_level = 0
                if climb_positive:
                    # Climb cut in +Y direction: start Y=0, cut to Y=cut_length
                    lines.append("G0 X{:.2f} Y0".format(position))
                    lines.append("G1 Z{:.2f} F{}".format(z_level, plunge_feed))
                    lines.append("G1 Y{:.1f} F{}".format(cut_length, feed))
                else:
                    # Climb cut in -Y direction: start Y=cut_length, cut to Y=0
                    lines.append("G0 X{:.2f} Y{:.1f}".format(position, cut_length))
                    lines.append("G1 Z{:.2f} F{}".format(z_level, plunge_feed))
                    lines.append("G1 Y0 F{}".format(feed))
                lines.append("G0 Z{:.1f}".format(safe_z))
        else:
            # Cutting along X at fixed Y position
            for p in range(num_passes):
                z_level = board_z - (p + 1) * depth_per_pass
                if z_level < 0:
                    z_level = 0
                if climb_positive:
                    # Climb cut in +X direction: start X=0, cut to X=cut_length
                    lines.append("G0 Y{:.2f} X0".format(position))
                    lines.append("G1 Z{:.2f} F{}".format(z_level, plunge_feed))
                    lines.append("G1 X{:.1f} F{}".format(cut_length, feed))
                else:
                    # Climb cut in -X direction: start X=cut_length, cut to X=0
                    lines.append("G0 Y{:.2f} X{:.1f}".format(position, cut_length))
                    lines.append("G1 Z{:.2f} F{}".format(z_level, plunge_feed))
                    lines.append("G1 X0 F{}".format(feed))
                lines.append("G0 Z{:.1f}".format(safe_z))

    def _generate_gcode(self):
        board_x = self._get_float(self.input_x, 100)
        board_y = self._get_float(self.input_y, 74)
        board_z = self._get_float(self.input_z, 16.6)
        tool_dia = self._get_float(self.input_tool_dia, 8)
        stepover = self._get_float(self.input_stepover, 5)
        depth_per_pass = self._get_float(self.input_depth_per_pass, 1)
        surface_depth = self._get_float(self.input_surface_depth, 0.5)
        rpm = int(self._get_float(self.input_rpm, 22000))
        feed = int(self._get_float(self.input_feed, 6000))
        plunge_feed = int(self._get_float(self.input_plunge_feed, 1000))
        ops = self._enabled_ops()

        safe_z = board_z + 5

        lines = []
        lines.append("%")
        lines.append("(Board squaring operation)")
        lines.append("(Board: X={:.1f} Y={:.1f} Z={:.1f})".format(
            board_x, board_y, board_z))
        lines.append("(Tool Dia={:.1f} Stepover={:.1f} Depth/Pass={:.1f})".format(
            tool_dia, stepover, depth_per_pass))
        lines.append("")
        lines.append("G21 (metric)")
        lines.append("G90 (absolute positioning)")
        lines.append("G40 (cancel cutter comp)")
        lines.append("G49 (cancel tool length offset)")
        lines.append("G64 P0.03 (path blending)")
        lines.append("G17 (XY plane)")
        lines.append("")
        lines.append("G53 G0 Z-5 (retract to safe machine Z)")
        lines.append("S{} M3 (start spindle)".format(rpm))
        lines.append("G4 P2 (wait for spindle)")
        lines.append("")

        # 1. Surface top
        if "top" in ops:
            self._gen_surfacing(lines, board_x, board_y, board_z, tool_dia,
                                stepover, surface_depth, feed, safe_z)
            lines.append("G53 G0 Z-5 (safe retract between ops)")
            lines.append("")

        # 2. +X end (end grain) - cut along Y at X=board_x
        #    Tool outside at +X, board to left: climb = -Y
        if "+x" in ops:
            lines.append("(--- MILL +X END - end grain ---)")
            self._gen_side_cut(lines, "X", board_x, board_y, board_z,
                               depth_per_pass, feed, plunge_feed, safe_z, False)
            lines.append("G53 G0 Z-5 (safe retract between ops)")
            lines.append("")

        # 3. -X end (end grain) - cut along Y at X=0
        #    Tool outside at -X, board to right: climb = +Y
        if "-x" in ops:
            lines.append("(--- MILL -X END - end grain ---)")
            self._gen_side_cut(lines, "X", 0, board_y, board_z,
                               depth_per_pass, feed, plunge_feed, safe_z, True)
            lines.append("G53 G0 Z-5 (safe retract between ops)")
            lines.append("")

        # 4. +Y side - cut along X at Y=board_y
        #    Tool outside at +Y, board below: climb = +X
        if "+y" in ops:
            lines.append("(--- MILL +Y SIDE ---)")
            self._gen_side_cut(lines, "Y", board_y, board_x, board_z,
                               depth_per_pass, feed, plunge_feed, safe_z, True)
            lines.append("G53 G0 Z-5 (safe retract between ops)")
            lines.append("")

        # 5. -Y side - cut along X at Y=0
        #    Tool outside at -Y, board above: climb = -X
        if "-y" in ops:
            lines.append("(--- MILL -Y SIDE ---)")
            self._gen_side_cut(lines, "Y", 0, board_x, board_z,
                               depth_per_pass, feed, plunge_feed, safe_z, False)
            lines.append("G53 G0 Z-5 (safe retract between ops)")
            lines.append("")

        lines.append("G53 G0 Z-5 (final retract)")
        lines.append("M5 (stop spindle)")
        lines.append("G0 X0 Y0 (return to origin)")
        lines.append("M2 (end program)")
        lines.append("%")

        return "\n".join(lines)

    def _save_gcode(self):
        gcode = self._generate_gcode()
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Board Squaring G-code",
            os.path.expanduser("~/GCODE/board_squaring.ngc"),
            "G-code Files (*.ngc *.nc *.gcode);;All Files (*)")
        if fname:
            with open(fname, 'w') as f:
                f.write(gcode + "\n")
            self.lbl_info.setText("Saved to: " + fname)

    def _send_to_linuxcnc(self):
        gcode = self._generate_gcode()
        tmp = os.path.join(tempfile.gettempdir(), "board_squaring_op.ngc")
        with open(tmp, 'w') as f:
            f.write(gcode + "\n")
        ACTION.OPEN_PROGRAM(tmp)
        self.lbl_info.setText(self.lbl_info.text() + "  |  Loaded into LinuxCNC")
