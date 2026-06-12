#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================
   Servicetop OpenRC Manager v3.6 RC (Optimized Edition)
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
import shlex
import shutil

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Настройки
TOP_COUNT = 5

# Рабочая директория
BASE_DIR = "/opt/servicetop"
FAV_FILE = os.path.join(BASE_DIR, "favorites.list")
BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.list")
PRIO_FILE = os.path.join(BASE_DIR, "priority.json")
LANG_FILE = os.path.join(BASE_DIR, "lang.json")

# Регулярки для раскраски логов и очистки (добавлены английские версии)
TOKEN_RE = re.compile(r'(\[\s*ok\s*\]|\[\s*!!\s*\]|\[\s*fail\s*\]|Ошибка:|Успешно:|Выполняю:|Error:|Success:|Executing:|\s\*\s)')
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
        "bottom_hint": " [ЛКМ] Меню [PgUp/Dn] Шаг [F] Избранное [P] Приор. [B] Blacklist [L] Все [/] Поиск [G] Язык [I] Инфо [F10/Q] Выход ",
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
        "msg_success": "Успешно: {}",
        "msg_error": "Ошибка: {}",
        "msg_pid_del": "PID файлы для {} удалены.",
        "msg_fav": "Статус Избранного для {} изменен.",
        "msg_bl": "Статус Blacklist для {} изменен.",
        "msg_prio": "Приоритет {} изменен.",
        "msg_bl_mode": "Режим отображения Blacklist: {}",
        "err_small": "Окно терминала слишком маленькое!",
        "search_prompt": "Поиск:",
        "msg_lang_ru": "Язык переключен на Русский",
        "msg_lang_en": "Language switched to English",
        "warn_title": " ВНИМАНИЕ ",
        "warn_crit": "Отключение критического сервиса может\nнарушить работу системы.\nПродолжить?",
        "btn_yes": "[Y/Д] Да",
        "btn_no": "[N/Н] Нет",
        "info_title": " Информация: {} ",
        "info_status": "Статус: {}",
        "info_rl": "Runlevel: {}",
        "info_fav": "Избранное: {}",
        "info_bl": "Blacklist: {}",
        "info_prio": "Приоритет: {}",
        "info_pid": "PID: {}",
        "info_uptime": "Uptime: {}",
        "info_cpu": "CPU процесса: {}",
        "info_mem": "Память процесса: {}",
        "info_path": "Путь к скрипту: {}",
        "info_deps": "Зависимости: {}",
        "info_desc": "Описание: {}",
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
        "bottom_hint": " [LMB] Menu [PgUp/Dn] Step [F] Fav [P] Prio [B] Blacklist [L] All [/] Search [G] Lang [I] Info [F10/Q] Exit ",
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
        "msg_success": "Success: {}",
        "msg_error": "Error: {}",
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
        "warn_crit": "Disabling this critical service may\ndisrupt the system.\nContinue?",
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
        "info_cpu": "Process CPU: {}",
        "info_mem": "Process Memory: {}",
        "info_path": "Script Path: {}",
        "info_deps": "Dependencies: {}",
        "info_desc": "Description: {}",
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
        except Exception as e:
            log_messages.append(f"Error creating lang.json: {e}")
        L = DEFAULT_LANG_DATA["ru"].copy()
        L["current_lang_code"] = "en"
        return L
    try:
        with open(LANG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            lang = data.get("current_lang", "en")
            L = data.get(lang, DEFAULT_LANG_DATA["ru"]).copy()
            L["current_lang_code"] = lang
            return L
    except Exception as e:
        log_messages.append(f"Error reading lang.json: {e}")
        L = DEFAULT_LANG_DATA["en"].copy()
        L["current_lang_code"] = "en"
        return L

load_language()

def safe_addstr(win, y, x, text, attr=None):
    try:
        if attr is not None:
            win.addstr(y, x, text, attr)
        else:
            win.addstr(y, x, text)
    except curses.error:
        pass

def add_log(msg):
    global log_messages
    for line in msg.split('\n'):
        line = line.strip()
        if line:
            log_messages.append(line)
    if len(log_messages) > MAX_LOG_LINES:
        del log_messages[:len(log_messages) - MAX_LOG_LINES]

def get_list(filepath):
    if not os.path.exists(filepath): return set()
    try:
        with open(filepath, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except Exception as e:
        log_messages.append(f"Error reading list {filepath}: {e}")
        return set()

def save_list(filepath, items):
    try:
        with open(filepath, 'w') as f:
            for item in sorted(list(items)): f.write(f"{item}\n")
    except Exception as e:
        log_messages.append(f"Error saving list {filepath}: {e}")

def get_dict(filepath):
    if not os.path.exists(filepath): return {}
    try:
        with open(filepath, 'r') as f: return json.load(f)
    except Exception as e:
        log_messages.append(f"Error reading dict {filepath}: {e}")
        return {}

def save_dict(filepath, data):
    try:
        with open(filepath, 'w') as f: json.dump(data, f, indent=4)
    except Exception as e:
        log_messages.append(f"Error saving dict {filepath}: {e}")

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
        out = subprocess.getoutput("ps -eo pid,pcpu,pmem,comm --sort=-pcpu | head -n " + str(TOP_COUNT + 1)).strip().split('\n')
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

def find_service_pid(svc_name):
    paths = [
        f"/run/openrc/daemons/{svc_name}/pid",
        f"/run/{svc_name}.pid",
        f"/var/run/{svc_name}.pid",
        f"/run/{svc_name}/{svc_name}.pid",
        f"/var/run/{svc_name}/{svc_name}.pid"
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, 'r') as f:
                    pid_str = f.read().strip()
                    if pid_str.isdigit(): return pid_str
            except: pass

    out = subprocess.getoutput(f"pidof {svc_name}").split()
    if out and out[0].isdigit(): return out[0]

    if HAS_PSUTIL:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == svc_name: return str(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    return "N/A"

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

            if is_bl and not show_blacklist and not is_fav and prio == 0:
                continue

            services.append({
                "name": file,
                "status": status_map.get(file, "stopped"),
                "runlevel": runlevel_map.get(file, ""),
                "is_fav": is_fav,
                "is_bl": is_bl,
                "priority": prio
            })

    services.sort(key=lambda x: (not x['is_fav'], -x['priority'], x['name']))
    return services

def fix_openrc_logs(text):
    return re.sub(r'(\[\s*(?:ok|!!|fail)\s*\])\s*(?=\*)', r'\1\n', text)

def execute_command(cmd):
    try:
        if isinstance(cmd, str):
            args = shlex.split(cmd)
        else:
            args = cmd
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        output = result.stdout.strip() + " " + result.stderr.strip()
        output = ANSI_ESCAPE.sub('', output)
        output = fix_openrc_logs(output)
        success_prefix = L.get('msg_success', 'Success: {}').format(' '.join(args))
        return output if output.strip() else success_prefix
    except Exception as e:
        return L.get('msg_error', 'Error: {}').format(e)

def draw_colorized_log(stdscr, y, x, msg, max_w):
    safe_msg = msg.replace('\n', '  ')
    if len(safe_msg) > max_w - 4:
        safe_msg = safe_msg[:max_w - 7] + "..."

    tokens = TOKEN_RE.split(safe_msg)
    curr_x = x
    for token in tokens:
        if not token: continue
        attr = curses.color_pair(6)
        if re.fullmatch(r'\[\s*ok\s*\]|Успешно:|Success:|\s\*\s', token): attr = curses.color_pair(1) | curses.A_BOLD
        elif re.fullmatch(r'\[\s*!!\s*\]|\[\s*fail\s*\]|Ошибка:|Error:', token): attr = curses.color_pair(2) | curses.A_BOLD
        elif re.fullmatch(r'Выполняю:|Executing:', token): attr = curses.color_pair(4) | curses.A_BOLD

        try:
            stdscr.addstr(y, curr_x, token, attr)
            curr_x += len(token)
        except curses.error: break

def show_confirm_dialog(stdscr, svc_name):
    h, w = stdscr.getmaxyx()
    dh = min(7, h - 2)
    dw = min(50, w - 2)
    dy, dx = max(0, (h - dh) // 2), max(0, (w - dw) // 2)

    win = curses.newwin(dh, dw, dy, dx)
    win.keypad(True)
    win.bkgd(' ', curses.color_pair(2) | curses.A_BOLD)

    lines = L['warn_crit'].split('\n')
    while True:
        win.erase()
        win.box()
        safe_addstr(win, 1, 2, L['warn_title'].center(dw-4)[:dw-4], curses.A_BOLD | curses.color_pair(5))
        for i, line in enumerate(lines):
            if 3 + i < dh - 2:
                safe_addstr(win, 3+i, 2, line.center(dw-4)[:dw-4])

        hint = f"{L['btn_yes']}   {L['btn_no']}"
        safe_addstr(win, dh-2, (dw-len(hint))//2, hint[:dw-4], curses.A_BOLD)

        win.refresh()

        try:
            k = win.get_wch()
        except curses.error:
            continue

        if isinstance(k, str):
            kl = k.lower()
            if kl in ('y', 'д'): return True
            if kl in ('n', 'н', '\x1b', '\n', '\r'): return False
        else:
            if k in (curses.KEY_ENTER, 10, 13, 27): return False
            if k == curses.KEY_MOUSE:
                try:
                    curses.getmouse()
                    return False
                except curses.error: pass

def show_info_panel(stdscr, svc):
    h, w = stdscr.getmaxyx()
    dh = min(17, h - 2)
    dw = min(65, w - 2)
    dy, dx = max(0, (h - dh) // 2), max(0, (w - dw) // 2)

    win = curses.newwin(dh, dw, dy, dx)
    win.keypad(True)
    win.bkgd(' ', curses.color_pair(5))

    svc_name = svc['name']
    pid = find_service_pid(svc_name)
    uptime = "N/A"
    p_cpu = "N/A"
    p_mem = "N/A"

    if pid != "N/A" and pid.isdigit():
        ut_out = subprocess.getoutput(f"ps -p {pid} -o etime=")
        if ut_out and not ut_out.startswith('ps'):
            uptime = ut_out.strip()

        if HAS_PSUTIL:
            try:
                p = psutil.Process(int(pid))
                p.cpu_percent(interval=None)
                time.sleep(0.1)
                p_cpu = f"{p.cpu_percent(interval=None)}%"
                p_mem = f"{p.memory_info().rss / 1024 / 1024:.1f} MB"
            except: pass

        if p_cpu == "N/A":
            ps_out = subprocess.getoutput(f"ps -p {pid} -o %cpu,%mem,rss= 2>/dev/null").strip().splitlines()
            if len(ps_out) > 1:
                parts = ps_out[1].split()
                if len(parts) >= 3:
                    p_cpu = f"{parts[0]}%"
                    p_mem = f"{float(parts[2])/1024:.1f} MB"

    prio_map = {1: L['prio_high'], 0: L['prio_norm'], -1: L['prio_low']}
    init_path = f"/etc/init.d/{svc_name}"

    desc = subprocess.getoutput(f"{init_path} describe 2>/dev/null").strip()
    if not desc or "unknown" in desc.lower() or desc.startswith("Usage:"):
        try:
            with open(init_path, "r", encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if "description=" in line:
                        desc = line.split("description=")[1].strip().strip('"').strip("'")
                        break
        except: pass
    if not desc or desc.startswith("Usage:"): desc = "-"

    depend_out = subprocess.getoutput(f"{init_path} depend 2>/dev/null").strip()
    deps = " | ".join(depend_out.splitlines()) if depend_out else "-"

    while True:
        win.erase()
        win.box()
        safe_addstr(win, 1, 2, L['info_title'].format(svc_name)[:dw-4], curses.A_BOLD)
        safe_addstr(win, 2, 2, "="*(dw-4))

        info_lines = [
            L['info_status'].format(svc['status']),
            L['info_rl'].format(svc['runlevel'] or '-'),
            L['info_fav'].format(L['yes'] if svc['is_fav'] else L['no']),
            L['info_bl'].format(L['yes'] if svc['is_bl'] else L['no']),
            L['info_prio'].format(prio_map.get(svc['priority'], L['prio_norm'])),
            L['info_pid'].format(pid),
            L['info_uptime'].format(uptime),
            L.get('info_cpu', 'Process CPU: {}').format(p_cpu),
            L.get('info_mem', 'Process Memory: {}').format(p_mem),
            L.get('info_path', 'Script Path: {}').format(init_path),
            L.get('info_desc', 'Description: {}').format(desc),
            L.get('info_deps', 'Dependencies: {}').format(deps)
        ]

        for i, text in enumerate(info_lines):
            if i + 3 < dh - 1:
                safe_addstr(win, i + 3, 2, text[:dw-4])

        win.refresh()
        try:
            k = win.get_wch()
        except curses.error:
            continue

        is_esc_enter = (isinstance(k, str) and k in ('\n', '\r', '\x1b')) or (isinstance(k, int) and k in (curses.KEY_ENTER, 10, 13, 27))
        if is_esc_enter or (isinstance(k, str) and k.lower() in ('i', 'ш')): break
        if isinstance(k, int) and k == curses.KEY_MOUSE:
            try:
                curses.getmouse()
                break
            except curses.error: pass

def show_action_menu(stdscr, service):
    h, w = stdscr.getmaxyx()

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

    menu_h = min(len(actions) + 4, h - 2)
    menu_w = min(54, w - 2)
    menu_y, menu_x = max(0, (h - menu_h) // 2), max(0, (w - menu_w) // 2)

    win = curses.newwin(menu_h, menu_w, menu_y, menu_x)
    win.keypad(True)
    win.bkgd(' ', curses.color_pair(5))

    sel_idx = 0
    in_submenu = False
    sub_idx = 0
    runlevels = ["default", "boot", "nonetwork", "shutdown", "sysinit"]

    BUTTON4 = getattr(curses, 'BUTTON4_PRESSED', 65536)
    BUTTON5 = getattr(curses, 'BUTTON5_PRESSED', 2097152)

    while True:
        win.erase()
        win.box()
        title_text = L.get('menu_title', ' Управление: {} ').format(service['name'])
        safe_addstr(win, 1, 2, title_text[:menu_w-4], curses.A_BOLD | curses.color_pair(5))
        safe_addstr(win, 2, 2, "="*(menu_w-4), curses.color_pair(5))

        for idx, (label, act_type, _) in enumerate(actions):
            if idx + 3 >= menu_h - 1: break
            if idx == sel_idx:
                attr = curses.color_pair(4) | curses.A_DIM if in_submenu else curses.color_pair(4)
            else:
                attr = curses.color_pair(5)

            safe_label = f" {label} "[:menu_w-8]
            safe_addstr(win, 3 + idx, 4, safe_label.ljust(menu_w-8), attr)

        win.refresh()

        sub_y, sub_x, sub_h, sub_w = 0, 0, 0, 0
        if in_submenu:
            sub_h = min(len(runlevels) + 2, h - 2)
            sub_w = min(17, w - 2)
            sub_y = menu_y + 3 + sel_idx
            sub_x = menu_x + menu_w - 2

            if sub_y + sub_h > h: sub_y = h - sub_h
            if sub_x + sub_w > w: sub_x = w - sub_w

            sub_win = curses.newwin(sub_h, sub_w, sub_y, sub_x)
            sub_win.keypad(True)
            sub_win.bkgd(' ', curses.color_pair(5))
            sub_win.box()

            for i, rl in enumerate(runlevels):
                if 1 + i >= sub_h - 1: break
                attr = curses.color_pair(4) if i == sub_idx else curses.color_pair(5)
                safe_addstr(sub_win, 1 + i, 2, f" {rl} "[:sub_w-4].ljust(sub_w-4), attr)

            sub_win.refresh()
            try:
                key = sub_win.get_wch()
            except curses.error:
                continue
        else:
            try:
                key = win.get_wch()
            except curses.error:
                continue

        is_enter = (isinstance(key, str) and key in ('\n', '\r')) or (isinstance(key, int) and key in (curses.KEY_ENTER, 10, 13))
        is_esc = (isinstance(key, str) and key == '\x1b') or (isinstance(key, int) and key == 27)

        max_visible_idx = min(len(actions), menu_h - 4)

        if isinstance(key, int) and key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()

                if bstate & BUTTON4:
                    if in_submenu and sub_idx > 0: sub_idx -= 1
                    elif not in_submenu and sel_idx > 0: sel_idx -= 1
                elif bstate & BUTTON5:
                    if in_submenu and sub_idx < len(runlevels) - 1: sub_idx += 1
                    elif not in_submenu and sel_idx < max_visible_idx - 1: sel_idx += 1
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
                        if menu_y + 3 <= my < menu_y + 3 + max_visible_idx and menu_x <= mx <= menu_x + menu_w:
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
            if isinstance(key, int) and key == curses.KEY_UP and sub_idx > 0: sub_idx -= 1
            elif isinstance(key, int) and key == curses.KEY_DOWN and sub_idx < len(runlevels) - 1: sub_idx += 1
            elif (isinstance(key, int) and key == curses.KEY_LEFT) or is_esc:
                in_submenu = False
                stdscr.touchwin()
                stdscr.refresh()
            elif is_enter:
                op = actions[sel_idx][2]
                rl = runlevels[sub_idx]
                return "CMD", f"rc-update {op} {service['name']} {rl}"
        else:
            if isinstance(key, int) and key == curses.KEY_UP and sel_idx > 0: sel_idx -= 1
            elif isinstance(key, int) and key == curses.KEY_DOWN and sel_idx < max_visible_idx - 1: sel_idx += 1
            elif isinstance(key, int) and key == curses.KEY_RIGHT and actions[sel_idx][1] == "SUBMENU":
                in_submenu = True
                sub_idx = 0
            elif is_enter:
                act_type = actions[sel_idx][1]
                if act_type == "SUBMENU":
                    op = actions[sel_idx][2]
                    return "CMD", f"rc-update {op} {service['name']} default"
                else:
                    return act_type, actions[sel_idx][2]
            elif is_esc:
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

    CRITICAL_SERVICES = [
        "sshd", "network", "netmount", "net.lo", "net.br0",
        "iptables", "iptables-manager", "nftables", "ufw", "firewalld",
        "dnsmasq", "docker", "containerd", "tailscaled", "kubelet",
        "podman", "libvirtd", "keepalived", "bird", "wireguard", "wg-quick",
        "dbus", "elogind", "syslog-ng", "rsyslog", "chronyd", "ntpd",
        "udev", "udev-trigger", "devfs", "localmount", "root", "sysfs"
    ]

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        max_w = w - 1

        if h < 10 or max_w < 34:
            safe_addstr(stdscr, 0, 0, L['err_small'][:max_w])
            stdscr.refresh()
            stdscr.getch()
            break

        display_services = [s for s in services if search_query.lower() in s['name'].lower()]
        if sel_idx >= len(display_services): sel_idx = max(0, len(display_services) - 1)

        safe_addstr(stdscr, 0, 0, L['title'].center(max_w)[:max_w], curses.color_pair(4) | curses.A_BOLD)
        safe_addstr(stdscr, 1, 0, "-" * max_w)

        show_top = h >= 26 and max_w >= 50
        show_sysinfo = h >= 14

        list_start_y = 2
        cpu, ram_str, ram_pct, load_str, procs = sys_info_cache

        if max_w >= 85:
            sys_info_text = L['sys_info'].format(cpu, ram_str, ram_pct, load_str, procs)
        elif max_w >= 50:
            sys_info_text = f"CPU: {cpu}% | RAM: {ram_pct}% ({ram_str}) | LOAD: {load_str}"
        else:
            sys_info_text = f"C: {cpu}% R: {ram_pct}% L: {load_str.split()[0]}"

        if show_sysinfo and show_top:
            safe_addstr(stdscr, 2, 2, sys_info_text[:max_w-4], curses.A_BOLD | curses.color_pair(3))

            top_title_dyn = L['top_title'].replace("TOP-5", f"TOP-{TOP_COUNT}")
            safe_addstr(stdscr, 4, 2, top_title_dyn[:max_w-4], curses.A_BOLD | curses.color_pair(6))
            for idx, proc in enumerate(top_procs_cache):
                attr = curses.color_pair(4) | curses.A_BOLD if idx == 0 else curses.color_pair(6)
                safe_addstr(stdscr, 5 + idx, 4, proc[:max_w-8], attr)

            safe_addstr(stdscr, 5 + len(top_procs_cache), 0, "-" * max_w)
            list_start_y = 6 + len(top_procs_cache)
        elif show_sysinfo:
            safe_addstr(stdscr, 2, 2, sys_info_text[:max_w-4], curses.A_BOLD | curses.color_pair(3))
            safe_addstr(stdscr, 3, 0, "-" * max_w)
            list_start_y = 4

        MIN_COL_W = 40
        col_count = max(1, max_w // MIN_COL_W)
        col_count = min(4, col_count)
        col_w = max_w // col_count

        if col_w < 55:
            status_w = 10
            rl_w = 0
            name_w = max(10, col_w - status_w - 5)
        else:
            status_w = 12
            rl_w = 10
            name_w = max(10, col_w - status_w - rl_w - 6)

        header_str = f"{L['col_service'].ljust(name_w)} {L['col_status'].ljust(status_w)}"
        if rl_w > 0:
            header_str += f" {L['col_autorun'].ljust(rl_w)}"

        for c in range(col_count):
            x_pos = 2 + c * col_w
            if x_pos < max_w:
                avail_w = min(col_w - 2, max_w - x_pos)
                if avail_w > 0:
                    safe_addstr(stdscr, list_start_y, x_pos, header_str[:avail_w], curses.A_BOLD)

        safe_addstr(stdscr, list_start_y + 1, 0, "-" * max_w)

        if h >= 30: log_lines_count = 8
        elif h >= 22: log_lines_count = 5
        elif h >= 15: log_lines_count = 3
        else: log_lines_count = 1

        bottom_h = log_lines_count + 3
        actual_list_start = list_start_y + 2
        list_h = max(1, h - actual_list_start - bottom_h)
        items_per_page = list_h * col_count

        current_page = sel_idx // items_per_page if items_per_page > 0 else 0
        scroll_offset = current_page * items_per_page

        for i in range(items_per_page):
            idx = scroll_offset + i
            if idx >= len(display_services): break
            svc = display_services[idx]

            row_idx = i % list_h
            col_idx = i // list_h

            y = actual_list_start + row_idx
            x_offset = col_idx * col_w

            status_color = curses.color_pair(6)
            if "started" in svc['status']: status_color = curses.color_pair(1)
            elif "crashed" in svc['status']: status_color = curses.color_pair(3)
            elif "stopped" in svc['status']: status_color = curses.color_pair(2)

            prefix_chars = []
            if svc['is_bl']: prefix_chars.append('B')
            if svc['is_fav']: prefix_chars.append('★')
            elif svc['priority'] == 1: prefix_chars.append('↑')
            elif svc['priority'] == -1: prefix_chars.append('↓')

            if prefix_chars: prefix = f"[{''.join(prefix_chars)}]"
            else: prefix = "   "

            name_color = curses.color_pair(6)
            prefix_color = curses.color_pair(6)

            if svc['is_fav'] and svc['priority'] == 1:
                prefix_color = curses.color_pair(8) | curses.A_BOLD
                name_color = curses.color_pair(3) | curses.A_BOLD
            elif svc['is_fav']:
                prefix_color = curses.color_pair(3) | curses.A_BOLD
                name_color = curses.color_pair(3) | curses.A_BOLD
            elif svc['is_bl'] and not svc['is_fav']:
                prefix_color = curses.color_pair(6) | curses.A_DIM
                name_color = curses.color_pair(6) | curses.A_DIM
            elif svc['priority'] == 1:
                prefix_color = curses.color_pair(4) | curses.A_BOLD
                name_color = curses.color_pair(4) | curses.A_BOLD
            elif svc['priority'] == -1:
                prefix_color = curses.color_pair(6) | curses.A_DIM
                name_color = curses.color_pair(6) | curses.A_DIM

            safe_status = svc['status'][:status_w]
            safe_runlevel = svc['runlevel'][:rl_w] if rl_w > 0 else ""

            name_x = x_offset + 2 + len(prefix) + 1
            status_x = x_offset + 2 + name_w + 1
            rl_x = status_x + status_w + 1

            if idx == sel_idx:
                safe_addstr(stdscr, y, x_offset, " " * (col_w - 1), curses.color_pair(4) | curses.A_REVERSE)
                safe_name = f"{prefix} {svc['name']}"[:name_w]
                safe_addstr(stdscr, y, x_offset + 2, safe_name.ljust(name_w), curses.color_pair(4) | curses.A_REVERSE | curses.A_BOLD)
                safe_addstr(stdscr, y, status_x, safe_status.ljust(status_w), curses.color_pair(4) | curses.A_REVERSE)
                if rl_w > 0:
                    safe_addstr(stdscr, y, rl_x, safe_runlevel.ljust(rl_w), curses.color_pair(4) | curses.A_REVERSE)
            else:
                safe_addstr(stdscr, y, x_offset + 2, prefix, prefix_color)
                space_left = max(0, name_w - len(prefix) - 1)
                safe_name_only = svc['name'][:space_left]
                safe_addstr(stdscr, y, name_x, safe_name_only.ljust(space_left), name_color)
                safe_addstr(stdscr, y, status_x, safe_status.ljust(status_w), status_color | curses.A_BOLD)
                if rl_w > 0:
                    safe_addstr(stdscr, y, rl_x, safe_runlevel[:rl_w], curses.color_pair(3))

        safe_addstr(stdscr, h - bottom_h, 0, "-" * max_w)
        bl_ind = f" ({L['shown']})" if show_blacklist else ""
        safe_addstr(stdscr, h - bottom_h + 1, 2, (L['log_title'] + bl_ind)[:max_w-4], curses.A_BOLD | curses.color_pair(6))

        for idx, log_msg in enumerate(log_messages[-log_lines_count:]):
            draw_colorized_log(stdscr, h - bottom_h + 2 + idx, 2, log_msg, max_w)

        if in_search:
            prompt = f"{L['search_prompt']} {search_query}█"
            safe_addstr(stdscr, h - 1, 0, prompt[:max_w].ljust(max_w), curses.color_pair(4) | curses.A_REVERSE | curses.A_BOLD)
        else:
            if search_query:
                hint = f"{L['search_prompt']} '{search_query}' " + L['bottom_hint']
                safe_addstr(stdscr, h - 1, 0, hint[:max_w].center(max_w), curses.color_pair(4))
            else:
                safe_addstr(stdscr, h - 1, 0, L['bottom_hint'][:max_w].center(max_w), curses.color_pair(4))

        stdscr.refresh()

        if pending_action:
            if pending_action == "CMD":
                is_crit = False
                is_dangerous_cmd = (
                    any(act in pending_payload for act in [" stop", " zap"]) or
                    pending_payload.startswith("rc-update del")
                )

                if is_dangerous_cmd:
                    parts = pending_payload.split()
                    svc_name = ""
                    if "rc-update" in pending_payload:
                        if len(parts) > 2:
                            svc_name = parts[2]
                    else:
                        if len(parts) > 0:
                            svc_name = os.path.basename(parts[0])

                    if svc_name and (svc_name in CRITICAL_SERVICES or svc_name.startswith("net.")):
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
                removed_items = []
                paths_to_remove = [
                    f"/run/{pending_payload}.pid",
                    f"/var/run/{pending_payload}.pid"
                ]
                for p in paths_to_remove:
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                            removed_items.append(p)
                        except Exception as e:
                            log_messages.append(f"Error removing {p}: {e}")

                dir_to_remove = f"/run/openrc/daemons/{pending_payload}"
                if os.path.exists(dir_to_remove):
                    try:
                        if os.path.isdir(dir_to_remove):
                            shutil.rmtree(dir_to_remove)
                        else:
                            os.remove(dir_to_remove)
                        removed_items.append(dir_to_remove)
                    except Exception as e:
                        log_messages.append(f"Error removing {dir_to_remove}: {e}")

                if removed_items:
                    add_log(L['msg_pid_del'].format(pending_payload) + f" ({', '.join(removed_items)})")
                else:
                    add_log(f"No PID files found for {pending_payload}.")

            pending_action = None
            pending_payload = None
            services = get_services(favs, bl_set, prio_dict, show_blacklist)
            continue

        try:
            key = stdscr.get_wch()
        except curses.error:
            key = -1

        current_time = time.time()
        if current_time - last_top_update > 2.0:
            top_procs_cache = get_top_processes()
            sys_info_cache = get_sys_info()
            last_top_update = current_time

        if key == -1: continue

        is_enter = (isinstance(key, str) and key in ('\n', '\r')) or (isinstance(key, int) and key in (curses.KEY_ENTER, 10, 13))
        is_esc = (isinstance(key, str) and key == '\x1b') or (isinstance(key, int) and key == 27)
        is_bs = (isinstance(key, str) and key in ('\b', '\x7f')) or (isinstance(key, int) and key in (curses.KEY_BACKSPACE, 127, 8))

        if in_search:
            if is_esc:
                in_search = False
                search_query = ""
                sel_idx = 0
            elif is_enter:
                in_search = False
            elif is_bs:
                search_query = search_query[:-1]
                sel_idx = 0
            elif isinstance(key, str) and key.isprintable():
                search_query += key
                sel_idx = 0
            continue
        else:
            if isinstance(key, str) and key == '/':
                in_search = True
                continue

        if (isinstance(key, str) and key.lower() in ('q', 'й')) or (isinstance(key, int) and key == curses.KEY_F10): break
        elif isinstance(key, int) and key == curses.KEY_UP and sel_idx > 0: sel_idx -= 1
        elif isinstance(key, int) and key == curses.KEY_DOWN and sel_idx < len(display_services) - 1: sel_idx += 1
        elif isinstance(key, int) and key == curses.KEY_NPAGE: sel_idx = min(len(display_services) - 1, sel_idx + 5)
        elif isinstance(key, int) and key == curses.KEY_PPAGE: sel_idx = max(0, sel_idx - 5)

        elif isinstance(key, str) and key.lower() in ('r', 'к'):
            add_log(L['msg_refresh'])
            services = get_services(favs, bl_set, prio_dict, show_blacklist)

        elif isinstance(key, str) and key.lower() in ('i', 'ш'):
            if display_services:
                show_info_panel(stdscr, display_services[sel_idx])

        elif isinstance(key, str) and key.lower() in ('g', 'п'):
            current_code = L.get("current_lang_code", "en")
            new_lang = "ru" if current_code == "en" else "en"
            full_data = get_dict(LANG_FILE) if os.path.exists(LANG_FILE) else DEFAULT_LANG_DATA.copy()
            full_data["current_lang"] = new_lang
            save_dict(LANG_FILE, full_data)
            load_language()
            msg = L.get(f'msg_lang_{new_lang}', f'Language switched to {new_lang}')
            add_log(msg)

        elif isinstance(key, str) and key.lower() in ('l', 'д'):
            show_blacklist = not show_blacklist
            status_txt = L['shown'] if show_blacklist else L['hidden']
            add_log(L['msg_bl_mode'].format(status_txt))
            services = get_services(favs, bl_set, prio_dict, show_blacklist)
            sel_idx = min(sel_idx, max(0, len(services) - 1))

        elif isinstance(key, str) and key.lower() in ('b', 'и'):
            if display_services:
                svc_name = display_services[sel_idx]['name']
                if svc_name in bl_set: bl_set.discard(svc_name)
                else: bl_set.add(svc_name)
                save_list(BLACKLIST_FILE, bl_set)
                add_log(L['msg_bl'].format(svc_name))
                services = get_services(favs, bl_set, prio_dict, show_blacklist)

        elif isinstance(key, str) and key.lower() in ('p', 'з'):
            if display_services:
                svc_name = display_services[sel_idx]['name']
                curr_prio = prio_dict.get(svc_name, 0)
                new_prio = 1 if curr_prio == 0 else 0

                if new_prio == 0 and svc_name in prio_dict: del prio_dict[svc_name]
                else: prio_dict[svc_name] = new_prio

                save_dict(PRIO_FILE, prio_dict)
                add_log(L['msg_prio'].format(svc_name))
                services = get_services(favs, bl_set, prio_dict, show_blacklist)

        elif isinstance(key, str) and key.lower() in ('f', 'а'):
            if display_services:
                svc_name = display_services[sel_idx]['name']
                if svc_name in favs: favs.discard(svc_name)
                else: favs.add(svc_name)
                save_list(FAV_FILE, favs)
                add_log(L['msg_fav'].format(svc_name))
                services = get_services(favs, bl_set, prio_dict, show_blacklist)

        elif is_enter:
            if not display_services: continue
            action_type, payload = show_action_menu(stdscr, display_services[sel_idx])
            if action_type in ("CMD", "PID"):
                pending_action, pending_payload = action_type, payload

        elif isinstance(key, int) and key == curses.KEY_MOUSE:
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
                        clicked_idx = scroll_offset + (col * list_h) + row
                        if clicked_idx < len(display_services):
                            if sel_idx != clicked_idx:
                                sel_idx = clicked_idx
                            elif bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED | curses.BUTTON1_PRESSED):
                                action_type, payload = show_action_menu(stdscr, display_services[sel_idx])
                                if action_type in ("CMD", "PID"):
                                    pending_action, pending_payload = action_type, payload
            except curses.error: pass

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
