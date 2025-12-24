from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QTimer
import sys
import ctypes
from ctypes import wintypes
from PyQt5.QtGui import QColor

class DraggableButton(QPushButton):
    # 自定义信号：当位置改变时触发，携带配置字典
    positionChanged = pyqtSignal(dict)
    # 自定义信号：当按钮被点击时触发，传递按钮ID
    clicked = pyqtSignal(str)

    def __init__(self, config, parent=None):
        super().__init__(config['label'], parent)  # 初始化父类并设置按钮文字
        self.config = config  # 保存配置信息
        self.m_drag = False  # 拖拽状态标志
        self.drag_start_pos = QPoint()  # 记录拖拽起始位置
        self.setup_style()  # 初始化样式
        if sys.platform == "win32":
            self.setup_win32_properties()
        else:
            print("Not Windows Platform")

    def setup_win32_properties(self):
        """Windows系统窗口特性设置"""
        # 获取窗口句柄并转换为ctypes兼容格式
        hwnd = int(self.winId())  # 关键修改：转换为整型

        # 设置API参数类型声明
        ctypes.windll.user32.GetWindowLongW.argtypes = [
            wintypes.HWND,
            ctypes.c_int
        ]

        # 获取当前扩展样式
        ex_style = ctypes.windll.user32.GetWindowLongW(
            hwnd,
            -20  # GWL_EXSTYLE
        )

        # 设置新样式
        ctypes.windll.user32.SetWindowLongW(
            hwnd,
            -20,  # GWL_EXSTYLE
            ex_style | 0x08000000  # WS_EX_NOACTIVATE
        )


    def mousePressEvent(self, event):
        """鼠标按下事件处理"""
        self.setFocusPolicy(Qt.NoFocus)  # 禁止按钮获取焦点
        self.drag_start_global = event.globalPos()  # 全局坐标记录
        self.drag_start_pos = event.pos()  # 记录点击位置（相对于组件）
        if event.button() == Qt.LeftButton:
            self.m_drag = True  # 标记开始拖拽
            # 计算鼠标全局位置与组件位置的偏移量
            self.drag_offset = event.globalPos() - self.pos()
        super().mousePressEvent(event)  # 调用父类处理

    def mouseMoveEvent(self, event):
        """鼠标移动事件处理"""
        self.setFocusPolicy(Qt.NoFocus)  # 禁止按钮获取焦点
        if self.m_drag and (self.config['position_lock'] == False):  # 锁定状态检查（当锁定时拒绝更新位置）
            # 计算新的位置（全局坐标减去偏移量）
            new_pos = event.globalPos() - self.drag_offset
            # 应用位置限制（防止移出屏幕）
            new_pos = self._clamp_position(new_pos)
            self.move(new_pos)  # 移动组件到新位置
            # 更新配置中的位置信息（使用列表格式存储x,y）
            self.config['position'] = [new_pos.x(), new_pos.y()]
            self.positionChanged.emit(self.config)  # 发射位置改变信号
        super().mouseMoveEvent(event)  # 调用父类处理

    def _clamp_position(self, pos):
        """限制按钮位置在屏幕范围内"""
        screen_rect = self.screen().availableGeometry()  # 获取屏幕可用区域
        return QPoint(
            # 限制X坐标在0到（屏幕宽度 - 按钮宽度）之间
            max(0, min(pos.x(), screen_rect.width() - self.width())),
            # 限制Y坐标在0到（屏幕高度 - 按钮高度）之间
            max(0, min(pos.y(), screen_rect.height() - self.height()))
        )

    def mouseReleaseEvent(self, event):
        """鼠标释放事件处理"""
        self.setFocusPolicy(Qt.NoFocus)  # 禁止按钮获取焦点
        # 如果移动距离小于5像素视为点击事件（使用曼哈顿距离）
        if (event.globalPos() - self.drag_start_global).manhattanLength() < 2:
            self.clicked.emit(self.config['id'])  # 发射点击信号并传递ID
        self.m_drag = False  # 重置拖拽状态
        super().mouseReleaseEvent(event)

    def update_style(self):
        """更新按钮样式（根据配置中的透明度）"""
        # 从配置获取颜色
        qcolor = QColor(self.config['color'])
        r = qcolor.red()
        g = qcolor.green()
        b = qcolor.blue()
        qcolor = QColor(self.config['textColor'])
        tr = qcolor.red()
        tg = qcolor.green()
        tb = qcolor.blue()
        qcolor = QColor(self.config['borderColor'])
        br = qcolor.red()
        bg = qcolor.green()
        bb = qcolor.blue()
        
        # 获取字体，确保向后兼容性
        font_family = self.config.get('fontFamily', '微软雅黑')
        # 如果字体为空，使用默认字体
        if not font_family or not font_family.strip():
            font_family = '微软雅黑'

        self.setFocusPolicy(Qt.NoFocus)  # 禁止按钮获取焦点
        self.setStyleSheet(f"""
            background-color: rgba({r}, {g}, {b}, {self.config['opacity']});
            color: rgba({tr}, {tg}, {tb});
            border-radius: 10px;        /* 圆角半径 */
            font-family: "{font_family}";
            font-size: {self.config['fontSize']}px;            /* 字体大小 */
            border: 2px solid rgba({br}, {bg}, {bb}, {self.config['opacity']}); /* 边框 */
        """)

    def setup_style(self):
        # 关键窗口标志组合
        self.setWindowFlags(
            Qt.FramelessWindowHint |  # 无边框
            Qt.WindowStaysOnTopHint |  # 置顶
            #Qt.Tool |  # 隐藏任务栏入口
            Qt.WindowDoesNotAcceptFocus  # 不接受焦点
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)  # 显示不激活
        self.setFocusPolicy(Qt.NoFocus)
        self.setGeometry(*self.config['position'], *self.config['size'])
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.update_style()
        self.show()

