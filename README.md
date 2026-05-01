# HLL Artillery Assistant

> Hell Let Loose 炮兵射击辅助工具 — 桌面端地图标定 + 移动端实时同步

## 功能概览

- **地图标定**：加载游戏地图图片，拖拽设定炮兵位置，自动计算目标点
- **键盘实时操控**：W/S 调整距离，A/D 调整方位角/朝向，Shift 吸附正方向
- **射界预览**：扇形射界 + 瞄准线 + 箭头实时预览
- **屏幕截图叠加**：截取游戏内地图区域，半透明叠加到底图上
- **移动端同步**：通过 WebRTC P2P 将地图、叠加层、标定数据实时同步到手机浏览器
- **双模式切换**：STD（标准炮兵）和 SPG（自行火炮，开发中）独立状态

## 安装

```bash
# 克隆项目
git clone <repo-url>
cd HLL_artillery_assistant

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

# 安装依赖
pip install PySide6 aiortc peerjs_py
```

## 运行

```bash
python main.py
```

### 或直接下载release中的压缩包解压即可
震撼美味，开盖即食（）

## 使用指南

### 1. 加载地图

`File → Open...`（Ctrl+O）选择游戏地图图片（支持 PNG/JPG/BMP）。

### 2. 设置炮兵位置

点击侧边栏 **Set A Point** 或在地图上点击拖拽：
- 拖拽设定朝向（射线方向）
- 按住 **Shift** 吸附正方向（0°/90°/180°/270°）
- 短距离点击（<5px）视为取消
- **Esc** 取消操作

### 3. 键盘操控

| 模式 | 按键 | 功能             |
|---|---|----------------|
| **F1**（Gunner，炮手） | W / S | 减小 / 增大距离      |
| | A / D | 逆时针 / 顺时针旋转方位角 |
| **F2**（Loader，装填手） | A / D | 移动炮架           |

### 4. Telemetry 面板

| 指标 | 含义                                     |
|---|----------------------------------------|
| Mode | 当前模式（STD · Gunner / STD · Loader） |
| Distance | 距离（m）                                  |
| Azimuth | 方位角（°）                                 |
| MIL | 密位值（MIL）                               |
| Relative | 相对射界偏角（°）                              |


### 5. 屏幕截图叠加

1. 调整 `Settings` 中的截图区域（LEFT/RIGHT/TOP/BOTTOM）
2. 点击 **Capture Overlay** 截取游戏内地图
3. 截图以半透明方式叠加到底图上
4. 点击 **Clear Overlay** 清除

### 6. 移动端同步

1. 点击 **Start Mobile Sync** 启动 P2P 信令服务
2. 侧边栏显示 Peer ID 和 Viewer 文件路径
3. 在手机浏览器中打开生成的 `sessions/mobile_viewer_<id>.html`
4. 输入 Peer ID 点击 Connect
5. 连接成功后手机端实时显示地图、A/B 点、射界和 Telemetry 数据
6. 手机端支持单指拖拽平移、双指缩放

### 7. 设置

`Settings...`（Ctrl+,）可配置：

| 标签页 | 配置项 |
|---|---|
| Appearance | A/B 点半径、箭头大小、拖拽阈值、4 种颜色 |
| Capture & Overlay | 截图区域四边坐标、叠加层透明度 |
| Mobile Sync | 同步帧率、JPEG 质量、信令服务器参数 |

配置保存至 `settings.json`，重启后自动加载。

## 项目结构

```
HLL_artillery_assistant/
├── main.py                  # 入口，暗色主题初始化
├── config.py                # 配置常量 + settings.json 读写
├── logic.py                 # 炮兵数学：MIL、距离、方位角、射界
├── capture.py               # 屏幕截图
├── ui/
│   ├── main_window.py       # 主窗口：菜单、侧边栏、键盘轮询
│   ├── map_view.py          # 地图视图：A/B 点、射界、叠加层、缩放
│   └── settings_dialog.py   # 设置对话框（3 标签页）
├── sync/
│   ├── desktop_sync.py      # WebRTC 同步管理器
│   └── viewer_page.py       # 移动端 HTML 模板生成
├── web/
│   └── mobile_viewer.html   # 移动端页面模板
├── sessions/                # 生成的 session HTML（gitignore）
├── sync/logs/               # 同步日志（gitignore）
└── tests/
    └── test_logic.py        # 数学函数单元测试
```

## 移动端界面

连接前显示登录卡片（Peer ID 输入 + Connect 按钮），连接后分为：

- **左侧栏**：Telemetry / Connection / Diagnostics 三组
- **右侧画布**：地图 + 叠加层 + 炮击目标点（红）/ 炮位（绿）/ 射界


## 技术栈

| 桌面端 | 移动端 | 通信 |
|---|---|---|
| Python 3.10+ | HTML5 Canvas | WebRTC (aiortc) |
| PySide6 (Qt) | PeerJS 1.5.5 | PeerJS signaling |
| Win32 API (键盘) | Vanilla JS | P2P DataChannel |
