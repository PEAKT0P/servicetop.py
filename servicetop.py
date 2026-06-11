#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================
   Servicetop OpenRC Manager v3.4.1 (Advanced Scroll Edition)
   Repository: https://github.com/PEAKT0P/servicetop.py
========================================================================
    Update/Install:
   $ sudo rm -f /opt/servicetop/lang.json /opt/servicetop/blacklist.list /opt/servicetop/favorites.list /opt/servicetop/priority.json
   $ sudo mkdir -p /opt/servicetop/
   $ sudo curl -o /opt/servicetop/servicetop.py https://raw.githubusercontent.com/PEAKT0P/servicetop.py/main/servicetop.py
   $ sudo chmod +x /opt/servicetop/servicetop.py
   $ sudo ln -sf /opt/servicetop/servicetop.py /usr/local/bin/servicetop
    Usage:
   $ sudo servicetop
========================================================================
"""

import curses
import subprocess
import os
import sys
import json
import re
import time

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Рабочая директория
BASE_DIR = "/opt/servicetop"
FAV_FILE = os.path.join(BASE_DIR, "favorites.list")
BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.list")
PRIO_FILE = os.path.join(BASE_DIR, "priority.json")
LANG_FILE = os.path.join(BASE_DIR, "lang.json")

# Регулярки для раскраски логов и очистки
TOKEN_RE = re.compile(r'(\[\s*ok\s*\]|\[\s*!!\s*\]|\[\s*fail\s*\]|Ошибка:|Успешно:|Выполняю:|\s\*\s)')
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

MAX_LOG_LINES = 500
log_messages = []

if os.geteuid() != 0:
    print("Ошибка: servicetop должен запускаться от root!")
    sys.exit(1)

os.makedirs(BASE_DIR, exist_ok=True)

DEFAULT_LANG_DATA = {
    "current_lang": "ru",
    "ru": {
        "title": " Servicetop (Gentoo/OpenRC) ",
        "top_title": " TOP-5 ПРОЦЕССОВ: ",
        "col_service": "СЕРВИС",
        "col_status": "СТАТУС",
        "col_autorun": "АВТОЗАПУСК",
        "log_title": "Лог действий:",
        "bottom_hint": " [ЛКМ] Меню [PgUp/Dn] Шаг 5 [F] Избранное [P] Приор. [B] Blacklist [L] Все [/] Поиск [G] Язык [I] Инфо [F10/Q] Выход ",
        "act_start": "Start (Запуск)",
        "act_stop": "Stop (Остановка)",
        "act_restart": "Restart (Перезапуск)",
        "act_zap": "ZAP (Сброс статуса)",
        "act_pid": "Удалить PID (Форс. очистка)",
        "act_add_auto": "Добавить в автозапуск ►",
        "act_del_auto": "Удалить из автозапуска ►",
        "act_cancel": "Отмена",
        "menu_title": " Управление: {} ",
        "msg_welcome": "Добро пожаловать в ServiceTop! Сбор данных завершен.",
        "msg_refresh": "Обновление списка сервисов...",
        "msg_exec": "Выполняю: {}",
        "msg_pid_del": "PID файлы для {} удалены.",
        "msg_fav": "Статус Избранного для {} изменен.",
        "msg_bl": "Статус Blacklist для {} изменен.",
        "msg_prio": "Приоритет {} изменен.",
        "msg_bl_mode": "Режим отображения Blacklist: {}",
        "err_small": "Окно терминала слишком маленькое!",
        "search_prompt": "Поиск:",
        "msg_lang_ru": "Язык переключен на Русский",
        "msg_lang_en": "Язык переключен на English",
        "warn_title": " ВНИМАНИЕ ",
        "warn_crit": "Остановка критического сервиса может\nнарушить работу системы.\nПродолжить?",
        "btn_yes": "[Y] Да",
        "btn_no": "[N] Нет",
        "info_title": " Информация: {} ",
        "info_status": "Статус: {}",
        "info_rl": "Runlevel: {}",
        "info_fav": "Избранное: {}",
        "info_bl": "Blacklist: {}",
        "info_prio": "Приоритет: {}",
        "info_pid": "PID: {}",
        "info_uptime": "Uptime: {}",
        "prio_high": "Высокий",
        "prio_norm": "Обычный",
        "prio_low": "Низкий",
        "yes": "Да",
        "no": "Нет",
        "shown": "Отображаются",
        "hidden": "Скрыты",
        "sys_info": "CPU: {}% | RAM: {} ({}%) | LOAD: {} | PROC: {}"
    },
    "en": {
        "title": " Servicetop (Gentoo/OpenRC) ",
        "top_title": " TOP-5 PROCESSES: ",
        "col_service": "SERVICE",
        "col_status": "STATUS",
        "col_autorun": "AUTOSTART",
        "log_title": "Activity log:",
        "bottom_hint": " [LMB] Menu [PgUp/Dn] Step 5 [F] Fav [P] Prio [B] Blacklist [L] All [/] Search [G] Lang [I] Info [F10/Q] Exit ",
        "act_start": "Start",
        "act_stop": "Stop",
        "act_restart": "Restart",
        "act_zap": "ZAP (Reset status)",
        "act_pid": "Delete PID (Force cleanup)",
        "act_add_auto": "Add to autostart ►",
        "act_del_auto": "Remove from autostart ►",
        "act_cancel": "Cancel",
        "menu_title": " Management: {} ",
        "msg_welcome": "Welcome to ServiceTop! Data collection completed.",
        "msg_refresh": "Refreshing service list...",
        "msg_exec": "Executing: {}",
        "msg_pid_del": "PID files for {} have been removed.",
        "msg_fav": "Favorite status for {} has been changed.",
        "msg_bl": "Blacklist status for {} has been changed.",
        "msg_prio": "Priority for {} has been changed.",
        "msg_bl_mode": "Blacklist display mode: {}",
        "err_small": "Terminal window is too small!",
        "search_prompt": "Search:",
        "msg_lang_ru": "Language switched to Russian",
        "msg_lang_en": "Language switched to English",
        "warn_title": " WARNING ",
        "warn_crit": "Stopping this critical service may\ndisrupt the system.\nContinue?",
        "btn_yes": "[Y] Yes",
        "btn_no": "[N] No",
        "info_title": " Info: {} ",
        "info_status": "Status: {}",
        "info_rl": "Runlevel: {}",
        "info_fav": "Favorite: {}",
        "info_bl": "Blacklist: {}",
        "info_prio": "Priority: {}",
        "info_pid": "PID: {}",
        "info_uptime": "Uptime: {}",
        "prio_high": "High",
        "prio_norm": "Normal",
        "prio_low": "Low",
        "yes": "Yes",
        "no": "No",
        "shown": "Shown",
        "hidden": "Hidden",
        "sys_info": "CPU: {}% | RAM: {} ({}%) | LOAD: {} | PROC: {}"
    }
}

L = {}

def load_language():
    global L
    if not os.path.exists(LANG_FILE):
        try:
            with open(LANG_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_LANG_DATA, f, indent=4, ensure_ascii=False)
        except: pass
        L = DEFAULT_LANG_DATA["ru"].copy()
        L["current_lang_code"] = "ru"
        return L
    try:
        with open(LANG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            lang = data.get("current_lang", "ru")
            L = data.get(lang, DEFAULT_LANG_DATA["ru"]).copy()
            L["current_lang_code"] = lang
            return L
    except:
        L = DEFAULT_LANG_DATA["ru"].copy()
        L["current_lang_code"] = "ru"
        return L

# Инициализация языка при старте
load_language()

def add_log(msg):
    """ Добавляет сообщение в лог, разбивая по строкам, и лимитирует размер. """
    global log_messages
    for line in msg.split('\n'):
        line = line.strip()
        if line:
            log_messages.append(line)

    if len(log_messages) > MAX_LOG_LINES:
        del log_messages[:len(log_messages) - MAX_LOG_LINES]

# --- Вспомогательные функции для работы с файлами ---
def get_list(filepath):
    if not os.path.exists(filepath): return set()
    try:
        with open(filepath, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except: return set()

def save_list(filepath, items):
    try:
        with open(filepath, 'w') as f:
            for item in sorted(list(items)): f.write(f"{item}\n")
    except: pass

def get_dict(filepath):
    if not os.path.exists(filepath): return {}
    try:
        with open(filepath, 'r') as f: return json.load(f)
    except: return {}

def save_dict(filepath, data):
    try:
        with open(filepath, 'w') as f: json.dump(data, f, indent=4)
    except: pass

# --- Системные функции ---
def get_sys_info():
    if HAS_PSUTIL:
        cpu = int(psutil.cpu_percent())
        mem = psutil.virtual_memory()
        ram_str = f"{mem.used/1024**3:.1f}G / {mem.total/1024**3:.1f}G"
        ram_pct = int(mem.percent)
        load = os.getloadavg()
        load_str = f"{load[0]:.2f} {load[1]:.2f} {load[2]:.2f}"
        procs = len(psutil.pids())
    else:
        cpu = 0
        load_str = "N/A"
        try:
            with open('/proc/loadavg') as f: load_str = ' '.join(f.read().split()[:3])
        except: pass

        total = free = buffers = cached = 0
        try:
            with open('/proc/meminfo') as f:
                for line in f:
                    if line.startswith("MemTotal:"): total = int(line.split()[1])
                    elif line.startswith("MemFree:"): free = int(line.split()[1])
                    elif line.startswith("Buffers:"): buffers = int(line.split()[1])
                    elif line.startswith("Cached:"): cached = int(line.split()[1])
            used = total - free - buffers - cached
            ram_pct = int((used / total) * 100) if total else 0
            ram_str = f"{used/1024**2:.1f}G / {total/1024**2:.1f}G"
        except:
            ram_str, ram_pct = "N/A", 0

        try:
            procs = len([pid for pid in os.listdir('/proc') if pid.isdigit()])
        except:
            procs = 0

    return cpu, ram_str, ram_pct, load_str, procs

def get_top_processes():
    try:
        out = subprocess.getoutput("ps -eo pid,pcpu,pmem,comm --sort=-pcpu | head -n 6").strip().split('\n')
        formatted = []
        formatted.append(f"{'PID'.ljust(8)} {'CPU%'.ljust(7)} {'MEM%'.ljust(7)} {'PROCESS'}")
        if len(out) > 1:
            for line in out[1:]:
                parts = line.strip().split(None, 3)
                if len(parts) == 4:
                    formatted.append(f"{parts[0].ljust(8)} {parts[1].ljust(7)} {parts[2].ljust(7)} {parts[3]}")
        return formatted
    except:
        return []

def get_services(favs, bl_set, prio_dict, show_blacklist):
    services = []
    status_out = subprocess.getoutput("rc-status -a").split('\n')
    status_map = {}
    for line in status_out:
        if '[' in line and ']' in line:
            parts = line.strip().split()
            if len(parts) >= 3:
                name = parts[0]
                try:
                    state_idx = parts.index('[') + 1
                    status_map[name] = parts[state_idx]
                except ValueError: pass

    rc_update_out = subprocess.getoutput("rc-update show").split('\n')
    runlevel_map = {}
    for line in rc_update_out:
        if '|' in line:
            parts = line.split('|')
            runlevel_map[parts[0].strip()] = parts[1].strip()

    for file in sorted(os.listdir('/etc/init.d/')):
        if file in ['functions.sh', 'net.lo'] or file.startswith('.'): continue
        filepath = os.path.join('/etc/init.d/', file)

        if os.path.isfile(filepath) and os.access(filepath, os.X_OK):
            is_fav = file in favs
            is_bl = file in bl_set
            prio = prio_dict.get(file, 0)

            # Пропускаем, если сервис в blacklist и режим отображения скрыт (но избранные показываем всегда)
            if is_bl and not show_blacklist and not is_fav:
                continue

            services.append({
                "name": file,
                "status": status_map.get(file, "stopped"),
                "runlevel": runlevel_map.get(file, ""),
                "is_fav": is_fav,
                "is_bl": is_bl,
                "priority": prio
            })

    # Сортировка: Избранное -> Приоритет(Высокий=1, Обычный=0, Низкий=-1) -> Имя
    services.sort(key=lambda x: (not x['is_fav'], -x['priority'], x['name']))
    return services

def fix_openrc_logs(text):
    """ Разделяет склеенные логи OpenRC на новые строки (напр: [ ok ] * samba...) """
    return re.sub(r'(\[\s*(?:ok|!!|fail)\s*\])\s*(?=\*)', r'\1\n', text)

def execute_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        output = result.stdout.strip() + " " + result.stderr.strip()
        output = ANSI_ESCAPE.sub('', output)
        output = fix_openrc_logs(output)
        return output if output else f"Успешно: {cmd}"
    except Exception as e:
        return f"Ошибка: {e}"

def draw_colorized_log(stdscr, y, x, msg, max_w):
    safe_msg = msg.replace('\n', '  ')
    if len(safe_msg) > max_w - 4:
        safe_msg = safe_msg[:max_w - 7] + "..."

    tokens = TOKEN_RE.split(safe_msg)
    curr_x = x
    for token in tokens:
        if not token: continue
        attr = curses.color_pair(6)
        if re.fullmatch(r'\[\s*ok\s*\]|Успешно:|\s\*\s', token): attr = curses.color_pair(1) | curses.A_BOLD
        elif re.fullmatch(r'\[\s*!!\s*\]|\[\s*fail\s*\]|Ошибка:', token): attr = curses.color_pair(2) | curses.A_BOLD
        elif re.fullmatch(r'Выполняю:', token): attr = curses.color_pair(4) | curses.A_BOLD

        try:
            stdscr.addstr(y, curr_x, token, attr)
            curr_x += len(token)
        except curses.error: break

def show_confirm_dialog(stdscr, svc_name):
    h, w = stdscr.getmaxyx()
    dh, dw = 7, 50
    dy, dx = (h - dh) // 2, (w - dw) // 2
    win = curses.newwin(dh, dw, dy, dx)
    win.keypad(True)
    win.bkgd(' ', curses.color_pair(2) | curses.A_BOLD)

    lines = L['warn_crit'].split('\n')
    while True:
        win.erase()
        win.box()
        win.addstr(1, 2, L['warn_title'].center(dw-4), curses.A_BOLD | curses.color_pair(5))
        for i, line in enumerate(lines):
            win.addstr(3+i, 2, line.center(dw-4))

        hint = f"{L['btn_yes']}     {L['btn_no']}"
        win.addstr(dh-2, (dw-len(hint))//2, hint, curses.A_BOLD)

        win.refresh()
        k = win.getch()
        if k in (ord('y'), ord('Y')): return True
        if k in (ord('n'), ord('N'), 27, 10, 13): return False
        if k == curses.KEY_MOUSE:
            try:
                curses.getmouse()
                return False
            except curses.error: pass

def show_info_panel(stdscr, svc):
    h, w = stdscr.getmaxyx()
    dh, dw = 11, 40
    dy, dx = (h - dh) // 2, (w - dw) // 2
    win = curses.newwin(dh, dw, dy, dx)
    win.keypad(True)
    win.bkgd(' ', curses.color_pair(5))

    pid = "N/A"
    uptime = "N/A"
    try:
        pid_file = f"/run/{svc['name']}.pid"
        if not os.path.exists(pid_file):
            pid_file = f"/var/run/{svc['name']}.pid"
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = f.read().strip()
        else:
            out = subprocess.getoutput(f"pidof {svc['name']}").split()
            if out: pid = out[0]

        if pid != "N/A" and pid.isdigit():
            ut_out = subprocess.getoutput(f"ps -p {pid} -o etime=")
            if ut_out and not ut_out.startswith('ps'):
                uptime = ut_out.strip()
    except: pass

    prio_map = {1: L['prio_high'], 0: L['prio_norm'], -1: L['prio_low']}

    while True:
        win.erase()
        win.box()
        win.addstr(1, 2, L['info_title'].format(svc['name'])[:dw-4], curses.A_BOLD)
        win.addstr(2, 2, "="*(dw-4))
        win.addstr(3, 2, L['info_status'].format(svc['status']))
        win.addstr(4, 2, L['info_rl'].format(svc['runlevel'] or '-'))
        win.addstr(5, 2, L['info_fav'].format(L['yes'] if svc['is_fav'] else L['no']))
        win.addstr(6, 2, L['info_bl'].format(L['yes'] if svc['is_bl'] else L['no']))
        win.addstr(7, 2, L['info_prio'].format(prio_map.get(svc['priority'], L['prio_norm'])))
        win.addstr(8, 2, L['info_pid'].format(pid))
        win.addstr(9, 2, L['info_uptime'].format(uptime))

        win.refresh()
        k = win.getch()
        if k in (27, 10, 13, ord('i'), ord('I')): break
        if k == curses.KEY_MOUSE:
            try:
                curses.getmouse()
                break
            except curses.error: pass

def show_action_menu(stdscr, service):
    h, w = stdscr.getmaxyx()
    menu_h, menu_w = 11, 54
    menu_y, menu_x = (h - menu_h) // 2, (w - menu_w) // 2

    win = curses.newwin(menu_h, menu_w, menu_y, menu_x)
    win.keypad(True)
    win.bkgd(' ', curses.color_pair(5))

    lbl_add = L.get('act_add_auto', 'Добавить в автозапуск').replace(' ►', '') + ' ►'
    lbl_del = L.get('act_del_auto', 'Удалить из автозапуска').replace(' ►', '') + ' ►'

    actions = [
        (L.get('act_start', 'Start'), "CMD", f"/etc/init.d/{service['name']} start"),
        (L.get('act_stop', 'Stop'), "CMD", f"/etc/init.d/{service['name']} stop"),
        (L.get('act_restart', 'Restart'), "CMD", f"/etc/init.d/{service['name']} restart"),
        (L.get('act_zap', 'ZAP'), "CMD", f"/etc/init.d/{service['name']} zap"),
        (L.get('act_pid', 'Удалить PID'), "PID", service['name']),
        (lbl_add, "SUBMENU", "add"),
        (lbl_del, "SUBMENU", "del"),
        (L.get('act_cancel', 'Отмена'), "CANCEL", "")
    ]

    sel_idx = 0
    in_submenu = False
    sub_idx = 0
    runlevels = ["default", "boot", "nonetwork", "shutdown", "sysinit"]

    BUTTON4 = getattr(curses, 'BUTTON4_PRESSED', 65536)
    BUTTON5 = getattr(curses, 'BUTTON5_PRESSED', 2097152)

    while True:
        win.erase()
        win.box()
        win.addstr(1, 2, L.get('menu_title', ' Управление: {} ').format(service['name']), curses.A_BOLD | curses.color_pair(5))
        win.addstr(2, 2, "="*(menu_w-4), curses.color_pair(5))

        for idx, (label, act_type, _) in enumerate(actions):
            if idx == sel_idx:
                attr = curses.color_pair(4) | curses.A_DIM if in_submenu else curses.color_pair(4)
            else:
                attr = curses.color_pair(5)

            win.addstr(3 + idx, 4, f" {label} ".ljust(menu_w-8), attr)

        win.refresh()

        sub_y, sub_x, sub_h, sub_w = 0, 0, 0, 0
        if in_submenu:
            sub_h = len(runlevels) + 2
            sub_w = 17
            sub_y = menu_y + 3 + sel_idx
            sub_x = menu_x + menu_w - 2

            if sub_y + sub_h > h: sub_y = h - sub_h
            if sub_x + sub_w > w: sub_x = w - sub_w

            sub_win = curses.newwin(sub_h, sub_w, sub_y, sub_x)
            sub_win.keypad(True)
            sub_win.bkgd(' ', curses.color_pair(5))
            sub_win.box()

            for i, rl in enumerate(runlevels):
                attr = curses.color_pair(4) if i == sub_idx else curses.color_pair(5)
                sub_win.addstr(1 + i, 2, f" {rl} ".ljust(sub_w-4), attr)

            sub_win.refresh()
            key = sub_win.getch()
        else:
            key = win.getch()

        if key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()

                if bstate & BUTTON4:
                    if in_submenu and sub_idx > 0: sub_idx -= 1
                    elif not in_submenu and sel_idx > 0: sel_idx -= 1
                elif bstate & BUTTON5:
                    if in_submenu and sub_idx < len(runlevels) - 1: sub_idx += 1
                    elif not in_submenu and sel_idx < len(actions) - 1: sel_idx += 1
                elif bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED | curses.BUTTON1_PRESSED):
                    if in_submenu:
                        if sub_y + 1 <= my < sub_y + 1 + len(runlevels) and sub_x <= mx <= sub_x + sub_w:
                            sub_idx = int(my - (sub_y + 1))
                            op = actions[sel_idx][2]
                            rl = runlevels[sub_idx]
                            return "CMD", f"rc-update {op} {service['name']} {rl}"
                        else:
                            in_submenu = False
                            stdscr.touchwin()
                            stdscr.refresh()
                    else:
                        if menu_y + 3 <= my < menu_y + 3 + len(actions) and menu_x <= mx <= menu_x + menu_w:
                            sel_idx = int(my - (menu_y + 3))
                            act_type = actions[sel_idx][1]
                            if act_type == "SUBMENU":
                                in_submenu = True
                                sub_idx = 0
                            elif act_type == "CANCEL":
                                return "CANCEL", ""
                            else:
                                return act_type, actions[sel_idx][2]
                        elif not (menu_y <= my <= menu_y + menu_h and menu_x <= mx <= menu_x + menu_w):
                            return "CANCEL", ""
            except curses.error:
                pass
            continue

        if in_submenu:
            if key == curses.KEY_UP and sub_idx > 0: sub_idx -= 1
            elif key == curses.KEY_DOWN and sub_idx < len(runlevels) - 1: sub_idx += 1
            elif key in (curses.KEY_LEFT, 27):
                in_submenu = False
                stdscr.touchwin()
                stdscr.refresh()
            elif key in [curses.KEY_ENTER, 10, 13]:
                op = actions[sel_idx][2]
                rl = runlevels[sub_idx]
                return "CMD", f"rc-update {op} {service['name']} {rl}"
        else:
            if key == curses.KEY_UP and sel_idx > 0: sel_idx -= 1
            elif key == curses.KEY_DOWN and sel_idx < len(actions) - 1: sel_idx += 1
            elif key == curses.KEY_RIGHT and actions[sel_idx][1] == "SUBMENU":
                in_submenu = True
                sub_idx = 0
            elif key in [curses.KEY_ENTER, 10, 13]:
                act_type = actions[sel_idx][1]
                if act_type == "SUBMENU":
                    op = actions[sel_idx][2]
                    return "CMD", f"rc-update {op} {service['name']} default"
                else:
                    return act_type, actions[sel_idx][2]
            elif key == 27:
                return "CANCEL", ""

def main(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.timeout(2000)

    BUTTON4 = getattr(curses, 'BUTTON4_PRESSED', 65536)
    BUTTON5 = getattr(curses, 'BUTTON5_PRESSED', 2097152)
    curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION | BUTTON4 | BUTTON5)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(6, curses.COLOR_WHITE, -1)
    curses.init_pair(7, curses.COLOR_MAGENTA, -1)
    curses.init_pair(8, curses.COLOR_YELLOW, curses.COLOR_BLUE)

    favs = get_list(FAV_FILE)
    bl_set = get_list(BLACKLIST_FILE)
    prio_dict = get_dict(PRIO_FILE)

    show_blacklist = False
    services = get_services(favs, bl_set, prio_dict, show_blacklist)
    sel_idx = 0
    add_log(L['msg_welcome'])

    top_procs_cache = get_top_processes()
    sys_info_cache = get_sys_info()
    last_top_update = time.time()

    pending_action = None
    pending_payload = None

    in_search = False
    search_query = ""

    CRITICAL_SERVICES = ["sshd", "network"]

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        max_w = w - 1

        if h < 24 or max_w < 70:
            stdscr.addstr(0, 0, L['err_small'])
            stdscr.refresh()
            stdscr.getch()
            break

        display_services = [s for s in services if search_query.lower() in s['name'].lower()]
        if sel_idx >= len(display_services): sel_idx = max(0, len(display_services) - 1)

        # Заголовок
        stdscr.addstr(0, 0, L['title'].center(max_w), curses.color_pair(4) | curses.A_BOLD)
        stdscr.addstr(1, 0, "-" * max_w)

        # TOP процессов и Мониторинг
        show_top = h >= 32
        list_start_y = 3
        if show_top:
            cpu, ram_str, ram_pct, load_str, procs = sys_info_cache
            sys_info_text = L['sys_info'].format(cpu, ram_str, ram_pct, load_str, procs)
            stdscr.addstr(2, 2, sys_info_text, curses.A_BOLD | curses.color_pair(3))

            stdscr.addstr(4, 2, L['top_title'], curses.A_BOLD | curses.color_pair(6))
            for idx, proc in enumerate(top_procs_cache):
                attr = curses.color_pair(4) | curses.A_BOLD if idx == 0 else curses.color_pair(6)
                stdscr.addstr(5 + idx, 4, proc[:max_w-8], attr)
            stdscr.addstr(11, 0, "-" * max_w)
            list_start_y = 12

        # Заголовки таблицы
        col_count = 2 if max_w >= 135 else 1
        col_w = max_w // col_count
        header_str = f"{L['col_service'].ljust(32)} {L['col_status'].ljust(15)} {L['col_autorun']}"

        if col_count == 2:
            stdscr.addstr(list_start_y, 2, header_str[:col_w - 4], curses.A_BOLD)
            stdscr.addstr(list_start_y, 2 + col_w, header_str[:col_w - 4], curses.A_BOLD)
        else:
            stdscr.addstr(list_start_y, 2, header_str, curses.A_BOLD)

        stdscr.addstr(list_start_y + 1, 0, "-" * max_w)

        # Расчет размеров
        log_lines_count = 8 if h >= 28 else 6
        bottom_h = log_lines_count + 3
        actual_list_start = list_start_y + 2
        list_h = h - actual_list_start - bottom_h
        items_per_page = list_h * col_count

        current_page = sel_idx // items_per_page
        scroll_offset = current_page * items_per_page

        # Отрисовка сервисов
        for i in range(items_per_page):
            idx = scroll_offset + i
            if idx >= len(display_services): break
            svc = display_services[idx]

            row_idx = i % list_h if col_count == 2 else i
            col_idx = i // list_h if col_count == 2 else 0
            y = actual_list_start + row_idx
            x_offset = col_idx * col_w

            status_color = curses.color_pair(6)
            if "started" in svc['status']: status_color = curses.color_pair(1)
            elif "crashed" in svc['status']: status_color = curses.color_pair(3)
            elif "stopped" in svc['status']: status_color = curses.color_pair(2)

            prefix = "   "
            name_color = curses.color_pair(6)
            prefix_color = name_color

            if svc['is_fav'] and svc['priority'] == 1:
                prefix = "[★]"
                prefix_color = curses.color_pair(8) | curses.A_BOLD
                name_color = curses.color_pair(3) | curses.A_BOLD
            elif svc['is_fav']:
                prefix = "[★]"
                name_color = curses.color_pair(3) | curses.A_BOLD
                prefix_color = name_color
            elif svc['is_bl']:
                prefix = "[B]"
                name_color = curses.color_pair(6) | curses.A_DIM
                prefix_color = name_color
            elif svc['priority'] == 1:
                prefix = "[↑]"
                name_color = curses.color_pair(4) | curses.A_BOLD
                prefix_color = name_color
            elif svc['priority'] == -1:
                prefix = "[↓]"
                name_color = curses.color_pair(6) | curses.A_DIM
                prefix_color = name_color

            safe_status = svc['status'][:13]
            safe_runlevel = svc['runlevel'][:15]

            if idx == sel_idx:
                stdscr.addstr(y, x_offset, " " * (col_w - 1), curses.color_pair(4) | curses.A_REVERSE)
                safe_name = f"{prefix} {svc['name']}"[:32]
                stdscr.addstr(y, x_offset + 2, safe_name.ljust(32), curses.color_pair(4) | curses.A_REVERSE | curses.A_BOLD)
                stdscr.addstr(y, x_offset + 35, safe_status.ljust(15), curses.color_pair(4) | curses.A_REVERSE)
                stdscr.addstr(y, x_offset + 51, safe_runlevel, curses.color_pair(4) | curses.A_REVERSE)
            else:
                stdscr.addstr(y, x_offset + 2, prefix, prefix_color)
                space_left = 32 - len(prefix) - 1
                safe_name_only = svc['name'][:space_left]
                stdscr.addstr(y, x_offset + 2 + len(prefix) + 1, safe_name_only.ljust(space_left), name_color)
                stdscr.addstr(y, x_offset + 35, safe_status.ljust(15), status_color | curses.A_BOLD)
                stdscr.addstr(y, x_offset + 51, safe_runlevel, curses.color_pair(3))

        # Окно логов
        stdscr.addstr(h - bottom_h, 0, "-" * max_w)
        bl_ind = f" ({L['shown']})" if show_blacklist else ""
        stdscr.addstr(h - bottom_h + 1, 2, L['log_title'] + bl_ind, curses.A_BOLD | curses.color_pair(6))

        for idx, log_msg in enumerate(log_messages[-log_lines_count:]):
            draw_colorized_log(stdscr, h - bottom_h + 2 + idx, 2, log_msg, max_w)

        # Подсказки и строка поиска
        try:
            if in_search:
                prompt = f"{L['search_prompt']} {search_query}█"
                stdscr.addstr(h - 1, 0, prompt.ljust(max_w), curses.color_pair(4) | curses.A_REVERSE | curses.A_BOLD)
            else:
                if search_query:
                    hint = f"{L['search_prompt']} '{search_query}' " + L['bottom_hint']
                    stdscr.addstr(h - 1, 0, hint[:max_w].center(max_w), curses.color_pair(4))
                else:
                    stdscr.addstr(h - 1, 0, L['bottom_hint'][:max_w].center(max_w), curses.color_pair(4))
        except curses.error: pass

        stdscr.refresh()

        if pending_action:
            if pending_action == "CMD":
                is_crit = False
                if any(act in pending_payload for act in [" stop", " restart", " zap"]):
                    parts = pending_payload.split()
                    svc_name = parts[2] if "rc-update" in pending_payload else os.path.basename(parts[0])
                    if svc_name in CRITICAL_SERVICES or svc_name.startswith("net."):
                        is_crit = True

                if is_crit:
                    if not show_confirm_dialog(stdscr, svc_name):
                        pending_action = None
                        pending_payload = None
                        continue

                add_log(L['msg_exec'].format(pending_payload))
                res = execute_command(pending_payload)
                add_log(res)
            elif pending_action == "PID":
                cmds = [
                    f"rm -f /run/{pending_payload}.pid",
                    f"rm -f /var/run/{pending_payload}.pid",
                    f"rm -rf /run/openrc/daemons/{pending_payload}"
                ]
                execute_command("; ".join(cmds))
                add_log(L['msg_pid_del'].format(pending_payload))

            pending_action = None
            pending_payload = None
            services = get_services(favs, bl_set, prio_dict, show_blacklist)
            continue

        key = stdscr.getch()

        current_time = time.time()
        if current_time - last_top_update > 2.0:
            top_procs_cache = get_top_processes()
            sys_info_cache = get_sys_info()
            last_top_update = current_time

        if key == -1: continue

        # --- Обработка ввода (Поиск) ---
        if in_search:
            if key == 27:
                in_search = False
                search_query = ""
                sel_idx = 0
            elif key in (10, 13):
                in_search = False
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                search_query = search_query[:-1]
                sel_idx = 0
            elif 32 <= key <= 126:
                search_query += chr(key)
                sel_idx = 0
            continue
        else:
            if key == ord('/'):
                in_search = True
                continue

        # --- Основная обработка горячих клавиш ---
        if key in (ord('q'), ord('Q'), curses.KEY_F10): break
        elif key == curses.KEY_UP and sel_idx > 0: sel_idx -= 1
        elif key == curses.KEY_DOWN and sel_idx < len(display_services) - 1: sel_idx += 1
        elif key == curses.KEY_NPAGE: sel_idx = min(len(display_services) - 1, sel_idx + 5)
        elif key == curses.KEY_PPAGE: sel_idx = max(0, sel_idx - 5)

        elif key in (ord('r'), ord('R')):
            add_log(L['msg_refresh'])
            services = get_services(favs, bl_set, prio_dict, show_blacklist)

        elif key in (ord('i'), ord('I')):
            if display_services:
                show_info_panel(stdscr, display_services[sel_idx])

        elif key in (ord('g'), ord('G')):
            current_code = L.get("current_lang_code", "ru")
            new_lang = "en" if current_code == "ru" else "ru"
            full_data = get_dict(LANG_FILE) if os.path.exists(LANG_FILE) else DEFAULT_LANG_DATA.copy()
            full_data["current_lang"] = new_lang
            save_dict(LANG_FILE, full_data)
            load_language()
            msg = L.get(f'msg_lang_{new_lang}', f'Language switched to {new_lang}')
            add_log(msg)

        elif key in (ord('l'), ord('L')):
            show_blacklist = not show_blacklist
            status_txt = L['shown'] if show_blacklist else L['hidden']
            add_log(L['msg_bl_mode'].format(status_txt))
            services = get_services(favs, bl_set, prio_dict, show_blacklist)
            sel_idx = min(sel_idx, max(0, len(services) - 1))

        elif key in (ord('b'), ord('B')):
            if display_services:
                svc_name = display_services[sel_idx]['name']
                if svc_name in bl_set: bl_set.discard(svc_name)
                else: bl_set.add(svc_name)
                save_list(BLACKLIST_FILE, bl_set)
                add_log(L['msg_bl'].format(svc_name))
                services = get_services(favs, bl_set, prio_dict, show_blacklist)

        elif key in (ord('p'), ord('P')):
            if display_services:
                svc_name = display_services[sel_idx]['name']
                curr_prio = prio_dict.get(svc_name, 0)
                new_prio = 1 if curr_prio == 0 else 0

                if new_prio == 0 and svc_name in prio_dict: del prio_dict[svc_name]
                else: prio_dict[svc_name] = new_prio

                save_dict(PRIO_FILE, prio_dict)
                add_log(L['msg_prio'].format(svc_name))
                services = get_services(favs, bl_set, prio_dict, show_blacklist)

        elif key in (ord('f'), ord('F')):
            if display_services:
                svc_name = display_services[sel_idx]['name']
                if svc_name in favs: favs.discard(svc_name)
                else: favs.add(svc_name)
                save_list(FAV_FILE, favs)
                add_log(L['msg_fav'].format(svc_name))
                services = get_services(favs, bl_set, prio_dict, show_blacklist)

        elif key in [curses.KEY_ENTER, 10, 13]:
            if not display_services: continue
            action_type, payload = show_action_menu(stdscr, display_services[sel_idx])
            if action_type in ("CMD", "PID"):
                pending_action, pending_payload = action_type, payload

        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()

                if bstate & BUTTON4:
                    if sel_idx > 0: sel_idx -= 1
                elif bstate & BUTTON5:
                    if sel_idx < len(display_services) - 1: sel_idx += 1
                elif actual_list_start <= my < actual_list_start + list_h:
                    row = my - actual_list_start
                    col = mx // col_w
                    if col < col_count:
                        clicked_idx = scroll_offset + (col * list_h) + row if col_count == 2 else scroll_offset + row
                        if clicked_idx < len(display_services):
                            if sel_idx != clicked_idx:
                                sel_idx = clicked_idx
                            elif bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED | curses.BUTTON1_PRESSED):
                                action_type, payload = show_action_menu(stdscr, display_services[sel_idx])
                                if action_type in ("CMD", "PID"):
                                    pending_action, pending_payload = action_type, payload
            except curses.error: pass

if __name__ == "__main__":
    curses.wrapper(main)
