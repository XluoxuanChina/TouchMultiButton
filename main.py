import sys,os
import json
import keyboard
import shutil
import copy
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer
from button import DraggableButton
from settings_window import SettingsDialog

class TouchButtonApp:
    def __init__(self):
        # 创建Qt应用实例
        self.app = QApplication(sys.argv)
        # 设置关闭最后一个窗口时不退出程序
        self.app.setQuitOnLastWindowClosed(False)
        
        # 确定基础路径
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            
        # 配置目录初始化
        self.config_dir = os.path.join(self.base_dir, 'config')
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            
        # 迁移旧配置（如果存在）
        old_config_path = os.path.join(self.base_dir, 'config.json')
        if os.path.exists(old_config_path):
            if not os.listdir(self.config_dir):
                shutil.move(old_config_path, os.path.join(self.config_dir, 'default.json'))
            else:
                # 如果config目录已有文件，则重命名备份旧文件
                shutil.move(old_config_path, os.path.join(self.config_dir, 'old_config_backup.json'))

        self.prefs_file = os.path.join(self.config_dir, 'preferences.json')
        self.current_config_file = self.get_last_config_file()
        self.buttons = []
        
        # 加载配置
        self.load_config()
        
        # 创建系统托盘图标 (需要在加载配置之后，以便菜单可能需要状态)
        self.tray = self.create_tray_icon()

    def get_last_config_file(self):
        if os.path.exists(self.prefs_file):
            try:
                with open(self.prefs_file, 'r') as f:
                    data = json.load(f)
                    last = data.get('last_config')
                    if last and os.path.exists(os.path.join(self.config_dir, last)):
                        return last
            except:
                pass
        return 'default.json'

    def save_prefs(self):
        try:
            with open(self.prefs_file, 'w') as f:
                json.dump({'last_config': self.current_config_file}, f)
        except Exception as e:
            print(f"Failed to save prefs: {e}")

    def create_tray_icon(self):
        # 创建系统托盘图标实例
        tray = QSystemTrayIcon()
        
        if getattr(sys, 'frozen', False):
            res_path = sys._MEIPASS
        else:
            res_path = self.base_dir
            
        icon_path = os.path.join(res_path, "TouchMultiButton.ico")
        tray.setIcon(QIcon(icon_path))

        # 创建右键菜单
        menu = QMenu()
        
        # === 配置文件切换菜单 ===
        self.config_menu = menu.addMenu("切换配置")
        self.update_config_menu()
        self.config_menu.aboutToShow.connect(self.update_config_menu)
        
        menu.addSeparator()
        
        # 添加"管理按钮"菜单项
        menu.addAction("管理按钮").triggered.connect(self.show_settings)
        
        # 添加"锁定所有位置"菜单项
        self.lock_action = menu.addAction("锁定所有位置")
        self.lock_action.setCheckable(True)
        # 初始化选中状态
        if self.buttons and self.buttons[0].config.get('position_lock', False):
            self.lock_action.setChecked(True)
        self.lock_action.triggered.connect(self.toggle_all_locks)
        
        # 添加分隔线
        menu.addSeparator()
        # 添加"退出"菜单项
        menu.addAction("退出").triggered.connect(self.clean_exit)
        # 设置托盘的上下文菜单
        tray.setContextMenu(menu)
        # 显示托盘图标
        tray.show()
        return tray

    def update_config_menu(self):
        """更新配置切换菜单的内容"""
        self.config_menu.clear()
        
        # 获取所有json文件，排除preferences.json
        files = [f for f in os.listdir(self.config_dir) if f.endswith('.json') and f != 'preferences.json']
        if not files:
            files = ['default.json']
            
        for f in files:
            action = self.config_menu.addAction(f)
            action.setCheckable(True)
            action.setChecked(f == self.current_config_file)
            # 使用闭包绑定文件名
            action.triggered.connect(lambda checked, fname=f: self.switch_config(fname))
            
        self.config_menu.addSeparator()
        new_action = self.config_menu.addAction("新建配置...")
        new_action.triggered.connect(self.create_new_config)

    def switch_config(self, filename):
        if filename == self.current_config_file:
            return
            
        print(f"Switching to config: {filename}")
        self.current_config_file = filename
        self.save_prefs()
        self.load_config(filename)
        # 更新托盘菜单选中状态（如果菜单是打开的）
        
    def create_new_config(self):
        # 简单实现：创建一个基于当前时间戳或递增的新配置
        import time
        new_name = f"config_{int(time.time())}.json"
        
        # 创建一个空配置
        new_path = os.path.join(self.config_dir, new_name)
        with open(new_path, 'w') as f:
            json.dump({"buttons": []}, f, indent=2)
            
        self.switch_config(new_name)
        self.tray.showMessage("TouchButton", f"已创建并切换到新配置: {new_name}", QSystemTrayIcon.Information, 2000)
        self.show_settings() # 自动打开设置以便编辑

    def toggle_all_locks(self):
        is_locked = self.lock_action.isChecked()
        for btn in self.buttons:
            btn.config['position_lock'] = is_locked
        
        # 同步更新配置
        for btn_cfg in self.config['buttons']:
            btn_cfg['position_lock'] = is_locked
            
        self.save_config()
        # msg = "所有按钮已锁定" if is_locked else "所有按钮已解锁"
        self.tray.showMessage("TouchButton", msg, QSystemTrayIcon.Information, 2000)

    def load_config(self, filename=None):
        if filename:
            self.current_config_file = filename
            
        config_path = os.path.join(self.config_dir, self.current_config_file)
        
        try:
            # 如果配置文件不存在则创建默认配置
            if not os.path.exists(config_path):
                self.config = {"buttons": []}
                self.save_config()
            else:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            
            self.create_buttons()
            
            # 更新锁定状态菜单
            if hasattr(self, 'lock_action') and self.config['buttons']:
                # 取第一个按钮的状态作为整体状态
                locked = self.config['buttons'][0].get('position_lock', False)
                self.lock_action.setChecked(locked)
                
        except Exception as e:
            print(f"加载配置失败: {e}")
            self.config = {"buttons": []}
            self.create_buttons()

    def create_buttons(self):
        # 清除现有按钮
        for btn in self.buttons:
            btn.deleteLater()  # 删除按钮控件
        self.buttons.clear()   # 清空按钮列表

        # 根据配置创建新按钮
        for btn_cfg in self.config['buttons']:
            self.create_single_button(btn_cfg)

    def create_single_button(self, config):
        # 创建可拖动按钮实例
        button = DraggableButton(config)
        # 绑定点击事件：使用闭包保存当前配置，触发快捷键
        button.clicked.connect(lambda _, c=config: self.trigger_shortcut(c['shortcut']))
        # 绑定位置变更事件
        button.positionChanged.connect(self.handle_position_change)
        # 显示按钮
        button.show()
        # 添加到按钮列表
        self.buttons.append(button)

    def handle_position_change(self, new_config):
        # 查找对应按钮的索引
        try:
            index = next(i for i, btn in enumerate(self.buttons)
                         if btn.config['id'] == new_config['id'])
            # 更新按钮配置
            self.buttons[index].config = new_config
            # 同步更新主配置对象中的数据
            # 注意：self.config['buttons'] 和 self.buttons[i].config 引用的是否是同一个对象？
            # DraggableButton 初始化时只是引用了传入的 dict。
            # 如果 DraggableButton 内部修改了 config (确实如此)，那么 self.config['buttons'] 里的引用也会变
            # 只要 load_config 时我们是直接传的引用。
            
            # 延迟100毫秒后保存配置（防频繁保存）
            QTimer.singleShot(100, self.save_config)
        except StopIteration:
            pass

    def trigger_shortcut(self, shortcut):
        if not shortcut: return
        try:
            # 模拟按下并释放快捷键
            keyboard.press(shortcut)
            keyboard.release(shortcut)
        except ValueError:
            # 处理无效快捷键错误
            print(f"无效的快捷键: {shortcut}")
        except Exception as e:
            print(f"快捷键执行错误: {e}")

    def apply_live_settings(self, new_config):
        # 仅更新内存中的配置并刷新按钮显示，不保存到磁盘
        self.config = copy.deepcopy(new_config)
        self.create_buttons()

    def show_settings(self):
        # 保存原始状态以便取消时恢复
        original_config = copy.deepcopy(self.config)
        original_filename = self.current_config_file
        
        # 创建设置对话框
        dialog = SettingsDialog(self.config_dir, self.current_config_file, self.config, apply_callback=self.apply_live_settings)
        if dialog.exec_():
            # 如果对话框确认提交，更新配置
            new_filename, new_config = dialog.get_values()
            
            self.current_config_file = new_filename
            self.config = new_config
            
            # 保存新配置
            self.save_config()
            self.save_prefs()
            
            # 重建所有按钮
            self.create_buttons()
        else:
            # 取消更改：恢复原始配置
            self.current_config_file = original_filename
            self.config = original_config
            self.create_buttons()

    def save_config(self):
        config_path = os.path.join(self.config_dir, self.current_config_file)
        try:
            # 确保数据最新
            self.config['buttons'] = [btn.config for btn in self.buttons]
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")


    def clean_exit(self):
        # 退出前保存配置
        self.save_config()
        # 删除所有按钮控件
        for btn in self.buttons:
            btn.deleteLater()
        # 退出应用
        self.app.quit()

    def run(self):
        # 启动应用主循环
        sys.exit(self.app.exec_())

if __name__ == "__main__":
    # 创建应用实例并运行
    app = TouchButtonApp()
    app.run()
