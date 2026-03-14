import os
import json
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
        self.tool_dia = 0
        self.ops = []  # list of operation names that are enabled

    def set_params(self, board_x, board_y, board_z, ops, depth_per_pass=1, tool_dia=6):
        self.board_x = board_x
        self.board_y = board_y
        self.board_z = board_z
        self.ops = ops
        self.depth_per_pass = depth_per_pass
        self.tool_dia = tool_dia
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
        # Reserve space for dimension lines outside the drawing
        dim_space = 70   # space on left/bottom for dimension lines
        dim_space_t = 35  # space on top
        dim_space_r = 45  # space on right

        draw_area_w = w - dim_space - dim_space_r
        draw_area_h = top_h - dim_space_t - dim_space

        tool_r = self.tool_dia / 2
        has_sides = any(op in self.ops for op in ["+x", "-x", "+y", "-y"])
        total_x = self.board_x + (self.tool_dia if has_sides else 0)
        total_y = self.board_y + (self.tool_dia if has_sides else 0)

        scale_x = draw_area_w / total_x
        scale_y = draw_area_h / total_y
        scale = min(scale_x, scale_y) * 0.88

        actual_w = self.board_x * scale
        actual_h = self.board_y * scale
        total_w = total_x * scale
        total_h = total_y * scale

        # Center the total area in the drawing zone
        cx = dim_space + (draw_area_w - total_w) / 2 + (tool_r * scale if has_sides else 0)
        cy = dim_space_t + (draw_area_h - total_h) / 2 + (tool_r * scale if has_sides else 0)

        def tx(x):
            return cx + x * scale

        def ty(y):
            return cy + actual_h - y * scale

        # Helper to draw a dimension line with ticks and centered text
        def draw_dim_h(y_pos, x_start, x_end, label, color, tick_len=5):
            """Horizontal dimension line at y_pos from x_start to x_end."""
            painter.setPen(QtGui.QPen(color, 1))
            painter.drawLine(QtCore.QPointF(x_start, y_pos),
                             QtCore.QPointF(x_end, y_pos))
            # Ticks
            painter.drawLine(QtCore.QPointF(x_start, y_pos - tick_len),
                             QtCore.QPointF(x_start, y_pos + tick_len))
            painter.drawLine(QtCore.QPointF(x_end, y_pos - tick_len),
                             QtCore.QPointF(x_end, y_pos + tick_len))
            # Text centered
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(label)
            text_x = (x_start + x_end) / 2 - tw / 2
            painter.drawText(QtCore.QPointF(text_x, y_pos - 4), label)

        def draw_dim_v(x_pos, y_start, y_end, label, color, tick_len=5):
            """Vertical dimension line at x_pos from y_start to y_end."""
            painter.setPen(QtGui.QPen(color, 1))
            painter.drawLine(QtCore.QPointF(x_pos, y_start),
                             QtCore.QPointF(x_pos, y_end))
            # Ticks
            painter.drawLine(QtCore.QPointF(x_pos - tick_len, y_start),
                             QtCore.QPointF(x_pos + tick_len, y_start))
            painter.drawLine(QtCore.QPointF(x_pos - tick_len, y_end),
                             QtCore.QPointF(x_pos + tick_len, y_end))
            # Text centered, rotated
            painter.save()
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(label)
            text_y = (y_start + y_end) / 2 + tw / 2
            painter.translate(x_pos - 5, text_y)
            painter.rotate(-90)
            painter.drawText(0, 0, label)
            painter.restore()

        # --- Draw shapes ---

        # Tool swath fill (outermost)
        if tool_r > 0 and has_sides:
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(255, 200, 50, 20))
            painter.drawRect(QtCore.QRectF(
                tx(-tool_r), ty(self.board_y + tool_r),
                total_w, total_h))

        # Tool center path - dashed yellow
        if tool_r > 0 and has_sides:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 200, 50, 150), 1.5, QtCore.Qt.DashLine))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(QtCore.QRectF(
                tx(-tool_r), ty(self.board_y + tool_r),
                (self.board_x + self.tool_dia) * scale,
                (self.board_y + self.tool_dia) * scale))

        # Board fill and outline
        painter.setPen(QtGui.QPen(QtGui.QColor(140, 140, 160), 2))
        painter.setBrush(QtGui.QColor(80, 70, 50, 180))
        painter.drawRect(QtCore.QRectF(tx(0), ty(self.board_y), actual_w, actual_h))

        # --- Surfacing indicator (subtle lines inside board) ---
        if "top" in self.ops:
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 200, 0, 100), 1))
            for i in range(5):
                frac = (i + 1) / 6
                yl = ty(self.board_y * frac)
                painter.drawLine(QtCore.QPointF(tx(0) + 3, yl),
                                 QtCore.QPointF(tx(self.board_x) - 3, yl))

        # --- Operation labels inside the board ---
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)

        op_num = 1
        # Center label for surfacing
        if "top" in self.ops:
            painter.setPen(QtGui.QColor(0, 220, 0))
            painter.drawText(QtCore.QRectF(tx(0), ty(self.board_y), actual_w, actual_h),
                             QtCore.Qt.AlignCenter, "{}: Surface Top".format(op_num))
            op_num += 1

        # Side operation labels along the edges (inside the board near each edge)
        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)

        if "+x" in self.ops:
            painter.setPen(QtGui.QColor(255, 100, 100))
            painter.save()
            painter.translate(tx(self.board_x) - 14, ty(self.board_y / 2) + 30)
            painter.rotate(-90)
            painter.drawText(0, 0, "{}: +X end".format(op_num))
            painter.restore()
            op_num += 1

        if "-x" in self.ops:
            painter.setPen(QtGui.QColor(255, 150, 50))
            painter.save()
            painter.translate(tx(0) + 12, ty(self.board_y / 2) + 25)
            painter.rotate(-90)
            painter.drawText(0, 0, "{}: -X end".format(op_num))
            painter.restore()
            op_num += 1

        if "+y" in self.ops:
            painter.setPen(QtGui.QColor(100, 150, 255))
            painter.drawText(QtCore.QPointF(tx(self.board_x / 2) - 20, ty(self.board_y) + 14),
                             "{}: +Y side".format(op_num))
            op_num += 1

        if "-y" in self.ops:
            painter.setPen(QtGui.QColor(200, 100, 255))
            painter.drawText(QtCore.QPointF(tx(self.board_x / 2) - 20, ty(0) - 5),
                             "{}: -Y side".format(op_num))
            op_num += 1

        # --- Side cut lines on the tool path ---
        if "+x" in self.ops:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 100, 100), 2))
            painter.drawLine(QtCore.QPointF(tx(self.board_x + tool_r), ty(self.board_y + tool_r)),
                             QtCore.QPointF(tx(self.board_x + tool_r), ty(-tool_r)))
        if "-x" in self.ops:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 150, 50), 2))
            painter.drawLine(QtCore.QPointF(tx(-tool_r), ty(self.board_y + tool_r)),
                             QtCore.QPointF(tx(-tool_r), ty(-tool_r)))
        if "+y" in self.ops:
            painter.setPen(QtGui.QPen(QtGui.QColor(100, 150, 255), 2))
            painter.drawLine(QtCore.QPointF(tx(-tool_r), ty(self.board_y + tool_r)),
                             QtCore.QPointF(tx(self.board_x + tool_r), ty(self.board_y + tool_r)))
        if "-y" in self.ops:
            painter.setPen(QtGui.QPen(QtGui.QColor(200, 100, 255), 2))
            painter.drawLine(QtCore.QPointF(tx(-tool_r), ty(-tool_r)),
                             QtCore.QPointF(tx(self.board_x + tool_r), ty(-tool_r)))

        # --- Extension lines (thin lines from shape to dimension lines) ---
        ext_color = QtGui.QColor(80, 80, 80)
        ext_pen = QtGui.QPen(ext_color, 1, QtCore.Qt.DotLine)

        # Bottom extension lines (from board corners down)
        board_bottom = ty(0)
        dim_y_inner = board_bottom + 18  # inner dimension line Y
        dim_y_outer = board_bottom + 36  # outer dimension line Y

        painter.setPen(ext_pen)
        painter.drawLine(QtCore.QPointF(tx(0), board_bottom + 2),
                         QtCore.QPointF(tx(0), dim_y_outer + 6))
        painter.drawLine(QtCore.QPointF(tx(self.board_x), board_bottom + 2),
                         QtCore.QPointF(tx(self.board_x), dim_y_outer + 6))
        if has_sides:
            painter.drawLine(QtCore.QPointF(tx(-tool_r), ty(-tool_r) + 2),
                             QtCore.QPointF(tx(-tool_r), dim_y_outer + 6))
            painter.drawLine(QtCore.QPointF(tx(self.board_x + tool_r), ty(-tool_r) + 2),
                             QtCore.QPointF(tx(self.board_x + tool_r), dim_y_outer + 6))

        # Left extension lines (from board corners left)
        board_left = tx(0)
        dim_x_inner = board_left - 18
        dim_x_outer = board_left - 36

        painter.drawLine(QtCore.QPointF(board_left - 2, ty(0)),
                         QtCore.QPointF(dim_x_outer - 6, ty(0)))
        painter.drawLine(QtCore.QPointF(board_left - 2, ty(self.board_y)),
                         QtCore.QPointF(dim_x_outer - 6, ty(self.board_y)))
        if has_sides:
            painter.drawLine(QtCore.QPointF(tx(-tool_r) - 2, ty(-tool_r)),
                             QtCore.QPointF(dim_x_outer - 6, ty(-tool_r)))
            painter.drawLine(QtCore.QPointF(tx(-tool_r) - 2, ty(self.board_y + tool_r)),
                             QtCore.QPointF(dim_x_outer - 6, ty(self.board_y + tool_r)))

        # --- Dimension lines ---
        font.setPointSize(9)
        font.setBold(False)
        painter.setFont(font)

        # Bottom: inner = board X, outer = total X
        dim_color = QtGui.QColor(180, 180, 180)
        draw_dim_h(dim_y_inner, tx(0), tx(self.board_x),
                   "{:.1f}".format(self.board_x), dim_color)
        if has_sides:
            tp_color = QtGui.QColor(255, 200, 50, 200)
            draw_dim_h(dim_y_outer, tx(-tool_r), tx(self.board_x + tool_r),
                       "{:.1f} (cut path)".format(total_x), tp_color)

        # Left: inner = board Y, outer = total Y
        draw_dim_v(dim_x_inner, ty(self.board_y), ty(0),
                   "{:.1f}".format(self.board_y), dim_color)
        if has_sides:
            draw_dim_v(dim_x_outer, ty(self.board_y + tool_r), ty(-tool_r),
                       "{:.1f} (cut path)".format(total_y), tp_color)

        # --- Title and legend ---
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(180, 180, 180))
        painter.drawText(QtCore.QPointF(10, 16), "Top View")

        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)

        # Legend (top right)
        legend_x = w - 185
        legend_y = 10
        # Board
        painter.setPen(QtGui.QPen(QtGui.QColor(140, 140, 160), 2))
        painter.drawLine(QtCore.QPointF(legend_x, legend_y + 4),
                         QtCore.QPointF(legend_x + 16, legend_y + 4))
        painter.setPen(QtGui.QColor(180, 180, 180))
        painter.drawText(QtCore.QPointF(legend_x + 20, legend_y + 8),
                         "Board ({:.1f} x {:.1f})".format(self.board_x, self.board_y))

        if has_sides:
            legend_y += 14
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 200, 50, 150), 1.5, QtCore.Qt.DashLine))
            painter.drawLine(QtCore.QPointF(legend_x, legend_y + 4),
                             QtCore.QPointF(legend_x + 16, legend_y + 4))
            painter.setPen(QtGui.QColor(255, 200, 50, 200))
            painter.drawText(QtCore.QPointF(legend_x + 20, legend_y + 8),
                             "Tool path ({:.1f}mm dia, +/-{:.1f} offset)".format(
                                 self.tool_dia, tool_r))

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
        painter.drawText(QtCore.QPointF(side_margin_l, top_h + 16), "Side View")
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

        # Z height label (left side)
        painter.setPen(QtGui.QColor(180, 180, 180))
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(QtCore.QPointF(s_ox - 55, stz(self.board_z / 2) + 4),
                         "Z: {:.1f}".format(self.board_z))

        # X length label (bottom)
        painter.drawText(QtCore.QPointF(stx(self.board_x / 2) - 25, stz(0) + 28),
                         "X: {:.1f} mm".format(self.board_x))

        # Z=0 and Z=top labels on left
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(120, 120, 120))
        painter.drawText(QtCore.QPointF(s_ox - 30, stz(0) + 4), "Z=0")
        painter.drawText(QtCore.QPointF(s_ox - 55, stz(self.board_z) + 4),
                         "Z={:.1f}".format(self.board_z))

        # Surface depth indicator
        if "top" in self.ops:
            surf_z = self.board_z - self.depth_per_pass  # approximate with depth_per_pass
            # Try to get actual surface_depth if available
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 200, 0, 150), 1, QtCore.Qt.DashLine))
            # Just show the top surface cut line
            surf_line_z = stz(self.board_z) + 3
            painter.drawLine(QtCore.QPointF(stx(0), surf_line_z),
                             QtCore.QPointF(stx(self.board_x), surf_line_z))
            painter.setPen(QtGui.QColor(0, 200, 0, 180))
            painter.drawText(QtCore.QPointF(stx(self.board_x) + 5, surf_line_z + 4),
                             "surface")

        # Depth per pass and pass count labels (right side)
        if has_sides and self.depth_per_pass > 0:
            num_passes = math.ceil(self.board_z / self.depth_per_pass)
            painter.setPen(QtGui.QColor(150, 200, 150))
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(QtCore.QPointF(stx(self.board_x) + 5, stz(self.board_z / 2) + 4),
                             "{} passes".format(num_passes))
            painter.drawText(QtCore.QPointF(stx(self.board_x) + 5, stz(self.board_z / 2) + 16),
                             "{:.1f}mm/pass".format(self.depth_per_pass))

        font.setPointSize(9)
        painter.setFont(font)

        # Origin marker
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 50, 50), 2))
        painter.drawLine(QtCore.QPointF(stx(0) - 6, stz(0)),
                         QtCore.QPointF(stx(0) + 6, stz(0)))
        painter.drawLine(QtCore.QPointF(stx(0), stz(0) - 6),
                         QtCore.QPointF(stx(0), stz(0) + 6))

        painter.end()


BOARD_SQUARING_CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'board_squaring.conf')


class BoardSquaring(QtWidgets.QWidget):
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

        self.input_tool_dia = make_input(6)
        tool_layout.addRow("Tool Diameter (mm):", self.input_tool_dia)

        self.input_stepover_pct = make_input(70)
        tool_layout.addRow("Stepover (% of tool):", self.input_stepover_pct)

        self.input_depth_per_pass = make_input(2)
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
                  self.input_tool_dia, self.input_stepover_pct,
                  self.input_depth_per_pass, self.input_surface_depth,
                  self.input_rpm, self.input_feed, self.input_plunge_feed]:
            w.textChanged.connect(self._update_preview)
            w.textChanged.connect(self._save_params)
        for chk in [self.chk_top, self.chk_plus_x, self.chk_minus_x,
                    self.chk_plus_y, self.chk_minus_y]:
            chk.toggled.connect(self._update_preview)
            chk.toggled.connect(self._save_params)

    def _param_widgets(self):
        return {
            'x': self.input_x,
            'y': self.input_y,
            'z': self.input_z,
            'tool_dia': self.input_tool_dia,
            'stepover_pct': self.input_stepover_pct,
            'depth_per_pass': self.input_depth_per_pass,
            'surface_depth': self.input_surface_depth,
            'rpm': self.input_rpm,
            'feed': self.input_feed,
            'plunge_feed': self.input_plunge_feed,
        }

    def _checkbox_widgets(self):
        return {
            'top': self.chk_top,
            'plus_x': self.chk_plus_x,
            'minus_x': self.chk_minus_x,
            'plus_y': self.chk_plus_y,
            'minus_y': self.chk_minus_y,
        }

    def _save_params(self):
        data = {}
        for key, w in self._param_widgets().items():
            data[key] = w.text()
        for key, chk in self._checkbox_widgets().items():
            data['chk_' + key] = chk.isChecked()
        try:
            with open(BOARD_SQUARING_CONF, 'w') as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def _load_params(self):
        try:
            with open(BOARD_SQUARING_CONF, 'r') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        for key, w in self._param_widgets().items():
            if key in data:
                w.setText(str(data[key]))
        for key, chk in self._checkbox_widgets().items():
            if 'chk_' + key in data:
                chk.setChecked(data['chk_' + key])

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
        tool_dia = self._get_float(self.input_tool_dia, 6)
        self.preview.set_params(board_x, board_y, board_z, ops, depth_per_pass, tool_dia)

        side_passes = math.ceil(board_z / depth_per_pass)
        stepover_pct = self._get_float(self.input_stepover_pct, 70)
        stepover = tool_dia * stepover_pct / 100.0
        padded_y = board_y + tool_dia  # tool_r on each side
        surface_passes = math.ceil(padded_y / stepover)

        info_parts = []
        if "top" in ops:
            info_parts.append("Top: {} passes ({:.1f}mm stepover)".format(
                surface_passes, stepover))
        side_count = len([o for o in ops if o != "top"])
        if side_count:
            info_parts.append("Sides: {} passes/side x {} sides".format(
                side_passes, side_count))
        self.lbl_info.setText("  |  ".join(info_parts))

    def _gen_surfacing(self, lines, board_x, board_y, board_z, tool_dia,
                       stepover, depth, feed, safe_z):
        """Surface the top - offset by tool radius to cover full board area."""
        tool_r = tool_dia / 2
        # Extend beyond board edges by tool radius so cutter fully covers all edges
        x_start = -tool_r
        x_end = board_x + tool_r
        y_start = -tool_r
        y_end = board_y + tool_r
        padded_y = y_end - y_start
        num_cuts = math.ceil(padded_y / stepover)
        actual_stepover = padded_y / num_cuts

        lines.append("(--- SURFACE TOP ---)")
        for i in range(num_cuts):
            y_pos = y_start + i * actual_stepover
            lines.append("G0 X{:.2f} Y{:.2f}".format(x_end, y_pos))
            lines.append("G1 Z{:.2f} F{}".format(board_z - depth, feed))
            lines.append("G1 X{:.2f} F{}".format(x_start, feed))
            lines.append("G0 Z{:.1f}".format(safe_z))
        lines.append("")

    def _gen_side_cut(self, lines, axis, position, cut_start, cut_end, board_z,
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
                    # Climb cut in +Y direction
                    lines.append("G0 X{:.2f} Y{:.2f}".format(position, cut_start))
                    lines.append("G1 Z{:.2f} F{}".format(z_level, plunge_feed))
                    lines.append("G1 Y{:.2f} F{}".format(cut_end, feed))
                else:
                    # Climb cut in -Y direction
                    lines.append("G0 X{:.2f} Y{:.2f}".format(position, cut_end))
                    lines.append("G1 Z{:.2f} F{}".format(z_level, plunge_feed))
                    lines.append("G1 Y{:.2f} F{}".format(cut_start, feed))
                lines.append("G0 Z{:.1f}".format(safe_z))
        else:
            # Cutting along X at fixed Y position
            for p in range(num_passes):
                z_level = board_z - (p + 1) * depth_per_pass
                if z_level < 0:
                    z_level = 0
                if climb_positive:
                    # Climb cut in +X direction
                    lines.append("G0 Y{:.2f} X{:.2f}".format(position, cut_start))
                    lines.append("G1 Z{:.2f} F{}".format(z_level, plunge_feed))
                    lines.append("G1 X{:.2f} F{}".format(cut_end, feed))
                else:
                    # Climb cut in -X direction
                    lines.append("G0 Y{:.2f} X{:.2f}".format(position, cut_end))
                    lines.append("G1 Z{:.2f} F{}".format(z_level, plunge_feed))
                    lines.append("G1 X{:.2f} F{}".format(cut_start, feed))
                lines.append("G0 Z{:.1f}".format(safe_z))

    def _generate_gcode(self):
        board_x = self._get_float(self.input_x, 100)
        board_y = self._get_float(self.input_y, 74)
        board_z = self._get_float(self.input_z, 16.6)
        tool_dia = self._get_float(self.input_tool_dia, 6)
        stepover_pct = self._get_float(self.input_stepover_pct, 70)
        stepover = tool_dia * stepover_pct / 100.0
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
        lines.append("(Tool Dia={:.1f} Stepover={:.1f}mm at {:.0f}% Depth/Pass={:.1f})".format(
            tool_dia, stepover, stepover_pct, depth_per_pass))
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

        tool_r = tool_dia / 2

        # 2. +X end (end grain) - tool center at board_x + radius
        #    Cutting along Y, extend past corners by tool_r
        #    Tool outside at +X, board to left: climb = -Y
        if "+x" in ops:
            lines.append("(--- MILL +X END - end grain ---)")
            self._gen_side_cut(lines, "X", board_x + tool_r,
                               -tool_r, board_y + tool_r, board_z,
                               depth_per_pass, feed, plunge_feed, safe_z, False)
            lines.append("G53 G0 Z-5 (safe retract between ops)")
            lines.append("")

        # 3. -X end (end grain) - tool center at 0 - radius
        #    Cutting along Y, extend past corners by tool_r
        #    Tool outside at -X, board to right: climb = +Y
        if "-x" in ops:
            lines.append("(--- MILL -X END - end grain ---)")
            self._gen_side_cut(lines, "X", -tool_r,
                               -tool_r, board_y + tool_r, board_z,
                               depth_per_pass, feed, plunge_feed, safe_z, True)
            lines.append("G53 G0 Z-5 (safe retract between ops)")
            lines.append("")

        # 4. +Y side - tool center at board_y + radius
        #    Cutting along X, extend past corners by tool_r
        #    Tool outside at +Y, board below: climb = +X
        if "+y" in ops:
            lines.append("(--- MILL +Y SIDE ---)")
            self._gen_side_cut(lines, "Y", board_y + tool_r,
                               -tool_r, board_x + tool_r, board_z,
                               depth_per_pass, feed, plunge_feed, safe_z, True)
            lines.append("G53 G0 Z-5 (safe retract between ops)")
            lines.append("")

        # 5. -Y side - tool center at 0 - radius
        #    Cutting along X, extend past corners by tool_r
        #    Tool outside at -Y, board above: climb = -X
        if "-y" in ops:
            lines.append("(--- MILL -Y SIDE ---)")
            self._gen_side_cut(lines, "Y", -tool_r,
                               -tool_r, board_x + tool_r, board_z,
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
