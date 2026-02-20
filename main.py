# main.py — DNS 一键修复助手主界面
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
import os

import dns_core as core

# ── 颜色主题（对应 Pencil 设计）────────────────────────
BG       = '#1a1a1a'
BG_CARD  = '#212121'
BG_ELEV  = '#2d2d2d'
BG_PH    = '#3d3d3d'
ORANGE   = '#ff6b35'
TEAL     = '#00d4aa'
RED      = '#ff4444'
WHITE    = '#ffffff'
GRAY     = '#777777'
BLACK_T  = '#0d0d0d'

FONT_H   = ('Oswald', 18, 'bold')
FONT_HM  = ('Oswald', 14, 'bold')
FONT_HS  = ('Oswald', 11, 'bold')
FONT_M   = ('Consolas', 11)
FONT_S   = ('Consolas', 10)
FONT_XS  = ('Consolas', 9)

WIN_W, WIN_H = 480, 600


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('DNS 一键修复助手')
        self.geometry(f'{WIN_W}x{WIN_H}')
        self.resizable(False, False)
        self.configure(bg=BG)
        self.overrideredirect(True)   # 无边框

        # 拖动支持
        self._drag_x = self._drag_y = 0
        self._frame = None

        # 状态
        self.adapters: list[dict] = []
        self.dns_configs: dict[str, dict] = {}
        self.selected_adapter = tk.StringVar()
        self.is_admin = core.is_admin()

        self._build_ui()
        self._center()
        self.after(100, self.refresh)

    # ── 布局 ──────────────────────────────────────────
    def _build_ui(self):
        self._build_titlebar()
        self._build_status()
        self._build_adapter_row()
        self._build_info_panel()
        self._build_repair_area()
        self._build_action_bar()

    def _build_titlebar(self):
        bar = tk.Frame(self, bg=BG_CARD, height=48)
        bar.pack(fill='x')
        bar.pack_propagate(False)

        tk.Label(bar, text='DNS_REPAIR', bg=BG_CARD, fg=WHITE,
                 font=FONT_H).place(x=20, rely=0.5, anchor='w')

        # 管理员徽章
        if self.is_admin:
            badge = tk.Frame(bar, bg=TEAL)
            badge.place(relx=1, rely=0.5, x=-90, anchor='e')
            tk.Label(badge, text='● ADMIN', bg=TEAL, fg=BLACK_T,
                     font=FONT_XS, padx=8, pady=3).pack()

        # 关闭按钮
        close = tk.Label(bar, text='✕', bg=BG_ELEV, fg=GRAY,
                         font=FONT_M, width=3, cursor='hand2')
        close.place(relx=1, rely=0.5, x=-10, anchor='e')
        close.bind('<Button-1>', lambda e: self.destroy())

        # 拖动
        bar.bind('<ButtonPress-1>', self._drag_start)
        bar.bind('<B1-Motion>', self._drag_move)

    def _build_status(self):
        self.status_frame = tk.Frame(self, bg=BG, height=220)
        self.status_frame.pack(fill='x')
        self.status_frame.pack_propagate(False)

        # 状态圆圈（用 Canvas 画）
        self.canvas = tk.Canvas(self.status_frame, width=130, height=130,
                                bg=BG, highlightthickness=0)
        self.canvas.place(relx=0.5, y=20, anchor='n')

        self.lbl_dns_label = tk.Label(self.status_frame, text='// DNS_STATUS',
                                      bg=BG, fg=GRAY, font=FONT_XS)
        self.lbl_dns_label.place(relx=0.5, y=158, anchor='n')

        self.lbl_status = tk.Label(self.status_frame, text='检测中...',
                                   bg=BG, fg=GRAY, font=('Oswald', 22, 'bold'))
        self.lbl_status.place(relx=0.5, y=174, anchor='n')

        self.lbl_desc = tk.Label(self.status_frame, text='正在扫描网络适配器...',
                                 bg=BG, fg=GRAY, font=FONT_S)
        self.lbl_desc.place(relx=0.5, y=202, anchor='n')

    def _draw_circle(self, color: str, bg_color: str):
        c = self.canvas
        c.delete('all')
        # 外圆背景
        c.create_oval(3, 3, 127, 127, fill=bg_color, outline=color, width=3)
        # 内圆
        c.create_oval(22, 22, 108, 108, fill=color, outline='')
        # 正常状态显示勾
        if color == TEAL:
            c.create_text(65, 65, text='✓', fill=BLACK_T,
                          font=('Arial', 28, 'bold'))

    def _build_adapter_row(self):
        self.adapter_row = tk.Frame(self, bg=BG, height=32)
        self.adapter_row.pack(fill='x', padx=20)
        self.adapter_row.pack_propagate(False)

        tk.Label(self.adapter_row, text='ADAPTER', bg=BG, fg=GRAY,
                 font=FONT_XS).pack(side='left', pady=6)

        self.adapter_menu = ttk.Combobox(
            self.adapter_row, textvariable=self.selected_adapter,
            state='readonly', font=FONT_S, width=28
        )
        self.adapter_menu.pack(side='right', pady=4)
        self.adapter_menu.bind('<<ComboboxSelected>>', self._on_adapter_change)
        self._style_combobox()

    def _style_combobox(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TCombobox',
                        fieldbackground=BG_ELEV, background=BG_ELEV,
                        foreground=WHITE, selectbackground=BG_ELEV,
                        selectforeground=WHITE, bordercolor=BG_PH,
                        arrowcolor=GRAY, relief='flat')
        style.map('TCombobox', fieldbackground=[('readonly', BG_ELEV)],
                  foreground=[('readonly', WHITE)])

    def _build_info_panel(self):
        self.info_frame = tk.Frame(self, bg=BG)
        self.info_frame.pack(fill='x', padx=20, pady=(4, 0))

        self.info_rows: list[tk.Frame] = []
        for _ in range(3):
            row = tk.Frame(self.info_frame, bg=BG_CARD, height=42)
            row.pack(fill='x', pady=1)
            row.pack_propagate(False)
            self.info_rows.append(row)

    def _set_info_row(self, idx: int, key: str, value: str, val_color=WHITE):
        row = self.info_rows[idx]
        for w in row.winfo_children():
            w.destroy()
        tk.Label(row, text=key, bg=BG_CARD, fg=GRAY,
                 font=FONT_XS).place(x=16, rely=0.5, anchor='w')
        tk.Label(row, text=value, bg=BG_CARD, fg=val_color,
                 font=FONT_S).place(relx=1, x=-16, rely=0.5, anchor='e')

    def _build_repair_area(self):
        area = tk.Frame(self, bg=BG)
        area.pack(fill='x', padx=20, pady=12)

        self.repair_btn = tk.Label(
            area, text='⚡  立即修复 DNS',
            bg=ORANGE, fg=BLACK_T, font=('Oswald', 16, 'bold'),
            height=2, cursor='hand2', relief='flat'
        )
        self.repair_btn.pack(fill='x', ipady=4)
        self.repair_btn.bind('<Button-1>', self._on_repair)

        self.note_frame = tk.Frame(area, bg=BG_CARD)
        self.note_frame.pack(fill='x', pady=(8, 0))
        self.note_lbl = tk.Label(
            self.note_frame,
            text='⚠  [WARNING] 修复前将自动备份当前配置',
            bg=BG_CARD, fg=GRAY, font=FONT_XS, anchor='w', padx=14, pady=8
        )
        self.note_lbl.pack(fill='x')

    def _build_action_bar(self):
        bar = tk.Frame(self, bg=BG_CARD, height=44)
        bar.pack(fill='x', side='bottom')
        bar.pack_propagate(False)

        def btn(parent, text, cmd):
            b = tk.Label(parent, text=text, bg=BG_ELEV, fg=WHITE,
                         font=FONT_XS, padx=12, pady=6, cursor='hand2')
            b.bind('<Button-1>', lambda e: cmd())
            b.bind('<Enter>', lambda e: b.config(bg=BG_PH))
            b.bind('<Leave>', lambda e: b.config(bg=BG_ELEV))
            return b

        btn(bar, '↻  refresh', self.refresh).pack(side='left', padx=(12, 0), pady=8)
        btn(bar, '≡  log', self._open_log).pack(side='right', padx=(0, 8), pady=8)
        btn(bar, '⚙  settings', self._open_settings).pack(side='right', padx=(0, 4), pady=8)

    # ── 拖动 ──────────────────────────────────────────
    def _drag_start(self, e):
        self._drag_x, self._drag_y = e.x, e.y

    def _drag_move(self, e):
        x = self.winfo_x() + e.x - self._drag_x
        y = self.winfo_y() + e.y - self._drag_y
        self.geometry(f'+{x}+{y}')

    def _center(self):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = (sw - WIN_W) // 2, (sh - WIN_H) // 2
        self.geometry(f'{WIN_W}x{WIN_H}+{x}+{y}')

    # ── 数据刷新 ──────────────────────────────────────
    def refresh(self):
        self.lbl_status.config(text='检测中...', fg=GRAY)
        self.lbl_desc.config(text='正在扫描网络适配器...')
        self._draw_circle(GRAY, BG_CARD)
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        adapters = core.get_active_adapters()
        configs = {a['name']: core.get_dns_config(a['name']) for a in adapters}
        self.after(0, self._apply_refresh, adapters, configs)

    def _apply_refresh(self, adapters, configs):
        self.adapters = adapters
        self.dns_configs = configs

        names = [a['name'] for a in adapters]
        self.adapter_menu['values'] = names

        cur = self.selected_adapter.get()
        if not cur or cur not in names:
            # 优先选有网关的
            primary = next((a for a in adapters if a['has_gateway']), adapters[0] if adapters else None)
            if primary:
                self.selected_adapter.set(primary['name'])

        self._update_status()

    def _update_status(self):
        if not self.adapters:
            self._draw_circle(GRAY, BG_CARD)
            self.lbl_status.config(text='未检测到网络', fg=GRAY)
            self.lbl_desc.config(text='请检查网络连接', fg=GRAY)
            self._set_repair_state([])
            return

        # 统计所有静态 DNS 适配器
        static_adapters = [
            a['name'] for a in self.adapters
            if self.dns_configs.get(a['name'], {}).get('mode') == 'static'
        ]

        # 当前选中适配器用于详情展示
        name = self.selected_adapter.get()
        cfg = self.dns_configs.get(name, {})
        mode = cfg.get('mode', 'unknown')
        ips = cfg.get('ips', [])

        if static_adapters:
            self._draw_circle(RED, '#2D1A1A')
            self.lbl_dns_label.config(fg=RED)
            count = len(static_adapters)
            self.lbl_status.config(text='STATIC_DNS', fg=RED)
            self.lbl_desc.config(
                text=f'发现 {count} 个适配器 DNS 被修改', fg=GRAY)
            self._set_info_row(0, 'AFFECTED', f'{count} adapter(s)', RED)
            if mode == 'static':
                self._set_info_row(1, 'PRIMARY_DNS', ips[0] if ips else '—', RED)
                self._set_info_row(2, 'SECONDARY_DNS', ips[1] if len(ips) > 1 else '—', RED)
            else:
                self._set_info_row(1, 'ADAPTER', name)
                self._set_info_row(2, 'DNS_MODE', mode.upper(), GRAY)
            self._set_repair_state(static_adapters)
        elif mode == 'dhcp' or all(
            self.dns_configs.get(a['name'], {}).get('mode') == 'dhcp'
            for a in self.adapters
        ):
            self._draw_circle(TEAL, '#0D2B1F')
            self.lbl_dns_label.config(fg=TEAL)
            self.lbl_status.config(text='DHCP_AUTO', fg=TEAL)
            self.lbl_desc.config(text='所有适配器 DNS 自动获取，正常', fg=GRAY)
            self._set_info_row(0, 'ADAPTER_NAME', name)
            self._set_info_row(1, 'DNS_MODE', '■ 自动获取 (DHCP)', TEAL)
            self._set_info_row(2, '', '')
            self._set_repair_state([])
        else:
            self._draw_circle(GRAY, BG_CARD)
            self.lbl_dns_label.config(fg=GRAY)
            self.lbl_status.config(text='UNKNOWN', fg=GRAY)
            self.lbl_desc.config(text='无法检测DNS状态', fg=GRAY)
            self._set_info_row(0, 'ADAPTER_NAME', name)
            self._set_info_row(1, '', '')
            self._set_info_row(2, '', '')
            self._set_repair_state([])

    def _set_repair_state(self, static_adapters: list):
        if static_adapters:
            count = len(static_adapters)
            label = f'⚡  修复全部 ({count} 个适配器)' if count > 1 else '⚡  立即修复 DNS'
            self.repair_btn.config(bg=ORANGE, fg=BLACK_T,
                                   text=label, cursor='hand2')
            self.note_lbl.config(text='⚠  [WARNING] 修复前将自动备份当前配置', fg=GRAY)
        else:
            self.repair_btn.config(bg=BG_ELEV, fg=BG_PH,
                                   text='⚡  DNS 状态正常', cursor='arrow')
            self.note_lbl.config(text='[OK] 无需修复，网络连接正常', fg=GRAY)
        self._static_adapters = static_adapters

    def _on_adapter_change(self, _=None):
        self._update_status()

    # ── 修复 ──────────────────────────────────────────
    def _on_repair(self, _=None):
        targets = getattr(self, '_static_adapters', [])
        if not targets:
            return
        self.repair_btn.config(text='修复中...', bg=BG_ELEV, fg=GRAY, cursor='arrow')
        flush = core.get_settings().get('flush_on_repair', True)
        threading.Thread(
            target=self._do_repair,
            args=(targets, flush),
            daemon=True
        ).start()

    def _do_repair(self, names: list, flush: bool):
        results = [core.repair_dns(n, flush=(flush and i == len(names) - 1))
                   for i, n in enumerate(names)]
        self.after(0, self._apply_repair, results)

    def _apply_repair(self, results: list):
        failed = [r for r in results if not r['success']]
        if not failed:
            count = len(results)
            self.note_lbl.config(
                text=f'[OK] 修复成功，{count} 个适配器已恢复自动获取', fg=TEAL
            )
            self.refresh()
        else:
            errs = '; '.join(r.get('error', r['adapter']) for r in failed)
            self.note_lbl.config(
                text=f'[ERROR] 部分失败: {errs}', fg=RED
            )
            self.repair_btn.config(text='⚡  立即修复 DNS', bg=ORANGE,
                                   fg=BLACK_T, cursor='hand2')

    # ── 子窗口 ────────────────────────────────────────
    def _open_settings(self):
        SettingsWindow(self)

    def _open_log(self):
        LogWindow(self)


# ── 设置窗口 ──────────────────────────────────────────
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('设置')
        self.geometry('400x480')
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()

        self.settings = core.get_settings()
        self._vars: dict[str, tk.Variable] = {}
        self._build()

    def _build(self):
        # 标题栏
        bar = tk.Frame(self, bg=BG_CARD, height=44)
        bar.pack(fill='x')
        bar.pack_propagate(False)
        tk.Label(bar, text='SETTINGS', bg=BG_CARD, fg=WHITE,
                 font=FONT_H).place(x=16, rely=0.5, anchor='w')
        tk.Label(bar, text='✕ close', bg=BG_ELEV, fg=GRAY,
                 font=FONT_XS, padx=10, pady=4, cursor='hand2').place(
            relx=1, x=-12, rely=0.5, anchor='e'
        ).bind('<Button-1>', lambda e: self.destroy()) if False else None
        close = tk.Label(bar, text='✕ close', bg=BG_ELEV, fg=GRAY,
                         font=FONT_XS, padx=10, pady=4, cursor='hand2')
        close.place(relx=1, x=-12, rely=0.5, anchor='e')
        close.bind('<Button-1>', lambda e: self.destroy())

        content = tk.Frame(self, bg=BG)
        content.pack(fill='both', expand=True, padx=16, pady=12)

        self._section(content, '// MONITOR_OPTIONS')
        self._toggle_row(content, 'auto_monitor', 'auto_monitor', '后台定时检测DNS状态')

        # 间隔选择
        row = tk.Frame(content, bg=BG_CARD)
        row.pack(fill='x', pady=2)
        tk.Label(row, text='monitor_interval', bg=BG_CARD, fg=WHITE,
                 font=FONT_S, padx=14, pady=10).pack(side='left')
        seg = tk.Frame(row, bg=BG_CARD)
        seg.pack(side='right', padx=14, pady=8)
        self._vars['monitor_interval'] = tk.IntVar(value=self.settings.get('monitor_interval', 5))
        for val in [5, 10, 30]:
            b = tk.Label(seg, text=f'{val}min', bg=BG_ELEV, fg=GRAY,
                         font=FONT_XS, padx=10, pady=4, cursor='hand2')
            b.pack(side='left', padx=2)
            b.bind('<Button-1>', lambda e, v=val, btn=b: self._select_interval(v))
            if val == self.settings.get('monitor_interval', 5):
                b.config(bg=ORANGE, fg=BLACK_T)
            setattr(self, f'_interval_btn_{val}', b)

        self._toggle_row(content, 'auto_repair', 'auto_repair', '发现异常时自动修复')
        self._toggle_row(content, 'flush_on_repair', 'flush_on_repair', '修复时清除DNS缓存')

        self._section(content, '// OTHER')
        self._toggle_row(content, 'language', 'language_zh', '使用中文界面',
                         is_bool=False, bool_val='zh')

        # 保存按钮
        save = tk.Label(content, text='✓  save_settings',
                        bg=ORANGE, fg=BLACK_T, font=('Oswald', 14, 'bold'),
                        height=2, cursor='hand2')
        save.pack(fill='x', pady=(16, 0))
        save.bind('<Button-1>', self._save)

    def _section(self, parent, text):
        tk.Label(parent, text=text, bg=BG, fg=ORANGE,
                 font=FONT_XS, anchor='w').pack(fill='x', pady=(8, 2))

    def _toggle_row(self, parent, key, var_key, desc, is_bool=True, bool_val=None):
        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(fill='x', pady=2)
        tk.Label(row, text=key, bg=BG_CARD, fg=WHITE,
                 font=FONT_S, padx=14, pady=10).pack(side='left')
        tk.Label(row, text=desc, bg=BG_CARD, fg=GRAY,
                 font=FONT_XS).pack(side='left')

        if is_bool:
            var = tk.BooleanVar(value=bool(self.settings.get(key, False)))
        else:
            var = tk.BooleanVar(value=self.settings.get(key) == bool_val)
        self._vars[var_key] = var

        toggle = tk.Canvas(row, width=44, height=24, bg=BG_CARD,
                           highlightthickness=0, cursor='hand2')
        toggle.pack(side='right', padx=14, pady=10)
        self._draw_toggle(toggle, var.get())
        toggle.bind('<Button-1>', lambda e, t=toggle, v=var: self._click_toggle(t, v))

    def _draw_toggle(self, canvas: tk.Canvas, on: bool):
        canvas.delete('all')
        color = TEAL if on else BG_ELEV
        canvas.create_rounded_rect = None
        canvas.create_oval(0, 0, 44, 24, fill=color, outline='')
        x = 26 if on else 4
        canvas.create_oval(x, 3, x + 18, 21, fill=BLACK_T if on else GRAY, outline='')

    def _click_toggle(self, canvas, var):
        var.set(not var.get())
        self._draw_toggle(canvas, var.get())

    def _select_interval(self, val: int):
        self._vars['monitor_interval'].set(val)
        for v in [5, 10, 30]:
            btn = getattr(self, f'_interval_btn_{v}', None)
            if btn:
                btn.config(bg=ORANGE if v == val else BG_ELEV,
                           fg=BLACK_T if v == val else GRAY)

    def _save(self, _=None):
        s = dict(self.settings)
        for key in ('auto_monitor', 'auto_repair', 'flush_on_repair'):
            if key in self._vars:
                s[key] = bool(self._vars[key].get())
        s['monitor_interval'] = self._vars['monitor_interval'].get()
        if 'language_zh' in self._vars:
            s['language'] = 'zh' if self._vars['language_zh'].get() else 'en'
        core.save_settings(s)
        self.destroy()


# ── 日志窗口 ──────────────────────────────────────────
class LogWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('操作日志')
        self.geometry('480x400')
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()
        self._build()

    def _build(self):
        bar = tk.Frame(self, bg=BG_CARD, height=44)
        bar.pack(fill='x')
        bar.pack_propagate(False)
        tk.Label(bar, text='LOG_HISTORY', bg=BG_CARD, fg=WHITE,
                 font=FONT_H).place(x=16, rely=0.5, anchor='w')

        right = tk.Frame(bar, bg=BG_CARD)
        right.place(relx=1, x=-12, rely=0.5, anchor='e')

        clear = tk.Label(right, text='清除', bg=BG_ELEV, fg=GRAY,
                         font=FONT_XS, padx=10, pady=4, cursor='hand2')
        clear.pack(side='left', padx=4)
        clear.bind('<Button-1>', self._clear)

        close = tk.Label(right, text='✕', bg=BG_ELEV, fg=GRAY,
                         font=FONT_XS, padx=8, pady=4, cursor='hand2')
        close.pack(side='left')
        close.bind('<Button-1>', lambda e: self.destroy())

        # 日志列表
        frame = tk.Frame(self, bg=BG)
        frame.pack(fill='both', expand=True, padx=12, pady=8)

        scrollbar = tk.Scrollbar(frame, bg=BG_CARD, troughcolor=BG)
        scrollbar.pack(side='right', fill='y')

        self.listbox = tk.Listbox(
            frame, bg=BG_CARD, fg=WHITE, font=FONT_XS,
            selectbackground=BG_ELEV, relief='flat', bd=0,
            yscrollcommand=scrollbar.set, activestyle='none'
        )
        self.listbox.pack(fill='both', expand=True)
        scrollbar.config(command=self.listbox.yview)

        self._load_logs()

    def _load_logs(self):
        self.listbox.delete(0, 'end')
        logs = core.get_logs()
        if not logs:
            self.listbox.insert('end', '  // 暂无操作记录')
            self.listbox.itemconfig(0, fg=GRAY)
            return
        for entry in logs:
            action = entry.get('action', '').upper()
            adapter = entry.get('adapter', '')
            ts = entry.get('ts', '')
            success = entry.get('success', False)
            before_ips = entry.get('before_ips', [])
            ip_str = before_ips[0] if before_ips else ''
            status = 'OK' if success else 'FAIL'
            color = TEAL if success else RED
            text = f'  [{action}] {adapter}  {ip_str}→DHCP  {status}  {ts}'
            self.listbox.insert('end', text)
            self.listbox.itemconfig('end', fg=color)

    def _clear(self, _=None):
        if messagebox.askyesno('确认', '清除所有日志记录？', parent=self):
            core.clear_logs()
            self._load_logs()


# ── 入口 ──────────────────────────────────────────────
if __name__ == '__main__':
    if not core.is_admin():
        core.relaunch_as_admin()
    app = App()
    app.mainloop()
