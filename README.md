# TouchMultiButton

一个基于PyQt5的多功能触摸按钮应用，支持自定义快捷键和可拖拽按钮布局。

## 功能特性

- 🎯 **可拖拽按钮**：按钮可以在屏幕上自由拖动定位
- ⌨️ **自定义快捷键**：每个按钮可以绑定不同的键盘快捷键
- ⚙️ **多配置支持**：支持多个配置文件，方便不同场景使用
- 🖥️ **系统托盘**：应用常驻系统托盘，不占用任务栏
- 🔒 **位置锁定**：支持锁定按钮位置防止误操作

## 项目结构

```
TouchMultiButton/
├── main.py              # 主程序入口
├── button.py            # 可拖拽按钮实现
├── settings_window.py   # 设置窗口界面
├── config/              # 配置文件目录
│   ├── preferences.json # 用户偏好设置
│   └── *.json          # 各种场景配置
├── TouchMultiButton.ico # 应用图标
└── README.md           # 项目说明
```

## 安装依赖

```bash
pip install PyQt5 keyboard
```

## 使用方法

1. 运行 `main.py` 启动应用
2. 应用会出现在系统托盘中
3. 右键点击托盘图标选择"管理按钮"进行配置
4. 可以创建多个配置文件，在不同场景间切换

## 配置说明

配置文件采用JSON格式，包含按钮的位置、大小、快捷键等信息：

```json
{
  "buttons": [
    {
      "id": "button1",
      "text": "按钮1", 
      "shortcut": "ctrl+a",
      "x": 100,
      "y": 200,
      "width": 80,
      "height": 40,
      "position_lock": false
    }
  ]
}
```

## 快捷键语法

支持标准的键盘快捷键语法：
- 单键：`a`, `enter`, `space`
- 组合键：`ctrl+c`, `alt+f4`, `shift+tab`
- 多键组合：`ctrl+shift+esc`

## 开发说明

- 使用PyQt5进行GUI开发
- 使用keyboard库模拟键盘输入
- 支持打包为可执行文件

## 许可证

MIT License"# TouchMultiButton" 
"# TouchMultiButton" 
