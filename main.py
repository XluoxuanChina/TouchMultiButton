import sys, os
import json
import keyboard
import shutil
import copy
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import QTimer
from button import DraggableButton
from settings_window import SettingsDialog, THEMES

class TouchButtonApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # 应用全局样式表 (美化托盘菜单)
        self.apply_global_styles()

        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.config_dir = os.path.join(self.base_dir, 'config')
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            
        old_config_path = os.path.join(self.base_dir, 'config.json')
        if os.path.exists(old_config_path):
            if not os.listdir(self.config_dir):
                shutil.move(old_config_path, os.path.join(self.config_dir, 'default.json'))
            else:
                shutil.move(old_config_path, os.path.join(self.config_dir, 'old_config_backup.json'))

        self.prefs_file = os.path.join(self.config_dir, 'preferences.json')
        self.current_config_file = self.get_last_config_file()
        self.buttons = []
        
        self.load_config()
        self.tray = self.create_tray_icon()

    def apply_global_styles(self):
        # 使用深色主题作为托盘菜单的默认配色
        thm = THEMES["深色 (Dark)"]
        
        # 增加 font-size 到 16px，增加 padding-right 改善对齐
        css = f"""
            /* 全局菜单样式 (影响托盘菜单) */
            QMenu {{
                background-color: {thm.bg_main}; 
                border: 1px solid {thm.border};  
                border-radius: 10px;             
                padding: 8px;                    
                color: {thm.text_main};          
                font-family: "Microsoft YaHei UI";
                font-size: 16px; /* 字体加大 */
            }}
            
            /* 菜单项 */
            QMenu::item {{
                background-color: transparent;
                padding: 10px 30px;             /* 增加水平内边距，解决对齐拥挤问题 */
                border-radius: 6px;             
                margin: 2px 4px;                
            }}
            
            /* 鼠标悬停/选中状态 */
            QMenu::item:selected {{
                background-color: {thm.primary}; 
                color: white;
            }}
            
            /* 分割线 */
            QMenu::separator {{
                height: 1px;
                background: {thm.border};
                margin: 6px 12px;               
            }}
            
            /* 禁用的菜单项 */
            QMenu::item:disabled {{
                color: {thm.text_dim};
            }}
            
            QInputDialog {{ background-color: {thm.bg_main}; color: {thm.text_main}; }}
            QMessageBox {{ background-color: {thm.bg_main}; color: {thm.text_main}; }}
            QLabel {{ color: {thm.text_main}; }}
        """
        self.app.setStyleSheet(css)

    def get_last_config_file(self):
        if os.path.exists(self.prefs_file):
            try:
                with open(self.prefs_file, 'r') as f:
                    data = json.load(f)
                    last = data.get('last_config')
                    if last and os.path.exists(os.path.join(self.config_dir, last)):
                        return last
            except: pass
        return 'default.json'

    def save_prefs(self):
        try:
            with open(self.prefs_file, 'w') as f: json.dump({'last_config': self.current_config_file}, f)
        except Exception as e: print(f"Failed to save prefs: {e}")

    def create_tray_icon(self):
        tray = QSystemTrayIcon()
        
        if getattr(sys, 'frozen', False): res_path = sys._MEIPASS
        else: res_path = self.base_dir
            
        icon_path = os.path.join(res_path, "TouchMultiButton.ico")
        if os.path.exists(icon_path): tray.setIcon(QIcon(icon_path))
        else:
            from PyQt5.QtWidgets import QStyle
            tray.setIcon(self.app.style().standardIcon(QStyle.SP_ComputerIcon))

        menu = QMenu()
        self.config_menu = menu.addMenu("切换配置")
        self.update_config_menu()
        self.config_menu.aboutToShow.connect(self.update_config_menu)
        menu.addSeparator()
        
        menu.addAction("管理按钮").triggered.connect(self.show_settings)
        
        self.lock_action = menu.addAction("锁定所有位置")
        self.lock_action.setCheckable(True)
        if self.buttons and self.buttons[0].config.get('position_lock', False):
            self.lock_action.setChecked(True)
        self.lock_action.triggered.connect(self.toggle_all_locks)
        
        menu.addSeparator()
        menu.addAction("退出").triggered.connect(self.clean_exit)
        tray.setContextMenu(menu)
        tray.show()
        return tray

    def update_config_menu(self):
        self.config_menu.clear()
        files = [f for f in os.listdir(self.config_dir) if f.endswith('.json') and f != 'preferences.json']
        if not files: files = ['default.json']
        for f in files:
            action = self.config_menu.addAction(f)
            action.setCheckable(True)
            action.setChecked(f == self.current_config_file)
            action.triggered.connect(lambda checked, fname=f: self.switch_config(fname))
        self.config_menu.addSeparator()
        new_action = self.config_menu.addAction("新建配置...")
        new_action.triggered.connect(self.create_new_config)

    def switch_config(self, filename):
        if filename == self.current_config_file: return
        print(f"Switching to config: {filename}")
        self.current_config_file = filename
        self.save_prefs()
        self.load_config(filename)
        
    def create_new_config(self):
        import time
        new_name = f"config_{int(time.time())}.json"
        new_path = os.path.join(self.config_dir, new_name)
        with open(new_path, 'w') as f: json.dump({"buttons": []}, f, indent=2)
        self.switch_config(new_name)
        self.tray.showMessage("TouchButton", f"已创建并切换到新配置: {new_name}", QSystemTrayIcon.Information, 2000)
        self.show_settings() 

    def toggle_all_locks(self):
        is_locked = self.lock_action.isChecked()
        for btn in self.buttons: btn.config['position_lock'] = is_locked
        for btn_cfg in self.config['buttons']: btn_cfg['position_lock'] = is_locked
        self.save_config()
        msg = "所有按钮已锁定" if is_locked else "所有按钮已解锁"
        self.tray.showMessage("TouchButton", msg, QSystemTrayIcon.Information, 2000)

    def load_config(self, filename=None):
        if filename: self.current_config_file = filename
        config_path = os.path.join(self.config_dir, self.current_config_file)
        try:
            if not os.path.exists(config_path):
                self.config = {"buttons": []}
                self.save_config()
            else:
                with open(config_path, 'r', encoding='utf-8') as f: self.config = json.load(f)
            self.create_buttons()
            if hasattr(self, 'lock_action') and self.config['buttons']:
                locked = self.config['buttons'][0].get('position_lock', False)
                self.lock_action.setChecked(locked)
        except Exception as e:
            print(f"加载配置失败: {e}")
            self.config = {"buttons": []}; self.create_buttons()

    def create_buttons(self):
        for btn in self.buttons: btn.deleteLater() 
        self.buttons.clear()   
        for btn_cfg in self.config['buttons']: self.create_single_button(btn_cfg)

    def create_single_button(self, config):
        button = DraggableButton(config)
        button.clicked.connect(lambda _, c=config: self.trigger_shortcut(c['shortcut']))
        button.positionChanged.connect(self.handle_position_change)
        button.show()
        self.buttons.append(button)

    def handle_position_change(self, new_config):
        try:
            index = next(i for i, btn in enumerate(self.buttons) if btn.config['id'] == new_config['id'])
            self.buttons[index].config = new_config
            QTimer.singleShot(100, self.save_config)
        except StopIteration: pass

    def trigger_shortcut(self, shortcut):
        if not shortcut: return
        try:
            keyboard.press(shortcut); keyboard.release(shortcut)
        except ValueError: print(f"无效的快捷键: {shortcut}")
        except Exception as e: print(f"快捷键执行错误: {e}")

    def apply_live_settings(self, new_config):
        self.config = copy.deepcopy(new_config)
        self.create_buttons()

    def show_settings(self):
        original_config = copy.deepcopy(self.config)
        original_filename = self.current_config_file
        dialog = SettingsDialog(self.config_dir, self.current_config_file, self.config, apply_callback=self.apply_live_settings)
        if dialog.exec_():
            new_filename, new_config = dialog.get_values()
            self.current_config_file = new_filename
            self.config = new_config
            self.save_config()
            self.save_prefs()
            self.create_buttons()
        else:
            self.current_config_file = original_filename
            self.config = original_config
            self.create_buttons()

    def save_config(self):
        config_path = os.path.join(self.config_dir, self.current_config_file)
        try:
            self.config['buttons'] = [btn.config for btn in self.buttons]
            with open(config_path, 'w', encoding='utf-8') as f: json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e: print(f"保存配置失败: {e}")

    def clean_exit(self):
        self.save_config()
        for btn in self.buttons: btn.deleteLater()
        self.app.quit()

    def run(self): sys.exit(self.app.exec_())

if __name__ == "__main__":
    app = TouchButtonApp()
    app.run()