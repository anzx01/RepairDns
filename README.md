# DNS 一键修复助手

VPN / 代理软件关闭后常将 Windows DNS 改为静态配置，导致网络异常。本工具一键检测并恢复所有适配器的 DNS 为自动获取（DHCP）。

    ![1771576013262](image/README/1771576013262.png)

## 功能

- 自动枚举所有已连接的网络适配器
- 检测每个适配器的 DNS 模式（DHCP / 静态）
- **一键修复全部**静态 DNS，无需逐个操作
- 修复前自动备份当前配置
- 可选修复后清除 DNS 缓存（`ipconfig /flushdns`）
- 操作日志记录，支持查看和清除
- 后台定时监控（可在设置中开启）

## 文件结构

```
RepairDns/
├── main.py        # GUI 主程序（tkinter）
├── dns_core.py    # DNS 检测 / 修复核心逻辑
├── build.bat      # PyInstaller 打包脚本
└── README.md
```

数据文件保存在 `%APPDATA%\RepairDns\`：

| 文件              | 内容                    |
| ----------------- | ----------------------- |
| `settings.json` | 用户设置                |
| `backups.json`  | DNS 配置备份            |
| `log.json`      | 操作日志（最近 200 条） |

## 运行要求

- Windows 7 / 10 / 11
- Python 3.8+（含 tkinter，标准库自带）
- **管理员权限**（修改 DNS 需要）

## 直接运行

```bat
C:\Python314\python.exe main.py
```

程序启动时若无管理员权限会自动弹出 UAC 提权请求。

## 打包为单文件 exe

```bat
build.bat
```

输出：`dist\DNS一键修复助手.exe`，约 15–20 MB，无需安装 Python。

> 首次运行 `build.bat` 会自动安装 PyInstaller。

## 技术说明

DNS 状态通过解析 `netsh interface ip show config` 输出判断，同时支持中文和英文 Windows 系统的输出格式。修复命令：

```bat
netsh interface ip set dns "适配器名称" dhcp
ipconfig /flushdns
```
