import os
import json
import tempfile
import math
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
        self.stepover = 0
        self.num_cuts = 0
        self.along_x = True

    def set_toolpath(self, toolpath, work_x, work_y, tool_dia,
                     stepover=0, num_cuts=0, along_x=True):
        self.toolpath = toolpath
        self.work_x = work_x
        self.work_y = work_y
        self.tool_dia = tool_dia
        self.stepover = stepover
        self.num_cuts = num_cuts
        self.along_x = along_x
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

        # Reserve space for dimension lines
        dim_space_l = 60   # left
        dim_space_b = 50   # bottom
        dim_space_t = 30   # top
        dim_space_r = 40   # right

        draw_w = w - dim_space_l - dim_space_r
        draw_h = h - dim_space_t - dim_space_b

        # Scale to fit workpiece, maintaining aspect ratio
        scale_x = draw_w / self.work_x
        scale_y = draw_h / self.work_y
        scale = min(scale_x, scale_y) * 0.9

        actual_w = self.work_x * scale
        actual_h = self.work_y * scale
        offset_x = dim_space_l + (draw_w - actual_w) / 2
        offset_y = dim_space_t + (draw_h - actual_h) / 2

        def tx(x):
            return offset_x + x * scale

        def ty(y):
            return offset_y + actual_h - y * scale

        # --- Dimension line helpers ---
        def draw_dim_h(y_pos, x_start, x_end, label, color, tick_len=5):
            painter.setPen(QtGui.QPen(color, 1))
            painter.drawLine(QtCore.QPointF(x_start, y_pos),
                             QtCore.QPointF(x_end, y_pos))
            painter.drawLine(QtCore.QPointF(x_start, y_pos - tick_len),
                             QtCore.QPointF(x_start, y_pos + tick_len))
            painter.drawLine(QtCore.QPointF(x_end, y_pos - tick_len),
                             QtCore.QPointF(x_end, y_pos + tick_len))
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(label)
            text_x = (x_start + x_end) / 2 - tw / 2
            painter.drawText(QtCore.QPointF(text_x, y_pos - 4), label)

        def draw_dim_v(x_pos, y_start, y_end, label, color, tick_len=5):
            painter.setPen(QtGui.QPen(color, 1))
            painter.drawLine(QtCore.QPointF(x_pos, y_start),
                             QtCore.QPointF(x_pos, y_end))
            painter.drawLine(QtCore.QPointF(x_pos - tick_len, y_start),
                             QtCore.QPointF(x_pos + tick_len, y_start))
            painter.drawLine(QtCore.QPointF(x_pos - tick_len, y_end),
                             QtCore.QPointF(x_pos + tick_len, y_end))
            painter.save()
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(label)
            text_y = (y_start + y_end) / 2 + tw / 2
            painter.translate(x_pos - 5, text_y)
            painter.rotate(-90)
            painter.drawText(0, 0, label)
            painter.restore()

        # --- Draw workpiece outline ---
        painter.setPen(QtGui.QPen(QtGui.QColor(140, 140, 160), 2))
        painter.setBrush(QtGui.QColor(80, 70, 50, 180))
        painter.drawRect(QtCore.QRectF(tx(0), ty(self.work_y), actual_w, actual_h))

        # --- Draw toolpath segments ---
        tool_screen_w = self.tool_dia * scale
        pen_rapid = QtGui.QPen(QtGui.QColor(100, 100, 100, 120), 1, QtCore.Qt.DashLine)

        for (x0, y0, x1, y1, is_cut) in self.toolpath:
            if is_cut:
                if tool_screen_w > 2:
                    swath_color = QtGui.QColor(0, 180, 0, 40)
                    painter.setPen(QtCore.Qt.NoPen)
                    painter.setBrush(swath_color)
                    half_tool = self.tool_dia / 2
                    sx0 = min(tx(x0), tx(x1)) - half_tool * scale
                    sy0 = min(ty(y0), ty(y1)) - half_tool * scale
                    sw = abs(tx(x1) - tx(x0)) + self.tool_dia * scale
                    sh = abs(ty(y1) - ty(y0)) + self.tool_dia * scale
                    painter.drawRect(QtCore.QRectF(sx0, sy0, sw, sh))

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

        # --- Origin marker ---
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 50, 50), 2))
        ox, oy = tx(0), ty(0)
        painter.drawLine(QtCore.QPointF(ox - 8, oy), QtCore.QPointF(ox + 8, oy))
        painter.drawLine(QtCore.QPointF(ox, oy - 8), QtCore.QPointF(ox, oy + 8))

        # --- Extension lines ---
        ext_pen = QtGui.QPen(QtGui.QColor(80, 80, 80), 1, QtCore.Qt.DotLine)
        painter.setPen(ext_pen)

        board_bottom = ty(0)
        dim_y = board_bottom + 20

        painter.drawLine(QtCore.QPointF(tx(0), board_bottom + 2),
                         QtCore.QPointF(tx(0), dim_y + 6))
        painter.drawLine(QtCore.QPointF(tx(self.work_x), board_bottom + 2),
                         QtCore.QPointF(tx(self.work_x), dim_y + 6))

        board_left = tx(0)
        dim_x = board_left - 20

        painter.drawLine(QtCore.QPointF(board_left - 2, ty(0)),
                         QtCore.QPointF(dim_x - 6, ty(0)))
        painter.drawLine(QtCore.QPointF(board_left - 2, ty(self.work_y)),
                         QtCore.QPointF(dim_x - 6, ty(self.work_y)))

        # --- Dimension lines ---
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        dim_color = QtGui.QColor(180, 180, 180)

        draw_dim_h(dim_y, tx(0), tx(self.work_x),
                   "{:.1f} mm".format(self.work_x), dim_color)
        draw_dim_v(dim_x, ty(self.work_y), ty(0),
                   "{:.1f} mm".format(self.work_y), dim_color)

        # --- Legend (top-right) ---
        font.setPointSize(8)
        painter.setFont(font)
        legend_x = w - dim_space_r - 5
        legend_y = dim_space_t

        painter.setPen(QtGui.QColor(0, 220, 0))
        painter.drawText(QtCore.QRectF(0, legend_y, legend_x, 15),
                         QtCore.Qt.AlignRight,
                         "Tool: {:.1f}mm dia".format(self.tool_dia))
        painter.setPen(QtGui.QColor(160, 160, 160))
        painter.drawText(QtCore.QRectF(0, legend_y + 14, legend_x, 15),
                         QtCore.Qt.AlignRight,
                         "{} passes, {:.1f}mm stepover".format(
                             self.num_cuts, self.stepover))
        cut_dir = "along X" if self.along_x else "along Y"
        painter.drawText(QtCore.QRectF(0, legend_y + 28, legend_x, 15),
                         QtCore.Qt.AlignRight,
                         "Climb cutting {}".format(cut_dir))

        painter.end()


SURFACING_CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'surfacing.conf')


class Surfacing(QtWidgets.QWidget):
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

        self.input_tool_dia = make_input(6)
        params_layout.addRow("Tool Diameter (mm):", self.input_tool_dia)

        self.input_stepover_pct = make_input(70)
        params_layout.addRow("Stepover (% of tool):", self.input_stepover_pct)

        self.input_safe_z = make_input(10)
        params_layout.addRow("Safe Z (mm):", self.input_safe_z)

        self.input_rpm = make_input(22000, int_val, "RPM")
        params_layout.addRow("Spindle Speed (RPM):", self.input_rpm)

        self.input_feed = make_input(6000, int_val, "mm/min")
        params_layout.addRow("Feed Rate (mm/min):", self.input_feed)

        self.combo_direction = QtWidgets.QComboBox()
        self.combo_direction.setMinimumHeight(30)
        self.combo_direction.addItems(["Along X", "Along Y"])
        params_layout.addRow("Direction:", self.combo_direction)

        self.combo_method = QtWidgets.QComboBox()
        self.combo_method.setMinimumHeight(30)
        self.combo_method.addItems(["Unidirectional", "Both edges inward"])
        params_layout.addRow("Method:", self.combo_method)

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
        for w in [self.input_x, self.input_y, self.input_tool_dia,
                  self.input_stepover_pct, self.input_safe_z,
                  self.input_rpm, self.input_feed]:
            w.textChanged.connect(self._update_preview)
            w.textChanged.connect(self._save_params)
        self.combo_direction.currentIndexChanged.connect(self._update_preview)
        self.combo_direction.currentIndexChanged.connect(self._save_params)
        self.combo_method.currentIndexChanged.connect(self._update_preview)
        self.combo_method.currentIndexChanged.connect(self._save_params)

    def _param_widgets(self):
        return {
            'x': self.input_x,
            'y': self.input_y,
            'tool_dia': self.input_tool_dia,
            'stepover_pct': self.input_stepover_pct,
            'safe_z': self.input_safe_z,
            'rpm': self.input_rpm,
            'feed': self.input_feed,
        }

    def _save_params(self):
        data = {}
        for key, w in self._param_widgets().items():
            data[key] = w.text()
        data['direction'] = self.combo_direction.currentIndex()
        data['method'] = self.combo_method.currentIndex()
        try:
            with open(SURFACING_CONF, 'w') as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def _load_params(self):
        try:
            with open(SURFACING_CONF, 'r') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        for key, w in self._param_widgets().items():
            if key in data:
                w.setText(str(data[key]))
        if 'direction' in data:
            self.combo_direction.setCurrentIndex(data['direction'])
        if 'method' in data:
            self.combo_method.setCurrentIndex(data['method'])

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
        stepover_pct = self._get_float(self.input_stepover_pct, 70)
        stepover = tool_dia * stepover_pct / 100.0
        along_x = self.combo_direction.currentIndex() == 0
        both_edges = self.combo_method.currentIndex() == 1

        if along_x:
            num_cuts = math.ceil(y_width / stepover)
            actual_stepover = y_width / num_cuts
        else:
            num_cuts = math.ceil(x_len / stepover)
            actual_stepover = x_len / num_cuts

        return num_cuts, actual_stepover, along_x, both_edges

    def _build_toolpath_segments(self):
        """Build list of (x0, y0, x1, y1, is_cut) for visualization."""
        x_len = self._get_float(self.input_x)
        y_width = self._get_float(self.input_y)
        tool_dia = self._get_float(self.input_tool_dia)
        num_cuts, stepover, along_x, both_edges = self._compute_passes()

        segments = []

        if both_edges:
            span = y_width if along_x else x_len
            near_idx = 0
            far_idx = 0
            from_near = True
            for i in range(num_cuts):
                if from_near:
                    pos = near_idx * stepover
                    if along_x:
                        segments.append((0, pos, x_len, pos, False))
                        segments.append((x_len, pos, 0, pos, True))
                    else:
                        segments.append((pos, 0, pos, y_width, False))
                        segments.append((pos, y_width, pos, 0, True))
                    near_idx += 1
                else:
                    pos = span - far_idx * stepover
                    if along_x:
                        segments.append((x_len, pos, 0, pos, False))
                        segments.append((0, pos, x_len, pos, True))
                    else:
                        segments.append((pos, y_width, pos, 0, False))
                        segments.append((pos, 0, pos, y_width, True))
                    far_idx += 1
                from_near = not from_near
        else:
            if along_x:
                for i in range(num_cuts):
                    y_pos = i * stepover
                    segments.append((0, y_pos, x_len, y_pos, False))
                    segments.append((x_len, y_pos, 0, y_pos, True))
            else:
                for i in range(num_cuts):
                    x_pos = i * stepover
                    segments.append((x_pos, 0, x_pos, y_width, False))
                    segments.append((x_pos, y_width, x_pos, 0, True))

        return segments

    def _update_preview(self):
        x_len = self._get_float(self.input_x)
        y_width = self._get_float(self.input_y)
        tool_dia = self._get_float(self.input_tool_dia)
        num_cuts, stepover, along_x, both_edges = self._compute_passes()
        segments = self._build_toolpath_segments()
        self.toolpath_view.set_toolpath(segments, x_len, y_width, tool_dia,
                                        stepover, num_cuts, along_x)

        method = "both edges inward" if both_edges else "unidirectional"
        self.lbl_info.setText(
            "Passes: {}  |  Stepover: {:.1f}mm ({:.0f}% of {:.0f}mm)  |  {}".format(
                num_cuts, stepover, self._get_float(self.input_stepover_pct, 70),
                tool_dia, method))

    def _generate_gcode(self):
        x_len = self._get_float(self.input_x)
        y_width = self._get_float(self.input_y)
        tool_dia = self._get_float(self.input_tool_dia)
        stepover_pct = self._get_float(self.input_stepover_pct, 70)
        safe_z = self._get_float(self.input_safe_z, 10)
        rpm = int(self._get_float(self.input_rpm, 22000))
        feed = int(self._get_float(self.input_feed, 6000))
        num_cuts, stepover, along_x, both_edges = self._compute_passes()
        method_str = "both edges inward" if both_edges else "unidirectional"

        lines = []
        lines.append("%")
        lines.append("(Surfacing operation - {})".format(method_str))
        lines.append("(X={:.1f} Y={:.1f} Tool Dia={:.1f} Stepover={:.1f}mm at {:.0f}%)".format(
            x_len, y_width, tool_dia, stepover, stepover_pct))
        lines.append("(Cut at Z=0 RPM={} Feed={})".format(rpm, feed))
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

        def _gcode_pass(lines, along_x, x_len, y_width, pos, feed, safe_z, reverse):
            """Generate G-code for a single surfacing pass.
            reverse=False: climb from near edge, reverse=True: climb from far edge."""
            if along_x:
                if reverse:
                    lines.append("G0 X0 Y{:.2f}".format(pos))
                    lines.append("G1 Z0 F{}".format(feed))
                    lines.append("G1 X{:.1f} F{}".format(x_len, feed))
                else:
                    lines.append("G0 X{:.1f} Y{:.2f}".format(x_len, pos))
                    lines.append("G1 Z0 F{}".format(feed))
                    lines.append("G1 X0 F{}".format(feed))
            else:
                if reverse:
                    lines.append("G0 X{:.2f} Y0".format(pos))
                    lines.append("G1 Z0 F{}".format(feed))
                    lines.append("G1 Y{:.1f} F{}".format(y_width, feed))
                else:
                    lines.append("G0 X{:.2f} Y{:.1f}".format(pos, y_width))
                    lines.append("G1 Z0 F{}".format(feed))
                    lines.append("G1 Y0 F{}".format(feed))
            lines.append("G0 Z{:.1f}".format(safe_z))

        if along_x:
            lines.append("G0 X{:.1f} Y0 (rapid to start position)".format(x_len))
        else:
            lines.append("G0 X0 Y{:.1f} (rapid to start position)".format(y_width))
        lines.append("S{} M3 (start spindle)".format(rpm))
        lines.append("G4 P2 (wait for spindle)")
        lines.append("")

        if both_edges:
            # Alternate: pass 1 from near edge, pass 2 from far edge, etc.
            # Near edge works inward: Y=0, Y=stepover, Y=2*stepover...
            # Far edge works inward: Y=max, Y=max-stepover, Y=max-2*stepover...
            span = y_width if along_x else x_len
            near_idx = 0
            far_idx = 0
            from_near = True
            for i in range(num_cuts):
                if from_near:
                    pos = near_idx * stepover
                    _gcode_pass(lines, along_x, x_len, y_width, pos, feed, safe_z, False)
                    near_idx += 1
                else:
                    pos = span - far_idx * stepover
                    _gcode_pass(lines, along_x, x_len, y_width, pos, feed, safe_z, True)
                    far_idx += 1
                from_near = not from_near
        else:
            for i in range(num_cuts):
                pos = i * stepover
                _gcode_pass(lines, along_x, x_len, y_width, pos, feed, safe_z, False)

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
