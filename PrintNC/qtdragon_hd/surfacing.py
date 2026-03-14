import os
import tempfile
from PyQt5 import QtWidgets, QtCore, QtGui
from qtvcp.core import Status, Action, Info

STATUS = Status()
ACTION = Action()
INFO = Info()


class ToolpathView(QtWidgets.QWidget):
    """Visual preview of the surfacing toolpath."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self.toolpath = []       # list of (x0, y0, x1, y1, is_cut) segments
        self.work_x = 0
        self.work_y = 0
        self.tool_dia = 0

    def set_toolpath(self, toolpath, work_x, work_y, tool_dia):
        self.toolpath = toolpath
        self.work_x = work_x
        self.work_y = work_y
        self.tool_dia = tool_dia
        self.update()

    def paintEvent(self, event):
        if not self.toolpath or self.work_x == 0 or self.work_y == 0:
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Dark background
        painter.fillRect(self.rect(), QtGui.QColor(30, 30, 30))

        w = self.width()
        h = self.height()
        margin = 40

        draw_w = w - 2 * margin
        draw_h = h - 2 * margin

        # Scale to fit, maintaining aspect ratio
        scale_x = draw_w / self.work_x
        scale_y = draw_h / self.work_y
        scale = min(scale_x, scale_y)

        # Center the drawing
        actual_w = self.work_x * scale
        actual_h = self.work_y * scale
        offset_x = margin + (draw_w - actual_w) / 2
        offset_y = margin + (draw_h - actual_h) / 2

        def tx(x):
            return offset_x + x * scale

        def ty(y):
            # Flip Y so 0 is at bottom
            return offset_y + actual_h - y * scale

        # Draw workpiece outline
        pen = QtGui.QPen(QtGui.QColor(80, 80, 80), 2)
        painter.setPen(pen)
        painter.drawRect(QtCore.QRectF(tx(0), ty(self.work_y), actual_w, actual_h))

        # Draw axis labels
        painter.setPen(QtGui.QColor(120, 120, 120))
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(QtCore.QPointF(tx(self.work_x / 2) - 10, ty(0) + 18), "X: {:.0f}".format(self.work_x))
        painter.save()
        painter.translate(tx(0) - 8, ty(self.work_y / 2) + 10)
        painter.rotate(-90)
        painter.drawText(0, 0, "Y: {:.0f}".format(self.work_y))
        painter.restore()

        # Draw tool width indicator in legend area
        tool_screen_w = self.tool_dia * scale
        if tool_screen_w > 1:
            painter.setPen(QtGui.QPen(QtGui.QColor(100, 200, 255, 80), 1))
            painter.drawText(QtCore.QPointF(margin, h - 8),
                             "Tool: {:.1f}mm".format(self.tool_dia))

        # Draw rapid moves (thin grey dashed)
        pen_rapid = QtGui.QPen(QtGui.QColor(100, 100, 100, 120), 1, QtCore.Qt.DashLine)

        # Draw cutting moves with tool width
        for (x0, y0, x1, y1, is_cut) in self.toolpath:
            if is_cut:
                # Draw tool swath
                if tool_screen_w > 2:
                    swath_color = QtGui.QColor(0, 180, 0, 40)
                    painter.setPen(QtCore.Qt.NoPen)
                    painter.setBrush(swath_color)
                    # Determine swath rectangle based on direction
                    half_tool = self.tool_dia / 2
                    sx0 = min(tx(x0), tx(x1)) - half_tool * scale
                    sy0 = min(ty(y0), ty(y1)) - half_tool * scale
                    sw = abs(tx(x1) - tx(x0)) + self.tool_dia * scale
                    sh = abs(ty(y1) - ty(y0)) + self.tool_dia * scale
                    painter.drawRect(QtCore.QRectF(sx0, sy0, sw, sh))

                # Draw cut line
                pen_cut = QtGui.QPen(QtGui.QColor(0, 255, 0), 2)
                painter.setPen(pen_cut)
                painter.setBrush(QtCore.Qt.NoBrush)
                painter.drawLine(QtCore.QPointF(tx(x0), ty(y0)),
                                 QtCore.QPointF(tx(x1), ty(y1)))
            else:
                painter.setPen(pen_rapid)
                painter.setBrush(QtCore.Qt.NoBrush)
                painter.drawLine(QtCore.QPointF(tx(x0), ty(y0)),
                                 QtCore.QPointF(tx(x1), ty(y1)))

        # Draw origin marker
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 50, 50), 2))
        ox, oy = tx(0), ty(0)
        painter.drawLine(QtCore.QPointF(ox - 8, oy), QtCore.QPointF(ox + 8, oy))
        painter.drawLine(QtCore.QPointF(ox, oy - 8), QtCore.QPointF(ox, oy + 8))

        painter.end()


class Surfacing(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._connect_signals()
        # Generate initial preview
        self._update_preview()

    def _build_ui(self):
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(12)

        # Left side: parameters
        params_group = QtWidgets.QGroupBox("Surfacing Parameters")
        params_layout = QtWidgets.QFormLayout(params_group)
        params_layout.setSpacing(10)
        params_layout.setContentsMargins(12, 20, 12, 12)

        float_val = QtGui.QDoubleValidator(0.001, 99999.0, 3)
        int_val = QtGui.QIntValidator(1, 99999)

        def make_input(default, validator=float_val, suffix="mm"):
            le = QtWidgets.QLineEdit(str(default))
            le.setValidator(validator)
            le.setPlaceholderText(suffix)
            le.setMinimumHeight(30)
            return le

        self.input_x = make_input(100)
        params_layout.addRow("X Length (mm):", self.input_x)

        self.input_y = make_input(100)
        params_layout.addRow("Y Width (mm):", self.input_y)

        self.input_tool_dia = make_input(8)
        params_layout.addRow("Tool Diameter (mm):", self.input_tool_dia)

        self.input_stepover = make_input(5)
        params_layout.addRow("Max Stepover (mm):", self.input_stepover)

        self.input_depth = make_input(0.5)
        params_layout.addRow("Cut Depth (mm):", self.input_depth)

        self.input_safe_z = make_input(10)
        params_layout.addRow("Safe Z Height (mm):", self.input_safe_z)

        self.input_rpm = make_input(22000, int_val, "RPM")
        params_layout.addRow("Spindle Speed (RPM):", self.input_rpm)

        self.input_feed = make_input(6000, int_val, "mm/min")
        params_layout.addRow("Feed Rate (mm/min):", self.input_feed)

        self.combo_direction = QtWidgets.QComboBox()
        self.combo_direction.setMinimumHeight(30)
        self.combo_direction.addItems(["Along X (conventional)", "Along Y"])
        params_layout.addRow("Direction:", self.combo_direction)

        main_layout.addWidget(params_group, 1)

        # Right side: visual preview and buttons
        right_layout = QtWidgets.QVBoxLayout()
        right_layout.setSpacing(8)

        # Visual toolpath preview
        preview_group = QtWidgets.QGroupBox("Toolpath Preview")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(4, 16, 4, 4)
        self.toolpath_view = ToolpathView()
        preview_layout.addWidget(self.toolpath_view)
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
        # Live preview updates when any parameter changes
        self.input_x.textChanged.connect(self._update_preview)
        self.input_y.textChanged.connect(self._update_preview)
        self.input_tool_dia.textChanged.connect(self._update_preview)
        self.input_stepover.textChanged.connect(self._update_preview)
        self.combo_direction.currentIndexChanged.connect(self._update_preview)

    def _get_float(self, widget, fallback=1.0):
        try:
            v = float(widget.text())
            return v if v > 0 else fallback
        except (ValueError, ZeroDivisionError):
            return fallback

    def _compute_passes(self):
        x_len = self._get_float(self.input_x)
        y_width = self._get_float(self.input_y)
        tool_dia = self._get_float(self.input_tool_dia)
        max_stepover = self._get_float(self.input_stepover)
        along_x = self.combo_direction.currentIndex() == 0

        if along_x:
            padded_y = y_width + tool_dia * 2
            num_cuts = int(-(-padded_y // max_stepover))
            stepover = padded_y / num_cuts
        else:
            padded_x = x_len + tool_dia * 2
            num_cuts = int(-(-padded_x // max_stepover))
            stepover = padded_x / num_cuts

        return num_cuts, stepover, along_x

    def _build_toolpath_segments(self):
        """Build list of (x0, y0, x1, y1, is_cut) for visualization."""
        x_len = self._get_float(self.input_x)
        y_width = self._get_float(self.input_y)
        tool_dia = self._get_float(self.input_tool_dia)
        num_cuts, stepover, along_x = self._compute_passes()

        segments = []

        if along_x:
            # All cuts from X_max to 0 (climb only), rapid back
            for i in range(num_cuts):
                y_pos = i * stepover
                # Rapid to start of cut
                segments.append((0, y_pos, x_len, y_pos, False))
                # Cut from X_max to 0
                segments.append((x_len, y_pos, 0, y_pos, True))
        else:
            # All cuts from Y_max to 0 (climb only), rapid back
            for i in range(num_cuts):
                x_pos = i * stepover
                # Rapid to start of cut
                segments.append((x_pos, 0, x_pos, y_width, False))
                # Cut from Y_max to 0
                segments.append((x_pos, y_width, x_pos, 0, True))

        return segments

    def _update_preview(self):
        x_len = self._get_float(self.input_x)
        y_width = self._get_float(self.input_y)
        tool_dia = self._get_float(self.input_tool_dia)
        num_cuts, stepover, along_x = self._compute_passes()
        segments = self._build_toolpath_segments()
        self.toolpath_view.set_toolpath(segments, x_len, y_width, tool_dia)

        padded = y_width + tool_dia * 2 if along_x else x_len + tool_dia * 2
        self.lbl_info.setText(
            "Passes: {}  |  Actual stepover: {:.2f} mm  |  Padded {}: {:.1f} mm".format(
                num_cuts, stepover, "Y" if along_x else "X", padded))

    def _generate_gcode(self):
        x_len = self._get_float(self.input_x)
        y_width = self._get_float(self.input_y)
        tool_dia = self._get_float(self.input_tool_dia)
        max_stepover = self._get_float(self.input_stepover)
        depth = self._get_float(self.input_depth, 0.5)
        safe_z = self._get_float(self.input_safe_z, 10)
        rpm = int(self._get_float(self.input_rpm, 22000))
        feed = int(self._get_float(self.input_feed, 6000))
        num_cuts, stepover, along_x = self._compute_passes()

        lines = []
        lines.append("%")
        lines.append("(Surfacing operation)")
        lines.append("(X={:.1f} Y={:.1f} Tool Dia={:.1f} Stepover={:.2f})".format(
            x_len, y_width, tool_dia, stepover))
        lines.append("(Depth={:.2f} RPM={} Feed={})".format(depth, rpm, feed))
        lines.append("")
        lines.append("G21 (metric)")
        lines.append("G90 (absolute positioning)")
        lines.append("G40 (cancel cutter comp)")
        lines.append("G49 (cancel tool length offset)")
        lines.append("G64 P0.03 (path blending)")
        lines.append("G17 (XY plane)")
        lines.append("")
        lines.append("G53 G0 Z-5 (retract to safe machine Z)")
        lines.append("")

        if along_x:
            lines.append("G0 X{:.1f} Y0 (rapid to start position)".format(x_len))
            lines.append("S{} M3 (start spindle)".format(rpm))
            lines.append("G4 P2 (wait for spindle)")
            lines.append("")
            for i in range(num_cuts):
                y_pos = i * stepover
                lines.append("G0 X{:.1f} Y{:.2f}".format(x_len, y_pos))
                lines.append("G1 Z-{:.2f} F{}".format(depth, feed))
                lines.append("G1 X0 F{}".format(feed))
                lines.append("G0 Z{:.1f}".format(safe_z))
        else:
            lines.append("G0 X0 Y{:.1f} (rapid to start position)".format(y_width))
            lines.append("S{} M3 (start spindle)".format(rpm))
            lines.append("G4 P2 (wait for spindle)")
            lines.append("")
            for i in range(num_cuts):
                x_pos = i * stepover
                lines.append("G0 X{:.2f} Y{:.1f}".format(x_pos, y_width))
                lines.append("G1 Z-{:.2f} F{}".format(depth, feed))
                lines.append("G1 Y0 F{}".format(feed))
                lines.append("G0 Z{:.1f}".format(safe_z))

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
            self, "Save Surfacing G-code", os.path.expanduser("~/GCODE/surfacing.ngc"),
            "G-code Files (*.ngc *.nc *.gcode);;All Files (*)")
        if fname:
            with open(fname, 'w') as f:
                f.write(gcode + "\n")
            self.lbl_info.setText("Saved to: " + fname)

    def _send_to_linuxcnc(self):
        gcode = self._generate_gcode()
        tmp = os.path.join(tempfile.gettempdir(), "surfacing_op.ngc")
        with open(tmp, 'w') as f:
            f.write(gcode + "\n")
        ACTION.OPEN_PROGRAM(tmp)
        self.lbl_info.setText(self.lbl_info.text() + "  |  Loaded into LinuxCNC")
