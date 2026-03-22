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
        self.compensate_x = False
        self.ops = []
        self.depth_per_pass = 1

    def set_params(self, board_x, board_y, board_z, ops, depth_per_pass=1,
                   tool_dia=6, compensate_x=False):
        self.board_x = board_x
        self.board_y = board_y
        self.board_z = board_z
        self.ops = ops
        self.depth_per_pass = depth_per_pass
        self.tool_dia = tool_dia
        self.compensate_x = compensate_x
        self.update()

    def paintEvent(self, event):
        if self.board_x <= 0 or self.board_y <= 0 or self.board_z <= 0:
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor(30, 30, 30))

        w = self.width()
        h = self.height()

        top_h = int(h * 0.6)
        side_h = h - top_h

        # --- TOP VIEW ---
        dim_space = 70
        dim_space_t = 35
        dim_space_r = 45

        draw_area_w = w - dim_space - dim_space_r
        draw_area_h = top_h - dim_space_t - dim_space

        tool_r = self.tool_dia / 2
        has_perim = "perimeter" in self.ops
        if has_perim and self.compensate_x:
            total_x = self.board_x + self.tool_dia
        else:
            total_x = self.board_x
        total_y = self.board_y + (self.tool_dia if has_perim else 0)

        scale_x = draw_area_w / total_x
        scale_y = draw_area_h / total_y
        scale = min(scale_x, scale_y) * 0.88

        actual_w = self.board_x * scale
        actual_h = self.board_y * scale
        total_w = total_x * scale
        total_h = total_y * scale

        # Board origin (0,0) is at bottom-left, tool path extends to +X and +Y only
        cx = dim_space + (draw_area_w - total_w) / 2
        cy = dim_space_t + (draw_area_h - total_h) / 2 + (self.tool_dia * scale if has_perim else 0)

        def tx(x):
            return cx + x * scale

        def ty(y):
            return cy + actual_h - y * scale

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

        # --- Draw shapes ---

        # Tool swath fill (outermost)
        if tool_r > 0 and has_perim:
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(255, 200, 50, 20))
            painter.drawRect(QtCore.QRectF(
                tx(0), ty(total_y),
                total_w, total_h))

        # Tool center path - dashed yellow
        if tool_r > 0 and has_perim:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 200, 50, 150), 1.5, QtCore.Qt.DashLine))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(QtCore.QRectF(
                tx(0), ty(total_y),
                total_w, total_h))

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

        # --- Operation labels ---
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)

        op_num = 1

        # Perimeter label
        if has_perim:
            # Draw perimeter cut lines on tool path
            perim_color = QtGui.QColor(255, 130, 70)
            painter.setPen(QtGui.QPen(perim_color, 2))
            # Draw all 4 sides of the tool path rectangle
            td = self.tool_dia
            cut_x = total_x
            cut_y = total_y
            corners = [
                (tx(0), ty(cut_y)),
                (tx(cut_x), ty(cut_y)),
                (tx(cut_x), ty(0)),
                (tx(0), ty(0)),
            ]
            for i in range(4):
                x1, y1 = corners[i]
                x2, y2 = corners[(i + 1) % 4]
                painter.drawLine(QtCore.QPointF(x1, y1), QtCore.QPointF(x2, y2))

            # Arrows showing cut direction (clockwise for climb with M3)
            arrow_color = QtGui.QColor(255, 130, 70, 200)
            painter.setPen(QtGui.QPen(arrow_color, 1.5))
            # Small arrows at midpoints of each side
            mid_points = []
            for i in range(4):
                x1, y1 = corners[i]
                x2, y2 = corners[(i + 1) % 4]
                mid_points.append(((x1 + x2) / 2, (y1 + y2) / 2))

            painter.setPen(perim_color)
            painter.drawText(QtCore.QRectF(tx(0), ty(self.board_y), actual_w, actual_h / 4),
                             QtCore.Qt.AlignCenter,
                             "{}: Perimeter".format(op_num))
            op_num += 1

        # Surface top label
        if "top" in self.ops:
            painter.setPen(QtGui.QColor(0, 220, 0))
            painter.drawText(QtCore.QRectF(tx(0), ty(self.board_y) + actual_h * 0.3,
                                           actual_w, actual_h / 3),
                             QtCore.Qt.AlignCenter,
                             "{}: Surface Top".format(op_num))
            op_num += 1

        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)

        # --- Extension lines ---
        ext_color = QtGui.QColor(80, 80, 80)
        ext_pen = QtGui.QPen(ext_color, 1, QtCore.Qt.DotLine)

        board_bottom = ty(0)
        dim_y_inner = board_bottom + 18
        dim_y_outer = board_bottom + 36

        painter.setPen(ext_pen)
        painter.drawLine(QtCore.QPointF(tx(0), board_bottom + 2),
                         QtCore.QPointF(tx(0), dim_y_outer + 6))
        painter.drawLine(QtCore.QPointF(tx(self.board_x), board_bottom + 2),
                         QtCore.QPointF(tx(self.board_x), dim_y_outer + 6))
        if has_perim and total_x != self.board_x:
            painter.drawLine(QtCore.QPointF(tx(total_x), ty(0) + 2),
                             QtCore.QPointF(tx(total_x), dim_y_outer + 6))

        board_left = tx(0)
        dim_x_inner = board_left - 18
        dim_x_outer = board_left - 36

        painter.drawLine(QtCore.QPointF(board_left - 2, ty(0)),
                         QtCore.QPointF(dim_x_outer - 6, ty(0)))
        painter.drawLine(QtCore.QPointF(board_left - 2, ty(self.board_y)),
                         QtCore.QPointF(dim_x_outer - 6, ty(self.board_y)))
        if has_perim:
            painter.drawLine(QtCore.QPointF(board_left - 2, ty(total_y)),
                             QtCore.QPointF(dim_x_outer - 6, ty(total_y)))

        # --- Dimension lines ---
        font.setPointSize(9)
        font.setBold(False)
        painter.setFont(font)

        dim_color = QtGui.QColor(180, 180, 180)
        draw_dim_h(dim_y_inner, tx(0), tx(self.board_x),
                   "{:.1f} (final)".format(self.board_x), dim_color)
        if has_perim and total_x != self.board_x:
            tp_color = QtGui.QColor(255, 200, 50, 200)
            draw_dim_h(dim_y_outer, tx(0), tx(total_x),
                       "{:.1f} (cut path)".format(total_x), tp_color)

        draw_dim_v(dim_x_inner, ty(self.board_y), ty(0),
                   "{:.1f} (final)".format(self.board_y), dim_color)
        if has_perim:
            tp_color = QtGui.QColor(255, 200, 50, 200)
            draw_dim_v(dim_x_outer, ty(total_y), ty(0),
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

        legend_x = w - 185
        legend_y = 10
        painter.setPen(QtGui.QPen(QtGui.QColor(140, 140, 160), 2))
        painter.drawLine(QtCore.QPointF(legend_x, legend_y + 4),
                         QtCore.QPointF(legend_x + 16, legend_y + 4))
        painter.setPen(QtGui.QColor(180, 180, 180))
        painter.drawText(QtCore.QPointF(legend_x + 20, legend_y + 8),
                         "Board ({:.1f} x {:.1f})".format(self.board_x, self.board_y))

        if has_perim:
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

        # Draw depth pass lines for perimeter cuts
        if has_perim and self.depth_per_pass > 0:
            start_z = self.board_z + 4  # extra material
            num_passes = math.ceil(start_z / self.depth_per_pass)
            for p in range(num_passes):
                z_level = start_z - (p + 1) * self.depth_per_pass
                if z_level < 0:
                    z_level = 0
                alpha = 80 + int(175 * (p + 1) / num_passes)
                green = 255 - int(150 * p / max(num_passes - 1, 1))
                painter.setPen(QtGui.QPen(QtGui.QColor(0, green, 0, alpha), 2))
                y_line = stz(z_level)
                painter.drawLine(QtCore.QPointF(stx(0), y_line),
                                 QtCore.QPointF(stx(self.board_x), y_line))

        # Z height label
        painter.setPen(QtGui.QColor(180, 180, 180))
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(QtCore.QPointF(s_ox - 55, stz(self.board_z / 2) + 4),
                         "Z: {:.1f}".format(self.board_z))

        # X length label
        painter.drawText(QtCore.QPointF(stx(self.board_x / 2) - 25, stz(0) + 28),
                         "X: {:.1f} mm".format(self.board_x))

        # Z=0 and Z=top labels
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(120, 120, 120))
        painter.drawText(QtCore.QPointF(s_ox - 30, stz(0) + 4), "Z=0")
        painter.drawText(QtCore.QPointF(s_ox - 55, stz(self.board_z) + 4),
                         "Z={:.1f}".format(self.board_z))

        # Surface depth indicator
        if "top" in self.ops:
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 200, 0, 150), 1, QtCore.Qt.DashLine))
            surf_line_z = stz(self.board_z) + 3
            painter.drawLine(QtCore.QPointF(stx(0), surf_line_z),
                             QtCore.QPointF(stx(self.board_x), surf_line_z))
            painter.setPen(QtGui.QColor(0, 200, 0, 180))
            painter.drawText(QtCore.QPointF(stx(self.board_x) + 5, surf_line_z + 4),
                             "surface")

        # Depth per pass and pass count labels
        if has_perim and self.depth_per_pass > 0:
            start_z = self.board_z + 4
            num_passes = math.ceil(start_z / self.depth_per_pass)
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

        self.input_rough_sides = make_input(0.2)
        tool_layout.addRow("Roughing Sides (mm):", self.input_rough_sides)

        self.input_rough_top = make_input(1.0)
        tool_layout.addRow("Roughing Top (mm):", self.input_rough_top)

        self.input_rpm = make_input(22000, int_val)
        tool_layout.addRow("Spindle Speed (RPM):", self.input_rpm)

        self.input_feed = make_input(6000, int_val)
        tool_layout.addRow("Feed Rate (mm/min):", self.input_feed)

        self.input_plunge_feed = make_input(1000, int_val)
        tool_layout.addRow("Plunge Feed (mm/min):", self.input_plunge_feed)

        self.input_finish_feed_pct = make_input(50, int_val)
        tool_layout.addRow("Finish Side Feed (%):", self.input_finish_feed_pct)

        left_layout.addWidget(tool_group)

        # Operations
        ops_group = QtWidgets.QGroupBox("Operations (in order)")
        ops_layout = QtWidgets.QVBoxLayout(ops_group)
        ops_layout.setSpacing(4)

        self.chk_perimeter = QtWidgets.QCheckBox("1. Mill perimeter (all 4 sides)")
        self.chk_perimeter.setChecked(True)
        ops_layout.addWidget(self.chk_perimeter)

        self.chk_top = QtWidgets.QCheckBox("2. Surface top (both edges inward)")
        self.chk_top.setChecked(True)
        ops_layout.addWidget(self.chk_top)

        left_layout.addWidget(ops_group)

        # Options
        opts_group = QtWidgets.QGroupBox("Options")
        opts_layout = QtWidgets.QVBoxLayout(opts_group)
        opts_layout.setSpacing(4)

        self.chk_compensate_x = QtWidgets.QCheckBox("Compensate X length for tool diameter")
        self.chk_compensate_x.setChecked(False)
        opts_layout.addWidget(self.chk_compensate_x)

        self.chk_finishing_pass = QtWidgets.QCheckBox("Finishing pass on top surface")
        self.chk_finishing_pass.setChecked(False)
        opts_layout.addWidget(self.chk_finishing_pass)

        left_layout.addWidget(opts_group)
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
                  self.input_depth_per_pass, self.input_rough_sides,
                  self.input_rough_top, self.input_finish_feed_pct,
                  self.input_rpm, self.input_feed, self.input_plunge_feed]:
            w.textChanged.connect(self._update_preview)
            w.textChanged.connect(self._save_params)
        for chk in [self.chk_perimeter, self.chk_top, self.chk_compensate_x,
                    self.chk_finishing_pass]:
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
            'rough_sides': self.input_rough_sides,
            'rough_top': self.input_rough_top,
            'rpm': self.input_rpm,
            'feed': self.input_feed,
            'plunge_feed': self.input_plunge_feed,
            'finish_feed_pct': self.input_finish_feed_pct,
        }

    def _checkbox_widgets(self):
        return {
            'perimeter': self.chk_perimeter,
            'top': self.chk_top,
            'compensate_x': self.chk_compensate_x,
            'finishing_pass': self.chk_finishing_pass,
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
        if self.chk_perimeter.isChecked():
            ops.append("perimeter")
        if self.chk_top.isChecked():
            ops.append("top")
        return ops

    def _update_preview(self):
        board_x = self._get_float(self.input_x, 100)
        board_y = self._get_float(self.input_y, 74)
        board_z = self._get_float(self.input_z, 16.6)
        ops = self._enabled_ops()

        depth_per_pass = self._get_float(self.input_depth_per_pass, 1)
        tool_dia = self._get_float(self.input_tool_dia, 6)
        compensate_x = self.chk_compensate_x.isChecked()
        self.preview.set_params(board_x, board_y, board_z, ops, depth_per_pass,
                                tool_dia, compensate_x)

        start_z = board_z + 4
        side_passes = math.ceil(start_z / depth_per_pass)
        stepover_pct = self._get_float(self.input_stepover_pct, 70)
        stepover = tool_dia * stepover_pct / 100.0
        padded_y = board_y + tool_dia  # 0 to board_y + tool_dia
        surface_passes = math.ceil(padded_y / stepover)

        info_parts = []
        if "perimeter" in ops:
            info_parts.append("Perimeter: {} depth passes x 4 sides".format(side_passes))
        if "top" in ops:
            info_parts.append("Top: {} passes ({:.1f}mm stepover, both edges inward)".format(
                surface_passes, stepover))
        self.lbl_info.setText("  |  ".join(info_parts))

    def _gen_perimeter(self, lines, board_x, board_y, board_z, tool_r,
                       depth_per_pass, feed, plunge_feed, safe_z,
                       compensate_x=False, roughing_offset=0, label=None,
                       single_pass_at_z=None, z_levels_override=None):
        """Mill all 4 sides of the board, one full loop per depth pass.
        Climb cutting with M3 CW = go around the perimeter clockwise
        when viewed from above: +X(down -Y), -Y(left -X), -X(up +Y), +Y(right +X).
        roughing_offset: extra outward offset (e.g. 0.2mm for roughing).
        single_pass_at_z: if set, do one loop at this Z instead of multiple passes."""

        # Cut positions (tool center path)
        if compensate_x:
            x_plus = board_x + tool_r * 2 + roughing_offset
        else:
            x_plus = board_x + roughing_offset
        x_minus = -roughing_offset
        y_plus = board_y + tool_r * 2 + roughing_offset
        y_minus = -roughing_offset

        if z_levels_override is not None:
            z_levels = z_levels_override
        elif single_pass_at_z is not None:
            z_levels = [single_pass_at_z]
        else:
            start_z = board_z + 4  # extra material allowance
            num_passes = math.ceil(start_z / depth_per_pass)
            z_levels = []
            for p in range(num_passes):
                z_level = start_z - (p + 1) * depth_per_pass
                if z_level < 0:
                    z_level = 0
                z_levels.append(z_level)

        if label:
            if single_pass_at_z is not None:
                lines.append("(--- MILL PERIMETER {} - single pass at Z={:.2f} ---)".format(
                    label, z_levels[0]))
            else:
                lines.append("(--- MILL PERIMETER {} - all 4 sides per depth pass ---)".format(label))
        else:
            lines.append("(--- MILL PERIMETER - all 4 sides per depth pass ---)")
        lines.append("(Climb cutting clockwise: +X, -Y, -X, +Y)")
        lines.append("")

        for i, z_level in enumerate(z_levels):
            lines.append("(--- Pass {} of {}, Z={:.2f} ---)".format(
                i + 1, len(z_levels), z_level))

            # Start at top-right corner (+X, +Y)
            lines.append("G0 X{:.2f} Y{:.2f}".format(x_plus, y_plus))
            lines.append("G1 Z{:.2f} F{}".format(z_level, plunge_feed))

            # +X side: go down from +Y to -Y (climb with M3)
            lines.append("G1 Y{:.2f} F{}".format(y_minus, feed))

            # -Y side: go left from +X to -X
            lines.append("G1 X{:.2f} F{}".format(x_minus, feed))

            # -X side: go up from -Y to +Y
            lines.append("G1 Y{:.2f} F{}".format(y_plus, feed))

            # +Y side: go right from -X to +X (back to start)
            lines.append("G1 X{:.2f} F{}".format(x_plus, feed))

            lines.append("G0 Z{:.1f}".format(safe_z))
            lines.append("")

    def _gen_surfacing_at_z(self, lines, board_x, board_y, cut_z, tool_dia,
                           stepover, feed, safe_z, compensate_x=False,
                           label=None):
        """Surface the top using both-edges-inward method.
        cut_z is the exact Z height to cut at.
        Alternating climb passes from near (Y=0) and far (Y=max) edges
        working toward the middle. Tool path extends beyond board by tool_r."""
        tool_r = tool_dia / 2
        # Stay at X=0, Y=0 on left/front, extend by full tool dia on right/back
        x_start = 0
        if compensate_x:
            x_end = board_x + tool_r * 2
        else:
            x_end = board_x
        y_start = 0
        y_end = board_y + tool_r * 2
        span = y_end - y_start
        half = span / 2

        # Build near and far position lists
        # Both lists go past the midpoint to guarantee overlap
        near_positions = []
        pos = y_start
        mid = y_start + half
        while pos <= mid + stepover:
            near_positions.append(pos)
            pos += stepover
            if pos > y_end:
                break

        far_positions = []
        pos = y_end
        mid_far = y_end - half
        while pos >= mid_far - stepover:
            far_positions.append(pos)
            pos -= stepover
            if pos < y_start:
                break

        # Interleave: near, far, near, far...
        passes = []
        ni = 0
        fi = 0
        from_near = True
        while ni < len(near_positions) or fi < len(far_positions):
            if from_near and ni < len(near_positions):
                passes.append((near_positions[ni], False))  # False = climb from far end
                ni += 1
            elif not from_near and fi < len(far_positions):
                passes.append((far_positions[fi], True))    # True = climb from near end
                fi += 1
            elif ni < len(near_positions):
                passes.append((near_positions[ni], False))
                ni += 1
            else:
                passes.append((far_positions[fi], True))
                fi += 1
            from_near = not from_near

        if label:
            lines.append("(--- SURFACE TOP {} - both edges inward, Z={:.2f} ---)".format(
                label, cut_z))
        else:
            lines.append("(--- SURFACE TOP - both edges inward ---)")
        for y_pos, reverse in passes:
            if reverse:
                # Cut from x_start to x_end (climb from near edge)
                lines.append("G0 X{:.2f} Y{:.2f}".format(x_start, y_pos))
                lines.append("G1 Z{:.2f} F{}".format(cut_z, feed))
                lines.append("G1 X{:.2f} F{}".format(x_end, feed))
            else:
                # Cut from x_end to x_start (climb from far edge)
                lines.append("G0 X{:.2f} Y{:.2f}".format(x_end, y_pos))
                lines.append("G1 Z{:.2f} F{}".format(cut_z, feed))
                lines.append("G1 X{:.2f} F{}".format(x_start, feed))
            lines.append("G0 Z{:.1f}".format(safe_z))
        lines.append("")

    def _generate_gcode(self):
        board_x = self._get_float(self.input_x, 100)
        board_y = self._get_float(self.input_y, 74)
        board_z = self._get_float(self.input_z, 16.6)
        tool_dia = self._get_float(self.input_tool_dia, 6)
        stepover_pct = self._get_float(self.input_stepover_pct, 70)
        stepover = tool_dia * stepover_pct / 100.0
        depth_per_pass = self._get_float(self.input_depth_per_pass, 1)
        rough_sides = self._get_float(self.input_rough_sides, 0.2)
        rough_top = self._get_float(self.input_rough_top, 1.0)
        rpm = int(self._get_float(self.input_rpm, 22000))
        feed = int(self._get_float(self.input_feed, 6000))
        plunge_feed = int(self._get_float(self.input_plunge_feed, 1000))
        ops = self._enabled_ops()
        compensate_x = self.chk_compensate_x.isChecked()

        tool_r = tool_dia / 2
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

        finishing = self.chk_finishing_pass.isChecked()

        # 1. Perimeter - all 4 sides, one loop per depth pass
        if "perimeter" in ops:
            if finishing:
                # Roughing: outward offset, full depth
                self._gen_perimeter(lines, board_x, board_y, board_z, tool_r,
                                    depth_per_pass, feed, plunge_feed, safe_z,
                                    compensate_x, roughing_offset=rough_sides,
                                    label="ROUGHING")
                lines.append("G53 G0 Z-5 (safe retract between passes)")
                lines.append("")
                # Finishing: exact final positions, half-tool-dia depth passes, slower feed
                finish_feed_pct = self._get_float(self.input_finish_feed_pct, 50)
                finish_feed = int(feed * finish_feed_pct / 100.0)
                finish_depth = tool_dia / 2  # half tool diameter
                start_z = board_z + 4
                finish_z_levels = []
                z = start_z
                while z > 0:
                    z -= finish_depth
                    if z < 0:
                        z = 0
                    finish_z_levels.append(z)
                self._gen_perimeter(lines, board_x, board_y, board_z, tool_r,
                                    depth_per_pass, finish_feed, plunge_feed, safe_z,
                                    compensate_x, roughing_offset=0,
                                    label="FINISHING", z_levels_override=finish_z_levels)
            else:
                self._gen_perimeter(lines, board_x, board_y, board_z, tool_r,
                                    depth_per_pass, feed, plunge_feed, safe_z,
                                    compensate_x)
            lines.append("G53 G0 Z-5 (safe retract between ops)")
            lines.append("")

        # 2. Surface top - both edges inward
        if "top" in ops:
            if finishing:
                # Roughing pass: cut above final by rough_top allowance
                self._gen_surfacing_at_z(lines, board_x, board_y, board_z + rough_top,
                                         tool_dia, stepover, feed, safe_z,
                                         compensate_x, label="ROUGHING")
                lines.append("")
                # Finishing pass: cut to board_z (final dimension)
                self._gen_surfacing_at_z(lines, board_x, board_y, board_z,
                                         tool_dia, stepover, feed, safe_z,
                                         compensate_x, label="FINISHING")
            else:
                self._gen_surfacing_at_z(lines, board_x, board_y, board_z,
                                         tool_dia, stepover, feed, safe_z,
                                         compensate_x)
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
