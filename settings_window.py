from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLineEdit, QSpinBox, QDoubleSpinBox,
    QListWidget, QPushButton, QMessageBox, QCheckBox,
    QColorDialog, QGroupBox, QLabel, QFrame, QSplitter,
    QComboBox, QInputDialog
)
from PyQt5.QtGui import QIcon, QKeySequence, QColor, QKeyEvent
from PyQt5.QtCore import Qt, QTimer
import uuid
import os, sys
import json
import copy

class ColorEdit(QPushButton):
    """颜色选择控件"""
    def __init__(self, color="#ffffff", parent=None):
        super().__init__(parent)
        self.color = color
        self.setText(color)
        self.clicked.connect(self.choose_color)
        self.update_style()
        self.setCursor(Qt.PointingHandCursor)

    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.color), self, "选择颜色")
        if color.isValid():
            self.color = color.name()
            self.setText(self.color)
            self.update_style()
            # 触发改变信号（虽然QPushButton没有textChanged，但在sync中我们会读取text）

    def update_style(self):
        bg = QColor(self.color)
        fg = "black" if bg.lightness() > 128 else "white"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color}; 
                color: {fg}; 
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                font-family: Consolas, monospace;
            }}
            QPushButton:hover {{
                border: 1px solid #999;
            }}
        """)

    def text(self):
        return self.color

    def setText(self, text):
        self.color = text
        super().setText(text)
        self.update_style()



class SettingsDialog(QDialog):
    def __init__(self, config_dir, current_filename, configs, apply_callback=None, parent=None):
        super().__init__(parent)
        self.config_dir = config_dir
        self.current_filename = current_filename
        # 深拷贝配置，确保“取消”时不会影响原数据
        self.configs = copy.deepcopy(configs)
        self.apply_callback = apply_callback
        self.current_id = None
        
        self.setup_ui()
        self.load_button_list()
        
        # 图标设置
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_path, "TouchMultiButton.ico")
        self.setWindowIcon(QIcon(icon_path))
        
        # 初始选中第一个
        if self.configs['buttons']:
            self.button_list.setCurrentRow(0)

    def setup_ui(self):
        self.setWindowTitle("按钮配置管理")
        self.setMinimumSize(800, 700)
        self.resize(900, 600)
        
        # 应用全局样式
        self.setStyleSheet("""
            QDialog { background-color: #f0f0f0; }
            QListWidget { 
                border: 1px solid #ccc; 
                border-radius: 4px;
                background-color: white;
                outline: none;
            }
            QListWidget::item { 
                padding: 8px; 
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected { 
                background-color: #3daee9; 
                color: white; 
            }
            QLabel { color: #333; }
            QGroupBox { 
                border: 1px solid #ccc; 
                border-radius: 6px; 
                margin-top: 10px; 
                background-color: white;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px; 
                color: #555;
                font-weight: bold;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                background-color: #e0e0e0;
                border: 1px solid #ccc;
            }
            QPushButton:hover { background-color: #d0d0d0; }
            QPushButton:pressed { background-color: #c0c0c0; }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # === 左侧面板 ===
        left_panel = QVBoxLayout()
        
        # 配置文件管理
        config_group = QGroupBox("配置文件")
        config_layout = QVBoxLayout()
        
        self.config_combo = QComboBox()
        # 暂时断开连接以防初始化触发
        self.config_combo.blockSignals(True)
        self.load_config_list()
        self.config_combo.blockSignals(False)
        self.config_combo.currentTextChanged.connect(self.on_config_changed)
        config_layout.addWidget(self.config_combo)
        
        cfg_btn_layout = QHBoxLayout()
        self.new_cfg_btn = QPushButton("新建")
        self.new_cfg_btn.clicked.connect(self.create_config)
        self.copy_cfg_btn = QPushButton("复制")
        self.copy_cfg_btn.clicked.connect(self.copy_config)
        self.del_cfg_btn = QPushButton("删除")
        self.del_cfg_btn.clicked.connect(self.delete_config)
        cfg_btn_layout.addWidget(self.new_cfg_btn)
        cfg_btn_layout.addWidget(self.copy_cfg_btn)
        cfg_btn_layout.addWidget(self.del_cfg_btn)
        config_layout.addLayout(cfg_btn_layout)
        
        config_group.setLayout(config_layout)
        left_panel.addWidget(config_group)
        
        # 按钮列表
        list_label = QLabel("按钮列表")
        list_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_panel.addWidget(list_label)
        
        self.button_list = QListWidget()
        self.button_list.currentItemChanged.connect(self.select_button)
        left_panel.addWidget(self.button_list)

        # 操作按钮组
        btn_group = QHBoxLayout()
        self.new_btn = QPushButton("新建")
        self.new_btn.clicked.connect(self.create_new_button)
        self.new_btn.setStyleSheet("background-color: #4CAF50; color: white; border: none;")
        
        self.copy_btn = QPushButton("复制")
        self.copy_btn.clicked.connect(self.copy_button)
        self.copy_btn.setStyleSheet("background-color: #2196F3; color: white; border: none;")
        
        self.del_btn = QPushButton("删除")
        self.del_btn.clicked.connect(self.delete_button)
        self.del_btn.setStyleSheet("background-color: #f44336; color: white; border: none;")
        
        btn_group.addWidget(self.new_btn)
        btn_group.addWidget(self.copy_btn)
        btn_group.addWidget(self.del_btn)
        left_panel.addLayout(btn_group)
        
        # === 右侧面板 ===
        right_panel = QVBoxLayout()
        
        # 基本属性组
        basic_group = QGroupBox("基本属性")
        basic_layout = QFormLayout()
        basic_layout.setSpacing(10)
        
        self.label = QLineEdit()
        self.label.textChanged.connect(self.sync_current_data)
        
        self.fontFamily = QComboBox()
        self.fontFamily.setEditable(True)
        # 获取系统字体列表
        from PyQt5.QtGui import QFontDatabase
        font_db = QFontDatabase()
        font_families = font_db.families()
        self.fontFamily.addItems(font_families)
        self.fontFamily.currentTextChanged.connect(self.sync_current_data)
        
        # 快捷键行（包含文本框和"按键检测"按钮）
        shortcut_layout = QHBoxLayout()
        self.shortcut = QLineEdit()
        self.shortcut.setPlaceholderText("直接输入快捷键 (如: ctrl+a) 或点击按键检测录制")
        # 使用 textChanged 信号实时同步，但设置一个防抖机制
        self.shortcut.textChanged.connect(self.on_shortcut_changed)
        
        self.key_detect_btn = QPushButton("按键检测")
        self.key_detect_btn.setCheckable(True)  # 设置为可切换按钮
        self.key_detect_btn.clicked.connect(self.toggle_key_detection)
        self.key_detect_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 8px;
                font-size: 12px;
                background-color: #e0e0e0;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QPushButton:checked {
                background-color: #2196F3;
                color: white;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:checked:hover {
                background-color: #1976D2;
            }
        """)
        shortcut_layout.addWidget(self.shortcut)
        shortcut_layout.addWidget(self.key_detect_btn)
        
        self.position_lock = QCheckBox("锁定位置")
        self.position_lock.stateChanged.connect(self.on_position_lock_changed)
        self.position_lock.stateChanged.connect(self.sync_current_data)

        basic_layout.addRow("按钮文字:", self.label)
        
        # 字体选择行（包含下拉框和"应用到全部"按钮）
        font_layout = QHBoxLayout()
        font_layout.addWidget(self.fontFamily)
        self.apply_font_to_all_btn = QPushButton("应用到全部")
        self.apply_font_to_all_btn.clicked.connect(self.apply_font_to_all)
        self.apply_font_to_all_btn.setStyleSheet("padding: 4px 8px; font-size: 12px;")
        font_layout.addWidget(self.apply_font_to_all_btn)
        basic_layout.addRow("文字字体:", font_layout)
        
        basic_layout.addRow("快捷键:", shortcut_layout)
        basic_layout.addRow("", self.position_lock)
        basic_group.setLayout(basic_layout)
        
        # 外观样式组
        style_group = QGroupBox("外观样式")
        style_layout = QFormLayout()
        
        self.color = ColorEdit()
        self.color.clicked.connect(self.sync_current_data) # ColorEdit update triggers clicked? No, need to handle text change
        # ColorEdit doesn't emit textChanged, but we can hook into setText or just use clicked to sync
        # Actually, choose_color updates internal state. We can override choose_color to call sync.
        # Simpler: connect clicked to a wrapper that waits or just rely on the fact that dialog is modal
        # Wait, ColorEdit.choose_color is blocking. After it returns, we can sync.
        # Let's modify ColorEdit connection below.
        
        self.textColor = ColorEdit()
        self.borderColor = ColorEdit()
        
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0.1, 1.0)
        self.opacity.setSingleStep(0.1)
        self.opacity.valueChanged.connect(self.sync_current_data)
        
        self.fontSize = QSpinBox()
        self.fontSize.setRange(8, 200)
        self.fontSize.valueChanged.connect(self.sync_current_data)
        
        style_layout.addRow("背景颜色:", self.color)
        style_layout.addRow("字体颜色:", self.textColor)
        style_layout.addRow("边框颜色:", self.borderColor)
        style_layout.addRow("透明度:", self.opacity)
        style_layout.addRow("字体大小:", self.fontSize)
        style_group.setLayout(style_layout)
        
        # 布局尺寸组
        layout_group = QGroupBox("布局尺寸")
        layout_grid = QFormLayout()
        
        self.position_x = QSpinBox()
        self.position_x.setRange(0, 3840)
        self.position_x.setSuffix(" px")
        self.position_x.valueChanged.connect(self.sync_current_data)
        
        self.position_y = QSpinBox()
        self.position_y.setRange(0, 2160)
        self.position_y.setSuffix(" px")
        self.position_y.valueChanged.connect(self.sync_current_data)
        
        self.size_w = QSpinBox()
        self.size_w.setRange(20, 1000)
        self.size_w.setSuffix(" px")
        self.size_w.valueChanged.connect(self.sync_current_data)
        
        self.size_h = QSpinBox()
        self.size_h.setRange(20, 1000)
        self.size_h.setSuffix(" px")
        self.size_h.valueChanged.connect(self.sync_current_data)
        
        layout_grid.addRow("X 坐标:", self.position_x)
        layout_grid.addRow("Y 坐标:", self.position_y)
        layout_grid.addRow("宽度:", self.size_w)
        layout_grid.addRow("高度:", self.size_h)
        layout_group.setLayout(layout_grid)

        # 操作按钮组（放在布局尺寸下方）
        action_group = QGroupBox("操作")
        action_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新按钮状态")
        self.refresh_btn.clicked.connect(self.on_refresh)
        self.refresh_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 6px 12px;")
        
        self.save_btn = QPushButton("保存按钮配置")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 6px 12px;")
        
        self.cancel_btn = QPushButton("取消更改并退出")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("padding: 6px 12px;")
        
        action_layout.addWidget(self.refresh_btn)
        action_layout.addStretch()
        action_layout.addWidget(self.save_btn)
        action_layout.addWidget(self.cancel_btn)
        action_group.setLayout(action_layout)
        
        # 添加到右侧
        right_panel.addWidget(basic_group)
        right_panel.addWidget(style_group)
        right_panel.addWidget(layout_group)
        right_panel.addWidget(action_group)
        right_panel.addStretch()
        
        # 布局组合
        splitter = QSplitter(Qt.Horizontal)
        left_widget = QFrame()
        left_widget.setLayout(left_panel)
        right_widget = QFrame()
        right_widget.setLayout(right_panel)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        
        # 特殊处理 ColorEdit 的同步 (因为没有 textChanged 信号)
        # 我们修改 ColorEdit 使其在改变后发射信号，或者这里我们 monkey patch
        self.color.clicked.connect(lambda: self.sync_current_data())
        self.textColor.clicked.connect(lambda: self.sync_current_data())
        self.borderColor.clicked.connect(lambda: self.sync_current_data())
        
        # 快捷键防抖定时器
        self.shortcut_timer = None

    def load_button_list(self):
        current_row = self.button_list.currentRow()
        self.button_list.clear()
        for config in self.configs['buttons']:
            self.button_list.addItem(f"{config['label']}")
        
        if current_row >= 0 and current_row < self.button_list.count():
            self.button_list.setCurrentRow(current_row)

    def select_button(self, item, previous=None):
        if not item: return
        index = self.button_list.row(item)
        if index < 0: return
        
        self.current_id = self.configs['buttons'][index]['id']
        self.load_config_to_ui(self.configs['buttons'][index])

    def load_config_to_ui(self, config):
        # 临时断开信号连接防止循环触发 sync (虽然 sync 是幂等的，但为了性能)
        self.block_signals(True)
        
        self.label.setText(config['label'])
        # 设置字体，确保向后兼容性（处理旧版本配置文件）
        font_family = config.get('fontFamily', '微软雅黑')
        # 如果字体列表中没有该字体，则添加到下拉框
        index = self.fontFamily.findText(font_family)
        if index >= 0:
            self.fontFamily.setCurrentIndex(index)
        else:
            # 如果字体不在列表中，添加并选中
            self.fontFamily.addItem(font_family)
            self.fontFamily.setCurrentText(font_family)
        self.shortcut.setText(config['shortcut'])
        self.color.setText(config['color'])
        self.textColor.setText(config['textColor'])
        self.borderColor.setText(config['borderColor'])
        self.fontSize.setValue(config['fontSize'])
        self.position_x.setValue(config['position'][0])
        self.position_y.setValue(config['position'][1])
        self.size_w.setValue(config['size'][0])
        self.size_h.setValue(config['size'][1])
        self.opacity.setValue(config['opacity'])
        self.position_lock.setChecked(config['position_lock'])
        
        # 确保按键检测按钮处于未选中状态
        self.key_detect_btn.setChecked(False)
        self.toggle_key_detection(False)
        
        self.on_position_lock_changed(config['position_lock'])
        
        self.block_signals(False)

    def on_shortcut_changed(self, text):
        """快捷键文本框内容变化时的防抖处理"""
        if self.shortcut_timer:
            self.shortcut_timer.stop()
        
        # 设置500ms防抖延迟
        self.shortcut_timer = QTimer()
        self.shortcut_timer.setSingleShot(True)
        self.shortcut_timer.timeout.connect(lambda: self.sync_current_data())
        self.shortcut_timer.start(500)

    def toggle_key_detection(self, checked):
        """切换按键检测模式"""
        if checked:
            # 进入按键检测模式
            self.shortcut.clearFocus()  # 文本框失去焦点
            self.shortcut.setPlaceholderText("按键检测模式已激活，请按下快捷键...")
            self.key_detect_btn.setText("停止检测")
            # 清空当前内容，准备录制
            self.shortcut.clear()
        else:
            # 退出按键检测模式
            self.shortcut.setPlaceholderText("直接输入快捷键 (如: ctrl+a) 或点击按键检测录制")
            self.key_detect_btn.setText("按键检测")

    def keyPressEvent(self, event):
        """全局按键事件处理"""
        if self.key_detect_btn.isChecked():
            # 只有在按键检测模式下才处理按键
            key = event.key()
            modifiers = event.modifiers()

            # 忽略修饰键单独按下
            if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
                return

            # ESC键退出检测模式
            if key == Qt.Key_Escape:
                self.key_detect_btn.setChecked(False)
                self.toggle_key_detection(False)
                return

            # 退格键清空内容
            if key in (Qt.Key_Backspace, Qt.Key_Delete):
                self.shortcut.clear()
                return

            # 构建快捷键字符串
            parts = []
            if modifiers & Qt.ControlModifier: parts.append("ctrl")
            if modifiers & Qt.ShiftModifier: parts.append("shift")
            if modifiers & Qt.AltModifier: parts.append("alt")
            if modifiers & Qt.MetaModifier: parts.append("windows")

            key_text = QKeySequence(key).toString().lower()
            if key_text:
                parts.append(key_text)

            if parts:
                self.shortcut.setText("+".join(parts))
                # 同步数据到配置
                self.sync_current_data()
                # 自动退出检测模式
                self.key_detect_btn.setChecked(False)
                self.toggle_key_detection(False)
            
            event.accept()
            return
            
        super().keyPressEvent(event)

    def block_signals(self, block):
        widgets = [
            self.label, self.fontFamily, self.shortcut, self.fontSize, 
            self.position_x, self.position_y, self.size_w, self.size_h, 
            self.opacity, self.position_lock
        ]
        for w in widgets:
            w.blockSignals(block)

    def sync_current_data(self):
        """实时将表单数据同步到内存配置中"""
        if not self.current_id:
            return
            
        index = next((i for i, btn in enumerate(self.configs['buttons'])
                      if btn['id'] == self.current_id), None)
        
        if index is not None:
            # 确保字体字段正确保存，即使为空字符串也要保存
            font_family = self.fontFamily.currentText().strip()
            if not font_family:
                font_family = "微软雅黑"  # 默认字体
                
            self.configs['buttons'][index].update({
                "label": self.label.text(),
                "fontFamily": font_family,
                "shortcut": self.shortcut.text(),
                "position": [self.position_x.value(), self.position_y.value()],
                "size": [self.size_w.value(), self.size_h.value()],
                "color": self.color.text(),
                "opacity": self.opacity.value(),
                "fontSize": self.fontSize.value(),
                "borderColor": self.borderColor.text(),
                "textColor": self.textColor.text(),
                'position_lock': self.position_lock.isChecked()
            })
            # 更新列表项显示（如果标题变了）
            item = self.button_list.item(index)
            if item:
                item.setText(self.label.text())

    def on_position_lock_changed(self, state):
        locked = (state == Qt.Checked) if isinstance(state, int) else state
        self.position_x.setEnabled(not locked)
        self.position_y.setEnabled(not locked)

    def create_new_button(self):
        new_config = {
            "id": str(uuid.uuid4()),
            "label": "新按钮",
            "fontFamily": "微软雅黑",
            "shortcut": "",
            "position": [200, 200],
            "size": [150, 100],
            "opacity": 0.8,
            "color": "#2196F3",
            "textColor": "#ffffff",
            "borderColor": "#1976D2",
            "fontSize": 20,
            'position_lock': False
        }
        self.configs['buttons'].append(new_config)
        self.load_button_list()
        self.button_list.setCurrentRow(len(self.configs['buttons']) - 1)

    def copy_button(self):
        """复制当前选中的按钮"""
        if not self.current_id:
            QMessageBox.information(self, "提示", "请先选择一个要复制的按钮")
            return
            
        # 找到当前选中的按钮索引
        current_index = next((i for i, btn in enumerate(self.configs['buttons'])
                             if btn['id'] == self.current_id), None)
        if current_index is None:
            return
            
        # 获取当前按钮配置
        current_button = self.configs['buttons'][current_index]
        
        # 创建新按钮配置（深拷贝）
        new_button = copy.deepcopy(current_button)
        
        # 生成新的唯一ID
        new_button['id'] = str(uuid.uuid4())
        
        # 修改标签名，添加"副本"后缀
        original_label = new_button['label']
        if not original_label.endswith('副本'):
            new_button['label'] = f"{original_label}副本"
        else:
            # 如果已经是副本，则添加数字后缀
            import re
            match = re.match(r'(.*副本)(\d*)$', original_label)
            if match:
                base_name = match.group(1)
                num_suffix = match.group(2)
                if num_suffix:
                    new_num = int(num_suffix) + 1
                    new_button['label'] = f"{base_name}{new_num}"
                else:
                    new_button['label'] = f"{base_name}2"
            else:
                new_button['label'] = f"{original_label}2"
        
        # 轻微偏移位置，避免完全重叠
        new_button['position'][0] += 20
        new_button['position'][1] += 20
        
        # 添加到按钮列表
        self.configs['buttons'].append(new_button)
        
        # 刷新列表并选中新按钮
        self.load_button_list()
        new_index = len(self.configs['buttons']) - 1
        self.button_list.setCurrentRow(new_index)
        
        QMessageBox.information(self, "复制成功", f"已成功复制按钮 '{original_label}'")

    def delete_button(self):
        if not self.current_id: return
        
        if len(self.configs['buttons']) <= 1:
            QMessageBox.warning(self, "警告", "必须至少保留一个按钮")
            return

        reply = QMessageBox.question(self, '确认删除', '确定要删除这个按钮吗？',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            index = next(i for i, btn in enumerate(self.configs['buttons'])
                         if btn['id'] == self.current_id)
            del self.configs['buttons'][index]
            self.current_id = None
            self.load_button_list()
            # 选中上一个
            new_index = min(index, len(self.configs['buttons']) - 1)
            self.button_list.setCurrentRow(new_index)

    def load_config_list(self):
        self.config_combo.blockSignals(True)
        self.config_combo.clear()
        files = [f for f in os.listdir(self.config_dir) if f.endswith('.json') and f != 'preferences.json']
        if not files:
            files = ['default.json']
        self.config_combo.addItems(files)
        
        index = self.config_combo.findText(self.current_filename)
        if index >= 0:
            self.config_combo.setCurrentIndex(index)
        self.config_combo.blockSignals(False)

    def on_config_changed(self, filename):
        if not filename or filename == self.current_filename:
            return
            
        path = os.path.join(self.config_dir, filename)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    new_configs = json.load(f)
                
                self.configs = new_configs
                self.current_filename = filename
                self.current_id = None
                self.load_button_list()
                if self.configs['buttons']:
                    self.button_list.setCurrentRow(0)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载配置文件失败: {e}")
                index = self.config_combo.findText(self.current_filename)
                self.config_combo.blockSignals(True)
                self.config_combo.setCurrentIndex(index)
                self.config_combo.blockSignals(False)

    def create_config(self):
        name, ok = QInputDialog.getText(self, "新建配置", "请输入配置文件名(不含.json):")
        if ok and name:
            filename = name if name.endswith('.json') else f"{name}.json"
            path = os.path.join(self.config_dir, filename)
            if os.path.exists(path):
                QMessageBox.warning(self, "错误", "文件已存在")
                return
            
            empty_config = {"buttons": []}
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(empty_config, f, indent=2)
                self.load_config_list()
                index = self.config_combo.findText(filename)
                if index >= 0:
                    self.config_combo.setCurrentIndex(index)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建文件失败: {e}")

    def copy_config(self):
        """复制当前配置文件"""
        current_filename = self.config_combo.currentText()
        if not current_filename:
            return
            
        # 获取新文件名
        name, ok = QInputDialog.getText(self, "复制配置", "请输入新配置文件名(不含.json):")
        if not ok or not name:
            return
            
        new_filename = name if name.endswith('.json') else f"{name}.json"
        new_path = os.path.join(self.config_dir, new_filename)
        
        # 检查文件是否已存在
        if os.path.exists(new_path):
            QMessageBox.warning(self, "错误", "文件已存在")
            return
            
        # 复制配置文件
        current_path = os.path.join(self.config_dir, current_filename)
        try:
            # 读取当前配置文件
            with open(current_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 写入新文件
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            # 更新配置文件列表
            self.load_config_list()
            
            # 切换到新文件
            index = self.config_combo.findText(new_filename)
            if index >= 0:
                self.config_combo.setCurrentIndex(index)
                
            QMessageBox.information(self, "复制成功", f"配置文件已成功复制为 {new_filename}")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"复制文件失败: {e}")

    def delete_config(self):
        if self.config_combo.count() <= 1:
            QMessageBox.warning(self, "警告", "至少保留一个配置文件")
            return
            
        filename = self.config_combo.currentText()
        reply = QMessageBox.question(self, "确认删除", f"确定要删除配置文件 {filename} 吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            path = os.path.join(self.config_dir, filename)
            try:
                os.remove(path)
                # 重新加载列表，并切换到第一个文件
                self.config_combo.blockSignals(True)
                self.config_combo.clear()
                files = [f for f in os.listdir(self.config_dir) if f.endswith('.json')]
                if not files:
                    # 极端情况：删完了
                    files = ['default.json']
                    with open(os.path.join(self.config_dir, 'default.json'), 'w') as f:
                        json.dump({"buttons": []}, f)
                        
                self.config_combo.addItems(files)
                self.config_combo.setCurrentIndex(0)
                self.config_combo.blockSignals(False)
                
                # 加载选中的文件
                self.on_config_changed(self.config_combo.currentText())
                
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除文件失败: {e}")

    def apply_font_to_all(self):
        """将当前选择的字体应用到所有按钮"""
        if not self.configs['buttons']:
            QMessageBox.information(self, "提示", "当前没有按钮配置")
            return
            
        current_font = self.fontFamily.currentText().strip()
        if not current_font:
            QMessageBox.warning(self, "警告", "请先选择一个字体")
            return
            
        reply = QMessageBox.question(self, "确认操作", 
                                   f"确定要将字体 '{current_font}' 应用到所有 {len(self.configs['buttons'])} 个按钮吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 更新所有按钮的字体
            for button in self.configs['buttons']:
                button['fontFamily'] = current_font
            
            # 如果当前有选中的按钮，刷新UI显示
            if self.current_id:
                index = next((i for i, btn in enumerate(self.configs['buttons']) 
                            if btn['id'] == self.current_id), None)
                if index is not None:
                    self.load_config_to_ui(self.configs['buttons'][index])
            
            QMessageBox.information(self, "操作完成", f"已成功将字体 '{current_font}' 应用到所有 {len(self.configs['buttons'])} 个按钮")

    def on_refresh(self):
        if self.apply_callback:
            self.apply_callback(self.configs)

    def get_values(self):
        return self.current_filename, self.configs

