import sys
import os
import json
import copy
import uuid
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLineEdit, QSpinBox, QDoubleSpinBox,
    QListWidget, QPushButton, QMessageBox, QCheckBox,
    QColorDialog, QGroupBox, QLabel, QFrame, QSplitter,
    QComboBox, QInputDialog, QWidget, QGraphicsDropShadowEffect,
    QApplication, QSizePolicy, QAbstractItemView, QMenu, QAction
)
from PyQt5.QtGui import QColor, QFont, QCursor, QPainter, QBrush, QPen, QColor, QMouseEvent, QPainterPath
from PyQt5.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, QRect, QPoint, pyqtProperty, pyqtSignal, QRectF, QAbstractAnimation

# ==========================================
# 1. 配置定义 (UI Scaling & Themes)
# ==========================================

class ScaleConfig:
    def __init__(self, font_size, row_height, icon_size, padding, spacing):
        self.font_size = font_size
        self.row_height = row_height
        self.icon_size = icon_size
        self.padding = padding
        self.spacing = spacing 

SCALES = {
    "标准 (Standard)": ScaleConfig(14, 38, 20, 8, 15),
    "中号 (Medium)":   ScaleConfig(16, 48, 24, 10, 20),
    "大号 (Large - 老人模式)": ScaleConfig(22, 64, 32, 14, 25)
}

class ThemeConfig:
    def __init__(self, bg_main, bg_side, bg_input, text_main, text_dim, border, primary, danger, shadow):
        self.bg_main = bg_main      
        self.bg_side = bg_side      
        self.bg_input = bg_input    
        self.text_main = text_main  
        self.text_dim = text_dim    
        self.border = border        
        self.primary = primary      
        self.danger = danger        
        self.shadow = shadow        

THEMES = {
    "深色 (Dark)": ThemeConfig(
        bg_main="#1c1c1e", bg_side="#252526", bg_input="#3a3a3c",
        text_main="#ffffff", text_dim="#98989d", border="#454545",
        primary="#0A84FF", danger="#FF453A", shadow=QColor(0, 0, 0, 150)
    ),
    "浅色 (Light)": ThemeConfig(
        bg_main="#ffffff", bg_side="#f2f2f7", bg_input="#ffffff",
        text_main="#000000", text_dim="#6e6e73", border="#c6c6c8", 
        primary="#007AFF", danger="#FF3B30", shadow=QColor(0, 0, 0, 40)
    )
}

# ==========================================
# 2. 全向拖拽基类
# ==========================================
class ResizableFramelessWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._padding = 6
        self._dragging = False
        self._resizing = False
        self._drag_pos = None
        self._resize_edge = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self._hit_test(event.pos())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                event.accept()
            elif event.y() < 60:
                self._dragging = True
                self._drag_pos = event.globalPos() - self.pos()
                event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.y() < 60 and event.button() == Qt.LeftButton:
            if self.isMaximized(): self.showNormal()
            else: self.showMaximized()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._resizing:
            self._handle_resize(event.globalPos())
            event.accept()
            return
        if self._dragging and self._drag_pos:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
            return
        edge = self._hit_test(event.pos())
        if edge: self.setCursor(self._get_cursor(edge))
        else: self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self._dragging = False; self._resizing = False; self._resize_edge = None
        self.setCursor(Qt.ArrowCursor)

    def _hit_test(self, pos):
        if self.isMaximized(): return None
        w, h = self.width(), self.height()
        p = self._padding
        x, y = pos.x(), pos.y()
        on_left = x < p; on_right = x > w - p
        on_top = y < p; on_bottom = y > h - p
        if on_top and on_left: return 'top_left'
        if on_top and on_right: return 'top_right'
        if on_bottom and on_left: return 'bottom_left'
        if on_bottom and on_right: return 'bottom_right'
        if on_top: return 'top'
        if on_bottom: return 'bottom'
        if on_left: return 'left'
        if on_right: return 'right'
        return None

    def _get_cursor(self, edge):
        cursors = {'top': Qt.SizeVerCursor, 'bottom': Qt.SizeVerCursor, 'left': Qt.SizeHorCursor, 'right': Qt.SizeHorCursor, 'top_left': Qt.SizeFDiagCursor, 'bottom_right': Qt.SizeFDiagCursor, 'top_right': Qt.SizeBDiagCursor, 'bottom_left': Qt.SizeBDiagCursor}
        return cursors.get(edge, Qt.ArrowCursor)

    def _handle_resize(self, global_pos):
        rect = self.geometry()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        gx, gy = global_pos.x(), global_pos.y()
        min_w, min_h = self.minimumWidth(), self.minimumHeight()
        
        if 'left' in self._resize_edge:
            delta = x - gx
            if w + delta > min_w: x = gx; w += delta
        elif 'right' in self._resize_edge: w = gx - x
        
        if 'top' in self._resize_edge:
            delta = y - gy
            if h + delta > min_h: y = gy; h += delta
        elif 'bottom' in self._resize_edge: h = gy - y
        
        self.setGeometry(x, y, max(w, min_w), max(h, min_h))

# ==========================================
# 3. 自定义控件
# ==========================================

# --- 新增：带有悬浮阴影动画的 GroupBox ---
class HoverGroupBox(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        # 初始化阴影效果
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(0) # 初始无阴影
        self.shadow.setOffset(0, 4)
        self.shadow.setColor(QColor(0, 0, 0, 0)) # 初始透明
        self.setGraphicsEffect(self.shadow)
        
        # 动画变量
        self.anim = QPropertyAnimation(self.shadow, b"blurRadius")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        
        # 用于主题更新的引用
        self.current_theme_shadow_color = QColor(0,0,0,100)

    def enterEvent(self, event):
        # 鼠标进入：阴影浮现
        self.shadow.setColor(self.current_theme_shadow_color)
        self.anim.stop()
        self.anim.setStartValue(self.shadow.blurRadius())
        self.anim.setEndValue(25) # 阴影大小
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # 鼠标离开：阴影消失
        self.anim.stop()
        self.anim.setStartValue(self.shadow.blurRadius())
        self.anim.setEndValue(0)
        self.anim.start()
        super().leaveEvent(event)
        
    def set_shadow_color(self, color):
        self.current_theme_shadow_color = color
        # 如果当前不是悬浮状态，不立即应用颜色，防止闪烁
        # 但如果是动画中，下次enter会用新颜色


class CycleIconButton(QPushButton):
    valueChanged = pyqtSignal(str)
    def __init__(self, btn_type, options_map, current_key, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(40, 40)
        self.btn_type = btn_type 
        self.options = list(options_map.keys()) 
        self.current_key = current_key
        self.hovered = False
        self.icon_color = QColor("#ffffff")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent; border: none;")

    def set_color(self, text_color):
        self.icon_color = QColor(text_color)
        self.update()

    def enterEvent(self, event):
        self.hovered = True; self.update(); super().enterEvent(event)
    def leaveEvent(self, event):
        self.hovered = False; self.update(); super().leaveEvent(event)

    def mousePressEvent(self, event):
        try:
            curr_idx = self.options.index(self.current_key)
            next_idx = (curr_idx + 1) % len(self.options)
            self.current_key = self.options[next_idx]
            self.valueChanged.emit(self.current_key)
            self.update()
        except ValueError: pass
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.hovered:
            painter.setBrush(QColor(128, 128, 128, 50))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(self.rect(), 8, 8)

        painter.setPen(Qt.NoPen); painter.setBrush(self.icon_color)
        rect = self.rect(); c = rect.center()
        
        if self.btn_type == 'theme':
            if "Light" in self.current_key or "浅色" in self.current_key:
                painter.drawEllipse(c, 6, 6) 
                painter.setPen(QPen(self.icon_color, 2))
                for i in range(8):
                    painter.save(); painter.translate(c); painter.rotate(i * 45)
                    painter.drawLine(0, 9, 0, 11); painter.restore()
            else:
                path = QPainterPath(); path.addEllipse(QRectF(c.x()-6, c.y()-6, 12, 12))
                cut = QPainterPath(); cut.addEllipse(QRectF(c.x()-2, c.y()-8, 12, 12))
                final_path = path.subtracted(cut)
                painter.setPen(Qt.NoPen); painter.setBrush(self.icon_color)
                painter.save(); painter.translate(-2, 2); painter.drawPath(final_path); painter.restore()
        elif self.btn_type == 'scale':
            painter.setPen(self.icon_color)
            f_small = self.font(); f_small.setPixelSize(12); f_small.setBold(True)
            painter.setFont(f_small); painter.drawText(QRect(0, 0, 20, 40), Qt.AlignCenter, "A")
            f_big = self.font(); f_big.setPixelSize(18); f_big.setBold(True)
            painter.setFont(f_big); painter.drawText(QRect(18, 0, 22, 40), Qt.AlignCenter, "A")

class AppleButton(QPushButton):
    def __init__(self, text="", parent=None, is_primary=False, config=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.is_primary = is_primary
        self.is_danger = (text == "删除")
        self.current_scale = SCALES["标准 (Standard)"]
        self.current_theme = THEMES["深色 (Dark)"]
        self.update_style()

    def set_theme_scale(self, theme, scale):
        self.current_theme = theme; self.current_scale = scale; self.update_style()

    def update_style(self):
        cfg = self.current_scale
        thm = self.current_theme
        self.setMinimumHeight(cfg.row_height)
        
        bg_color = thm.bg_input
        text_color = thm.text_main
        border_color = thm.border
        hover_bg = thm.border
        hover_text = thm.text_main
        hover_border = thm.border

        if self.is_primary:
            bg_color = thm.primary; text_color = "#ffffff"; border_color = thm.primary
            hover_bg = "#409cff"; hover_text = "#ffffff"; hover_border = "#409cff"
            
        elif self.is_danger:
            bg_color = thm.bg_input; text_color = thm.danger; border_color = thm.border
            hover_bg = thm.danger; hover_text = "#ffffff"; hover_border = thm.danger
        
        border_style = f"1px solid {border_color}"

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color}; color: {text_color}; border: {border_style};
                border-radius: 8px; font-family: "Microsoft YaHei UI";
                font-size: {cfg.font_size}px; padding: 0 {cfg.padding * 2}px; font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {hover_bg}; color: {hover_text}; border: 1px solid {hover_border};
            }}
            QPushButton:pressed {{ padding-top: 2px; }}
        """)

class AppleColorWell(QPushButton):
    colorChanged = pyqtSignal(str)
    
    PRESET_COLORS = [
        ("红色 (Red)", "#FF3B30"), ("橙色 (Orange)", "#FF9500"), ("黄色 (Yellow)", "#FFCC00"),
        ("绿色 (Green)", "#34C759"), ("薄荷 (Teal)", "#5AC8FA"), ("蓝色 (Blue)", "#007AFF"),
        ("靛蓝 (Indigo)", "#5856D6"), ("紫色 (Purple)", "#AF52DE"), ("粉色 (Pink)", "#FF2D55"),
        ("灰色 (Gray)", "#8E8E93"), ("白色 (White)", "#FFFFFF"), ("黑色 (Black)", "#000000")
    ]

    def __init__(self, color="#ffffff", parent=None):
        super().__init__(parent)
        self.color = color
        self.setCursor(Qt.PointingHandCursor)
        self.current_scale = SCALES["标准 (Standard)"]
        self.current_theme = THEMES["深色 (Dark)"]
        self.clicked.connect(self.choose_color)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def set_theme_scale(self, theme, scale):
        self.current_theme = theme
        self.current_scale = scale
        self.setMinimumHeight(scale.row_height)
        self.update()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        lbl = QAction("⚡ 快速选择颜色:", self); lbl.setEnabled(False); menu.addAction(lbl)
        menu.addSeparator()

        for name, hex_code in self.PRESET_COLORS:
            action = QAction(name, self)
            from PyQt5.QtGui import QPixmap, QIcon
            pix = QPixmap(16, 16); pix.fill(QColor(hex_code))
            action.setIcon(QIcon(pix))
            action.triggered.connect(lambda checked, c=hex_code: self.set_preset_color(c))
            menu.addAction(action)
        menu.exec_(self.mapToGlobal(pos))

    def set_preset_color(self, hex_code):
        self.color = hex_code; self.update(); self.colorChanged.emit(self.color)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        thm = self.current_theme; cfg = self.current_scale
        painter.setBrush(QColor(thm.bg_input)); painter.setPen(QPen(QColor(thm.border), 1))
        rect = self.rect(); painter.drawRoundedRect(rect.adjusted(1,1,-1,-1), 8, 8)
        
        r = cfg.icon_size // 2; cy = rect.height() / 2; cx = 20 + r
        painter.setBrush(QBrush(QColor(self.color))); painter.setPen(QPen(QColor(128, 128, 128, 100), 1)) 
        painter.drawEllipse(QPoint(int(cx), int(cy)), r, r)
        
        painter.setPen(QColor(thm.text_main))
        font = self.font(); font.setFamily("Consolas"); font.setPointSize(max(12, int(cfg.font_size * 0.9)))
        painter.setFont(font)
        text_rect = QRect(int(cx + r + 15), 0, rect.width(), rect.height())
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, self.color.upper())

    def choose_color(self):
        dlg = QColorDialog(self); dlg.setCurrentColor(QColor(self.color))
        if dlg.exec_():
            c = dlg.selectedColor()
            if c.isValid(): self.color = c.name(QColor.HexArgb) if c.alpha() < 255 else c.name(); self.update(); self.colorChanged.emit(self.color)
    def text(self): return self.color
    def setText(self, t): self.color = t; self.update()

class IOSSwitch(QCheckBox):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.current_scale = SCALES["标准 (Standard)"]
        self.current_theme = THEMES["深色 (Dark)"]
    def set_theme_scale(self, theme, scale):
        self.current_theme = theme; self.current_scale = scale; self.update_style()
    def update_style(self):
        cfg = self.current_scale; thm = self.current_theme
        sw_w = int(cfg.row_height * 1.2); sw_h = int(cfg.row_height * 0.7); radius = sw_h // 2
        self.setStyleSheet(f"""
            QCheckBox {{ spacing: 15px; color: {thm.text_main}; font-size: {cfg.font_size}px; padding: 5px; }}
            QCheckBox::indicator {{ width: {sw_w}px; height: {sw_h}px; border-radius: {radius}px; }}
            QCheckBox::indicator:unchecked {{ background-color: {thm.bg_input}; border: 1px solid {thm.border}; }}
            QCheckBox::indicator:checked {{ background-color: #30D158; border: 1px solid #30D158; }}
        """)

# ==========================================
# 4. 主窗口逻辑
# ==========================================

class SettingsDialog(ResizableFramelessWindow):
    def __init__(self, config_dir, current_filename, configs, apply_callback=None, parent=None):
        super().__init__(parent)
        self.config_dir = config_dir
        self.current_filename = current_filename
        self.configs = copy.deepcopy(configs)
        self.apply_callback = apply_callback
        self.current_id = None
        
        self.current_scale_name = "标准 (Standard)"
        self.current_theme_name = "深色 (Dark)"
        
        self.setup_ui()
        self.load_button_list()
        self.refresh_theme_scale()
        if self.configs['buttons']: self.button_list.setCurrentRow(0)

    def setup_ui(self):
        self.resize(1100, 780)
        outer_layout = QVBoxLayout(self); outer_layout.setContentsMargins(6, 6, 6, 6) 
        self.main_frame = QFrame(); self.main_frame.setObjectName("MainFrame")
        self.shadow_effect = QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(20); self.shadow_effect.setOffset(0, 0)
        self.main_frame.setGraphicsEffect(self.shadow_effect)
        outer_layout.addWidget(self.main_frame)
        
        frame_layout = QVBoxLayout(self.main_frame); frame_layout.setContentsMargins(0, 0, 0, 0); frame_layout.setSpacing(0)
        
        # === 标题栏 ===
        title_bar = QFrame(); title_bar.setFixedHeight(50); title_bar.setObjectName("TitleBar")
        tb_layout = QHBoxLayout(title_bar); tb_layout.setContentsMargins(20, 0, 20, 0)
        self.title_lbl = QLabel("按钮配置中心"); self.title_lbl.setObjectName("TitleLabel")
        
        self.btn_theme_toggle = CycleIconButton('theme', THEMES, self.current_theme_name)
        self.btn_theme_toggle.valueChanged.connect(self.on_theme_changed); self.btn_theme_toggle.setToolTip("切换颜色主题")

        self.btn_scale_toggle = CycleIconButton('scale', SCALES, self.current_scale_name)
        self.btn_scale_toggle.valueChanged.connect(self.on_scale_changed); self.btn_scale_toggle.setToolTip("切换界面尺寸")
        
        win_btns_layout = QHBoxLayout(); win_btns_layout.setSpacing(8)
        self.btn_max = QPushButton("□"); self.btn_max.setObjectName("MaxBtn"); self.btn_max.setFixedSize(32, 32)
        self.btn_max.setCursor(Qt.PointingHandCursor); self.btn_max.clicked.connect(self.toggle_max); self.btn_max.setToolTip("最大化/还原")

        close_btn = QPushButton("✕"); close_btn.setObjectName("CloseBtn"); close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor); close_btn.clicked.connect(self.reject); close_btn.setToolTip("关闭")
        
        win_btns_layout.addWidget(self.btn_max); win_btns_layout.addWidget(close_btn)
        
        tb_layout.addWidget(self.title_lbl); tb_layout.addStretch()
        tb_layout.addWidget(self.btn_theme_toggle); tb_layout.addSpacing(10)
        tb_layout.addWidget(self.btn_scale_toggle); tb_layout.addSpacing(15)
        tb_layout.addLayout(win_btns_layout)
        frame_layout.addWidget(title_bar)
        
        # === 内容区 ===
        content_box = QHBoxLayout(); content_box.setContentsMargins(0, 0, 0, 0); content_box.setSpacing(0)
        self.splitter = QSplitter(Qt.Horizontal); self.splitter.setHandleWidth(1)
        
        # --- 左侧栏 ---
        self.left_widget = QWidget()
        self.left_layout = QVBoxLayout(self.left_widget); self.left_layout.setContentsMargins(15, 15, 15, 15)
        self.lbl_cfg = QLabel("配置文件"); self.left_layout.addWidget(self.lbl_cfg)
        self.config_combo = QComboBox(); self.config_combo.currentTextChanged.connect(self.on_config_changed)
        self.left_layout.addWidget(self.config_combo)
        
        cfg_btns = QHBoxLayout()
        self.btn_new_cfg = AppleButton("新建"); self.btn_new_cfg.clicked.connect(self.create_config)
        self.btn_del_cfg = AppleButton("删除"); self.btn_del_cfg.clicked.connect(self.delete_config)
        cfg_btns.addWidget(self.btn_new_cfg); cfg_btns.addWidget(self.btn_del_cfg)
        self.left_layout.addLayout(cfg_btns)
        
        self.lbl_list = QLabel("按钮列表"); self.left_layout.addWidget(self.lbl_list)
        self.button_list = QListWidget(); self.button_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.button_list.currentItemChanged.connect(self.select_button)
        self.left_layout.addWidget(self.button_list)
        
        list_btns = QHBoxLayout()
        self.btn_add = AppleButton("＋ 新增", is_primary=True); self.btn_add.clicked.connect(self.create_new_button)
        self.btn_copy = AppleButton("复制"); self.btn_copy.clicked.connect(self.copy_button)
        self.btn_del = AppleButton("删除"); self.btn_del.clicked.connect(self.delete_button)
        list_btns.addWidget(self.btn_add); list_btns.addWidget(self.btn_copy); list_btns.addWidget(self.btn_del)
        self.left_layout.addLayout(list_btns)
        
        # --- 右侧栏 ---
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget); self.right_layout.setContentsMargins(25, 20, 25, 20)
        
        # 1. 基本 (使用新的 HoverGroupBox)
        self.group_basic = HoverGroupBox("基本属性") # 修改这里
        self.form_basic = QFormLayout(); self.form_basic.setLabelAlignment(Qt.AlignRight)
        
        self.label_edit = QLineEdit(); self.label_edit.textChanged.connect(self.sync_current_data)
        
        font_layout = QHBoxLayout()
        self.font_combo = QComboBox(); self.font_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        from PyQt5.QtGui import QFontDatabase
        self.font_combo.addItems(QFontDatabase().families()); self.font_combo.setEditable(True)
        self.font_combo.currentTextChanged.connect(self.sync_current_data)
        self.btn_apply_font = AppleButton("全应用"); self.btn_apply_font.clicked.connect(self.apply_font_to_all)
        font_layout.addWidget(self.font_combo); font_layout.addWidget(self.btn_apply_font)
        
        shortcut_layout = QHBoxLayout()
        self.shortcut_edit = QLineEdit(); self.shortcut_edit.textChanged.connect(self.on_shortcut_changed)
        self.btn_record = AppleButton("录制"); self.btn_record.setCheckable(True); self.btn_record.clicked.connect(self.toggle_key_detection)
        shortcut_layout.addWidget(self.shortcut_edit); shortcut_layout.addWidget(self.btn_record)
        
        self.chk_lock = IOSSwitch("锁定坐标位置")
        self.chk_lock.stateChanged.connect(self.on_position_lock_changed); self.chk_lock.stateChanged.connect(self.sync_current_data)
        
        self.form_basic.addRow("名称:", self.label_edit)
        self.form_basic.addRow("字体:", font_layout)
        self.form_basic.addRow("热键:", shortcut_layout)
        self.form_basic.addRow("", self.chk_lock)
        self.group_basic.setLayout(self.form_basic)
        
        # 2. 样式 (使用新的 HoverGroupBox)
        self.group_style = HoverGroupBox("外观样式") # 修改这里
        style_box = QVBoxLayout()
        
        row_colors = QHBoxLayout(); row_colors.setSpacing(15)
        v1 = QVBoxLayout(); self.lbl_c1 = QLabel("背景"); v1.addWidget(self.lbl_c1); v1.addWidget(self._make_color_well('bg'))
        v2 = QVBoxLayout(); self.lbl_c2 = QLabel("文字"); v2.addWidget(self.lbl_c2); v2.addWidget(self._make_color_well('text'))
        v3 = QVBoxLayout(); self.lbl_c3 = QLabel("边框"); v3.addWidget(self.lbl_c3); v3.addWidget(self._make_color_well('border'))
        row_colors.addLayout(v1); row_colors.addLayout(v2); row_colors.addLayout(v3)
        
        row_nums = QHBoxLayout()
        self.spin_opacity = QDoubleSpinBox(); self.spin_opacity.setRange(0.1, 1.0); self.spin_opacity.setSingleStep(0.1); self.spin_opacity.valueChanged.connect(self.sync_current_data)
        self.spin_size = QSpinBox(); self.spin_size.setRange(8, 300); self.spin_size.valueChanged.connect(self.sync_current_data)
        self.lbl_op = QLabel("透明度:"); self.lbl_op.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_sz = QLabel("字号:"); self.lbl_sz.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row_nums.addWidget(self.lbl_op); row_nums.addWidget(self.spin_opacity)
        row_nums.addSpacing(20); row_nums.addWidget(self.lbl_sz); row_nums.addWidget(self.spin_size)
        style_box.addLayout(row_colors); style_box.addSpacing(15); style_box.addLayout(row_nums)
        self.group_style.setLayout(style_box)
        
        # 3. 布局 (使用新的 HoverGroupBox)
        self.group_pos = HoverGroupBox("位置与尺寸") # 修改这里
        layout_pos = QHBoxLayout()
        self.spin_x = QSpinBox(); self.spin_x.setRange(0, 9999); self.spin_x.setPrefix("X: "); self.spin_x.valueChanged.connect(self.sync_current_data)
        self.spin_y = QSpinBox(); self.spin_y.setRange(0, 9999); self.spin_y.setPrefix("Y: "); self.spin_y.valueChanged.connect(self.sync_current_data)
        self.spin_w = QSpinBox(); self.spin_w.setRange(10, 9999); self.spin_w.setPrefix("W: "); self.spin_w.valueChanged.connect(self.sync_current_data)
        self.spin_h = QSpinBox(); self.spin_h.setRange(10, 9999); self.spin_h.setPrefix("H: "); self.spin_h.valueChanged.connect(self.sync_current_data)
        for sp in [self.spin_x, self.spin_y, self.spin_w, self.spin_h]: layout_pos.addWidget(sp)
        self.group_pos.setLayout(layout_pos)
        
        self.right_layout.addWidget(self.group_basic); self.right_layout.addWidget(self.group_style)
        self.right_layout.addWidget(self.group_pos); self.right_layout.addStretch()
        
        bot_layout = QHBoxLayout()
        self.btn_refresh = AppleButton("立即应用"); self.btn_refresh.clicked.connect(self.on_refresh)
        self.btn_cancel = AppleButton("取消"); self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = AppleButton("保存更改", is_primary=True); self.btn_save.clicked.connect(self.accept)
        bot_layout.addWidget(self.btn_refresh); bot_layout.addStretch(); bot_layout.addWidget(self.btn_cancel); bot_layout.addWidget(self.btn_save)
        self.right_layout.addLayout(bot_layout)
        
        self.splitter.addWidget(self.left_widget); self.splitter.addWidget(self.right_widget)
        self.splitter.setStretchFactor(0, 1); self.splitter.setStretchFactor(1, 3); self.splitter.setCollapsible(0, False)
        content_box.addWidget(self.splitter); frame_layout.addLayout(content_box)
        
        self.load_config_list(); self.shortcut_timer = None

    def _make_color_well(self, type_):
        w = AppleColorWell()
        if type_ == 'bg': self.color_bg = w
        elif type_ == 'text': self.color_text = w
        elif type_ == 'border': self.color_border = w
        w.colorChanged.connect(lambda: self.sync_current_data())
        return w

    def toggle_max(self):
        if self.isMaximized(): self.showNormal()
        else: self.showMaximized()

    def on_scale_changed(self, text): self.current_scale_name = text; self.refresh_theme_scale()
    def on_theme_changed(self, text): self.current_theme_name = text; self.refresh_theme_scale()

    def refresh_theme_scale(self):
        cfg = SCALES[self.current_scale_name]
        thm = THEMES[self.current_theme_name]
        
        self.btn_theme_toggle.set_color(thm.text_main)
        self.btn_scale_toggle.set_color(thm.text_main)
        self.shadow_effect.setColor(thm.shadow)
        
        # 更新 GroupBox 的阴影颜色引用
        shadow_color = QColor(0, 0, 0, 120) if self.current_theme_name == "深色 (Dark)" else QColor(0, 0, 0, 40)
        for gb in self.findChildren(HoverGroupBox):
            gb.set_shadow_color(shadow_color)
            
        max_btn_hover_bg = "#454545" if self.current_theme_name == "深色 (Dark)" else "#e5e5e5"
        
        css = f"""
            #MainFrame {{ background-color: {thm.bg_main}; border-radius: 12px; border: 1px solid {thm.border}; }}
            #TitleBar {{ background-color: transparent; border-bottom: 1px solid {thm.border}; }}
            QWidget {{ font-family: "Microsoft YaHei UI", sans-serif; font-size: {cfg.font_size}px; color: {thm.text_main}; }}
            #TitleLabel {{ font-size: {cfg.font_size + 2}px; font-weight: bold; }}
            QWidget {{ background-color: transparent; }}
            
            #CloseBtn, #MaxBtn {{ background-color: transparent; border: none; border-radius: 6px; color: {thm.text_dim}; font-family: "Segoe UI Symbol"; font-size: 16px; }}
            #CloseBtn:hover {{ background-color: #c42b1c; color: white; }}
            #MaxBtn:hover {{ background-color: {max_btn_hover_bg}; color: {thm.text_main}; }}
            
            /* === GroupBox 样式 (配合 HoverGroupBox 类) === */
            QGroupBox {{
                border: 1px solid {thm.border};
                border-radius: 12px;
                margin-top: 1.5em;
                padding-top: 15px; 
                background-color: {thm.bg_input}; /* 实色背景，遮挡阴影穿透 */
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; subcontrol-position: top left; left: 15px; padding: 0 5px;
                color: {thm.text_dim}; font-weight: bold; font-size: {cfg.font_size}px;
                background-color: transparent;
            }}

            QLineEdit, QSpinBox, QDoubleSpinBox {{
                background-color: {thm.bg_input}; border: 1px solid {thm.border}; border-radius: 6px;
                color: {thm.text_main}; padding: {cfg.padding}px; min-height: {cfg.row_height - (cfg.padding*2)}px;
                selection-background-color: {thm.primary}; selection-color: white;
            }}
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {thm.primary}; }}

            /* === 下拉菜单美化 (ComboBox) === */
            QComboBox {{
                background-color: {thm.bg_input};
                border: 1px solid {thm.border};
                border-radius: 6px;
                color: {thm.text_main};
                padding: {cfg.padding}px;
                padding-right: 30px; /* 给箭头留空间 */
                min-height: {cfg.row_height - (cfg.padding*2)}px;
            }}
            QComboBox:focus {{ border: 1px solid {thm.primary}; }}
            
            /* 下拉箭头区域 */
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left-width: 0px;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background: transparent;
            }}
            /* 箭头本身 */
            QComboBox::down-arrow {{
                width: 12px; height: 12px;
                image: none; /* 清除默认 */
                border-left: 2px solid {thm.text_dim}; /* 用边框画箭头 */
                border-bottom: 2px solid {thm.text_dim};
                transform: rotate(-45deg); /* 旋转成向下箭头 */
                margin-top: -3px; /* 微调位置 */
            }}
            QComboBox::down-arrow:on {{ /* 展开时箭头反转 */
                transform: rotate(135deg);
                margin-top: 3px;
            }}
            
            /* 下拉弹出列表 */
            QComboBox QAbstractItemView {{
                background-color: {thm.bg_input};
                color: {thm.text_main};
                border: 1px solid {thm.border};
                selection-background-color: {thm.primary};
                selection-color: white;
                outline: none;
                border-radius: 8px;
                padding: 4px; /* 列表整体内边距 */
            }}
            QComboBox QAbstractItemView::item {{
                height: {cfg.row_height}px; /* 增加行高 */
                padding: 4px 8px;
                border-radius: 4px; /* 选项圆角 */
            }}
            
            QMenu {{ background-color: {thm.bg_main}; border: 1px solid {thm.border}; border-radius: 10px; padding: 6px; }}
            QMenu::item {{ background-color: transparent; padding: 8px 20px; border-radius: 6px; color: {thm.text_main}; }}
            QMenu::item:selected {{ background-color: {thm.primary}; color: white; }}
            QMenu::separator {{ height: 1px; background: {thm.border}; margin: 4px 10px; }}

            QListWidget {{ background-color: {thm.bg_side}; border: 1px solid {thm.border}; border-radius: 8px; outline: none; color: {thm.text_main}; }}
            QListWidget::item {{ height: {cfg.row_height + 4}px; padding-left: 10px; margin: 2px 5px; border-radius: 6px; }}
            QListWidget::item:selected {{
                background-color: {thm.bg_input if self.current_theme_name == "浅色 (Light)" else "#3a3a3c"};
                color: {thm.text_main}; border: 1px solid {thm.primary}; border-left: 5px solid {thm.primary};
            }}
            
            QSplitter::handle {{ background-color: {thm.border}; }}
        """
        self.main_frame.setStyleSheet(css)
        self.left_widget.setStyleSheet(f"background-color: {thm.bg_side}; border-bottom-left-radius: 12px;")
        self.right_widget.setStyleSheet(f"background-color: {thm.bg_main}; border-bottom-right-radius: 12px;")
        
        self.left_layout.setSpacing(cfg.spacing); self.right_layout.setSpacing(cfg.spacing)
        self.form_basic.setSpacing(cfg.spacing); self.form_basic.setVerticalSpacing(cfg.spacing)
        
        for btn in self.findChildren(AppleButton): btn.set_theme_scale(thm, cfg)
        for well in self.findChildren(AppleColorWell): well.set_theme_scale(thm, cfg)
        for sw in self.findChildren(IOSSwitch): sw.set_theme_scale(thm, cfg)
        if "Large" in self.current_scale_name and self.width() < 1200: self.resize(1250, 850)

    def load_button_list(self):
        current_row = self.button_list.currentRow()
        self.button_list.clear()
        if not self.configs.get('buttons'): self.configs['buttons'] = []
        for config in self.configs['buttons']: self.button_list.addItem(f"{config['label']}")
        if self.button_list.count() > 0:
            row = current_row if (current_row >= 0 and current_row < self.button_list.count()) else 0
            self.button_list.setCurrentRow(row)

    def select_button(self, item, previous=None):
        if not item: return
        index = self.button_list.row(item)
        if index < 0 or index >= len(self.configs['buttons']): return
        self.current_id = self.configs['buttons'][index]['id']
        self.load_config_to_ui(self.configs['buttons'][index])

    def load_config_to_ui(self, config):
        self.block_signals_custom(True)
        self.label_edit.setText(config.get('label', ''))
        font = config.get('fontFamily', '微软雅黑')
        idx = self.font_combo.findText(font)
        if idx >= 0: self.font_combo.setCurrentIndex(idx)
        else: self.font_combo.addItem(font); self.font_combo.setCurrentText(font)
        self.shortcut_edit.setText(config.get('shortcut', ''))
        self.color_bg.setText(config.get('color', '#ffffff'))
        self.color_text.setText(config.get('textColor', '#000000'))
        self.color_border.setText(config.get('borderColor', '#cccccc'))
        self.spin_opacity.setValue(config.get('opacity', 1.0))
        self.spin_size.setValue(config.get('fontSize', 14))
        pos = config.get('position', [0, 0]); self.spin_x.setValue(pos[0]); self.spin_y.setValue(pos[1])
        size = config.get('size', [100, 50]); self.spin_w.setValue(size[0]); self.spin_h.setValue(size[1])
        locked = config.get('position_lock', False); self.chk_lock.setChecked(locked); self.on_position_lock_changed(locked)
        self.block_signals_custom(False)

    def block_signals_custom(self, block):
        for w in [self.label_edit, self.font_combo, self.shortcut_edit, self.color_bg, self.color_text, self.color_border, self.spin_opacity, self.spin_size, self.spin_x, self.spin_y, self.spin_w, self.spin_h, self.chk_lock]: w.blockSignals(block)

    def sync_current_data(self):
        if not self.current_id: return
        index = next((i for i, b in enumerate(self.configs['buttons']) if b['id'] == self.current_id), None)
        if index is not None:
            self.configs['buttons'][index].update({
                "label": self.label_edit.text(), "fontFamily": self.font_combo.currentText(), "shortcut": self.shortcut_edit.text(),
                "color": self.color_bg.text(), "textColor": self.color_text.text(), "borderColor": self.color_border.text(),
                "opacity": self.spin_opacity.value(), "fontSize": self.spin_size.value(),
                "position": [self.spin_x.value(), self.spin_y.value()], "size": [self.spin_w.value(), self.spin_h.value()],
                "position_lock": self.chk_lock.isChecked()
            })
            item = self.button_list.item(index)
            if item: item.setText(self.label_edit.text())

    def on_shortcut_changed(self, text):
        if self.shortcut_timer: self.shortcut_timer.stop()
        self.shortcut_timer = QTimer(); self.shortcut_timer.setSingleShot(True)
        self.shortcut_timer.timeout.connect(lambda: self.sync_current_data()); self.shortcut_timer.start(500)

    def toggle_key_detection(self, checked):
        if checked:
            self.shortcut_edit.clearFocus(); self.shortcut_edit.setPlaceholderText("按下按键...")
            self.shortcut_edit.clear(); self.btn_record.setText("停止")
        else:
            self.shortcut_edit.setPlaceholderText("Ctrl+C"); self.btn_record.setText("录制")

    def keyPressEvent(self, event):
        if self.btn_record.isChecked():
            key = event.key()
            if key in (Qt.Key_Escape,): self.btn_record.setChecked(False); self.toggle_key_detection(False); return
            from PyQt5.QtGui import QKeySequence
            if key not in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
                seq = QKeySequence(event.modifiers() | key); self.shortcut_edit.setText(seq.toString().lower())
                self.sync_current_data(); self.btn_record.setChecked(False); self.toggle_key_detection(False)
            return
        super().keyPressEvent(event)

    def on_position_lock_changed(self, state):
        locked = (state == Qt.Checked) if isinstance(state, int) else state
        self.spin_x.setEnabled(not locked); self.spin_y.setEnabled(not locked)

    def load_config_list(self):
        self.config_combo.blockSignals(True); self.config_combo.clear()
        if not os.path.exists(self.config_dir): os.makedirs(self.config_dir)
        files = [f for f in os.listdir(self.config_dir) if f.endswith('.json') and f != 'preferences.json']
        if not files: files = ['default.json']
        self.config_combo.addItems(files)
        idx = self.config_combo.findText(self.current_filename); 
        if idx >= 0: self.config_combo.setCurrentIndex(idx)
        self.config_combo.blockSignals(False)

    def on_config_changed(self, filename):
        if not filename: return
        path = os.path.join(self.config_dir, filename)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: self.configs = json.load(f)
                self.current_filename = filename; self.current_id = None; self.load_button_list()
            except: pass

    def create_config(self):
        name, ok = QInputDialog.getText(self, "新建", "文件名:")
        if ok and name:
            fname = name if name.endswith('.json') else f"{name}.json"
            with open(os.path.join(self.config_dir, fname), 'w') as f: json.dump({"buttons": []}, f)
            self.load_config_list(); self.config_combo.setCurrentText(fname)

    def delete_config(self):
        if self.config_combo.count() <= 1: return
        fname = self.config_combo.currentText()
        if QMessageBox.question(self, "删除", f"删除 {fname}?") == QMessageBox.Yes:
            os.remove(os.path.join(self.config_dir, fname))
            self.load_config_list(); self.on_config_changed(self.config_combo.currentText())

    def create_new_button(self):
        new_btn = {
            "id": str(uuid.uuid4()), "label": "新按钮", "position": [100, 100], "size": [120, 60],
            "color": "#0A84FF", "textColor": "#ffffff", "borderColor": "#0071e3", "opacity": 0.9, "fontSize": 14,
            "position_lock": False, "fontFamily": "Microsoft YaHei UI"
        }
        self.configs['buttons'].append(new_btn); self.load_button_list(); self.button_list.setCurrentRow(len(self.configs['buttons'])-1)

    def copy_button(self):
        if not self.current_id: return
        idx = next((i for i, b in enumerate(self.configs['buttons']) if b['id'] == self.current_id), None)
        if idx is not None:
            new_btn = copy.deepcopy(self.configs['buttons'][idx]); new_btn['id'] = str(uuid.uuid4()); new_btn['label'] += " 副本"
            new_btn['position'][0] += 20; new_btn['position'][1] += 20
            self.configs['buttons'].append(new_btn); self.load_button_list(); self.button_list.setCurrentRow(len(self.configs['buttons'])-1)

    def delete_button(self):
        if not self.current_id: return
        idx = next((i for i, b in enumerate(self.configs['buttons']) if b['id'] == self.current_id), None)
        if idx is not None:
            if QMessageBox.question(self, "删除", "确认删除?") == QMessageBox.Yes:
                del self.configs['buttons'][idx]; self.current_id = None; self.load_button_list()

    def apply_font_to_all(self):
        font = self.font_combo.currentText()
        for b in self.configs['buttons']: b['fontFamily'] = font
        self.sync_current_data(); QMessageBox.information(self, "成功", "已应用")

    def on_refresh(self):
        if self.apply_callback: self.apply_callback(self.configs)

    def get_values(self): return self.current_filename, self.configs