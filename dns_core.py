# dns_core.py — DNS 检测与修复核心逻辑
import subprocess
import re
import json
import os
import ctypes
import sys
from datetime import datetime
from typing import Optional

# ── 常量 ──────────────────────────────────────────────
DATA_DIR = os.path.join(os.environ.get('APPDATA', '.'), 'RepairDns')
BACKUP_FILE = os.path.join(DATA_DIR, 'backups.json')
LOG_FILE = os.path.join(DATA_DIR, 'log.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')

os.makedirs(DATA_DIR, exist_ok=True)

# ── 权限 ──────────────────────────────────────────────
def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def relaunch_as_admin():
    """以管理员权限重启自身"""
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, ' '.join(sys.argv), None, 1
    )
    sys.exit(0)

# ── 命令执行 ──────────────────────────────────────────
def run(cmd: str) -> str:
    result = subprocess.run(
        cmd, shell=True, capture_output=True
    )
    # 尝试 GBK 解码（中文 Windows），失败则 UTF-8
    for enc in ('gbk', 'utf-8', 'latin-1'):
        try:
            return result.stdout.decode(enc)
        except Exception:
            continue
    return ''

# ── 适配器枚举 ────────────────────────────────────────
CONNECTED_RE = re.compile(r'Connected|已连接', re.IGNORECASE)

def get_active_adapters() -> list[dict]:
    output = run('netsh interface show interface')
    adapters = []
    lines = output.splitlines()
    # 找表头后的数据行
    start = 0
    for i, line in enumerate(lines):
        if re.search(r'Admin|管理员', line):
            start = i + 2
            break
    for line in lines[start:]:
        line = line.strip()
        if not line or not CONNECTED_RE.search(line):
            continue
        # 前3列是状态字段，第4列起是名称
        parts = re.split(r'\s{2,}', line)
        if len(parts) >= 4:
            name = ' '.join(parts[3:]).strip()
            if name:
                adapters.append({
                    'name': name,
                    'type': _guess_type(name),
                    'has_gateway': False,
                })
    _mark_gateway(adapters)
    return adapters

def _guess_type(name: str) -> str:
    n = name.lower()
    if re.search(r'wi-?fi|wlan|wireless|无线', n): return 'wifi'
    if re.search(r'ethernet|以太网|local area', n): return 'ethernet'
    if re.search(r'vmware|virtualbox|hyper-v|loopback|虚拟|vethernet', n): return 'virtual'
    return 'other'

def _mark_gateway(adapters: list[dict]):
    try:
        out = run('route print 0.0.0.0')
        for a in adapters:
            if a['name'] in out:
                a['has_gateway'] = True
        if not any(a['has_gateway'] for a in adapters):
            for a in adapters:
                if a['type'] in ('ethernet', 'wifi'):
                    a['has_gateway'] = True
                    break
    except Exception:
        pass

# ── DNS 状态检测 ──────────────────────────────────────
DHCP_RE = [
    re.compile(r'DNS\s+Servers\s+configured\s+through\s+DHCP', re.IGNORECASE),
    re.compile(r'通过\s*DHCP\s*配置的\s*DNS'),
    re.compile(r'DHCP\s+配置的\s*DNS'),
]
STATIC_RE = [
    re.compile(r'Statically\s+Configured\s+DNS\s+Servers', re.IGNORECASE),
    re.compile(r'静态配置的\s*DNS\s*服务器'),
    re.compile(r'手动配置的\s*DNS'),
]
IP_RE = re.compile(r'(\d{1,3}(?:\.\d{1,3}){3})')

def get_dns_config(adapter_name: str) -> dict:
    try:
        output = run(f'netsh interface ip show config "{adapter_name}"')
        return _parse_netsh(output, adapter_name)
    except Exception as e:
        return {'adapter': adapter_name, 'mode': 'unknown', 'ips': [], 'raw': str(e)}

def _parse_netsh(output: str, adapter_name: str) -> dict:
    mode = 'unknown'
    ips = []
    for line in output.splitlines():
        if any(p.search(line) for p in DHCP_RE):
            mode = 'dhcp'
            m = IP_RE.search(line)
            if m: ips.append(m.group(1))
            continue
        if any(p.search(line) for p in STATIC_RE):
            mode = 'static'
            m = IP_RE.search(line)
            if m: ips.append(m.group(1))
            continue
        if mode == 'static':
            t = line.strip()
            if IP_RE.match(t) and '.' in t and not re.search(r'[a-zA-Z]', t):
                ips.append(t)
    return {'adapter': adapter_name, 'mode': mode, 'ips': ips, 'raw': output}

# ── DNS 修复 ──────────────────────────────────────────
def repair_dns(adapter_name: str, flush: bool = True) -> dict:
    before = get_dns_config(adapter_name)
    _save_backup(before)
    try:
        run(f'netsh interface ip set dns "{adapter_name}" dhcp')
        if flush:
            run('ipconfig /flushdns')
        after = get_dns_config(adapter_name)
        _add_log('repair', adapter_name, before, after, True)
        return {'success': True, 'adapter': adapter_name}
    except Exception as e:
        _add_log('repair', adapter_name, before, None, False, str(e))
        return {'success': False, 'adapter': adapter_name, 'error': str(e)}

# ── 备份 ─────────────────────────────────────────────
def _save_backup(config: dict):
    backups = _load_json(BACKUP_FILE, [])
    # 每个适配器保留最近 10 条
    same = [b for b in backups if b['adapter'] != config['adapter']]
    kept = same[-9:] if len(same) > 9 else same
    kept.append({'ts': _now(), **config})
    _save_json(BACKUP_FILE, kept)

def get_backups() -> list:
    return _load_json(BACKUP_FILE, [])

def rollback(backup: dict) -> dict:
    adapter = backup['adapter']
    before = get_dns_config(adapter)
    try:
        if backup['mode'] == 'dhcp':
            run(f'netsh interface ip set dns "{adapter}" dhcp')
        elif backup['ips']:
            run(f'netsh interface ip set dns "{adapter}" static {backup["ips"][0]}')
            if len(backup['ips']) > 1:
                run(f'netsh interface ip add dns "{adapter}" {backup["ips"][1]} index=2')
        after = get_dns_config(adapter)
        _add_log('rollback', adapter, before, after, True)
        return {'success': True}
    except Exception as e:
        _add_log('rollback', adapter, before, None, False, str(e))
        return {'success': False, 'error': str(e)}

# ── 日志 ─────────────────────────────────────────────
def _add_log(action, adapter, before, after, success, error=None):
    logs = _load_json(LOG_FILE, [])
    logs.append({
        'ts': _now(), 'action': action, 'adapter': adapter,
        'before_mode': before.get('mode'), 'before_ips': before.get('ips', []),
        'after_mode': after.get('mode') if after else None,
        'success': success, 'error': error,
    })
    _save_json(LOG_FILE, logs[-200:])

def get_logs() -> list:
    return list(reversed(_load_json(LOG_FILE, [])))

def clear_logs():
    _save_json(LOG_FILE, [])

# ── 设置 ─────────────────────────────────────────────
DEFAULT_SETTINGS = {
    'auto_monitor': False,
    'monitor_interval': 5,
    'auto_repair': False,
    'flush_on_repair': True,
    'language': 'zh',
}

def get_settings() -> dict:
    s = _load_json(SETTINGS_FILE, {})
    return {**DEFAULT_SETTINGS, **s}

def save_settings(s: dict):
    _save_json(SETTINGS_FILE, s)

# ── 工具函数 ──────────────────────────────────────────
def _now() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def _load_json(path: str, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path: str, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
