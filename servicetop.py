#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================
   Servicetop OpenRC Manager v3.2 (Advanced Edition)
   Repository: https://github.com/PEAKT0P/servicetop.py
========================================================================
    Update/Install:
   $ sudo rm -f /opt/servicetop/lang.json
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

# Рабочая директория
BASE_DIR = "/opt/servicetop"
FAV_FILE = os.path.join(BASE_DIR, "favorites.list")
BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.list")
PRIO_FILE = os.path.join(BASE_DIR, "priority.json")
LANG_FILE = os.path.join(BASE_DIR, "lang.json")

# Регулярки для раскраски логов и очистки
TOKEN_RE = re.compile(r'(\[\s*ok\s*\]|\[\s*!!\s*\]|\[\s*fail\s*\]|Ошибка:|Успешно:|Выполняю:|\s\*\s)')
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

if os.geteuid() != 0:
    print("Ошибка: servicetop должен запускаться от root!")
    sys.exit(1)

os.makedirs(BASE_DIR, exist_ok=True)

DEFAULT_LANG_DATA = {
    "current_lang": "ru",
    "ru": {
        "title": " Servicetop (Gentoo/OpenRC) ",
        "top_title": " TOP-4 ПРОЦЕССА (CPU/MEM): ",
        "col_service": "СЕРВИС",
        "col_status": "СТАТУС",
        "col_autorun": "АВТОЗАПУСК",
        "log_title": "Лог действий:",
        "bottom_hint": " [ЛКМ] Меню [PgUp/Dn] Шаг 5 [F] Избранное [P] Приоритет [B] Blacklist [L] Показать все [Q] Выход ",
        "act_start": "Start (Запуск)",
        "act_stop": "Stop (Остановка)",
        "act_restart": "Restart (Перезапуск)",
        "act_zap": "ZAP (Сброс статуса)",
        "act_pid": "Удалить PID (Форс. очистка)",
        "act_add_auto": "Добавить в автозапуск",
        "act_del_auto": "Удалить из автозапуска",
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
        "err_small": "Окно терминала слишком маленькое!"
    }
}

def load_language():
    if not os.path.exists(LANG_FILE):
        try:
            with open(LANG_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_LANG_DATA, f, indent=4, ensure_ascii=False)
        except: pass
        return DEFAULT_LANG_DATA["ru"]
    try:
        with open(LANG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get(data.get("current_lang", "ru"), DEFAULT_LANG_DATA["ru"])
    except:
        return DEFAULT_LANG_DATA["ru"]

L = load_language()

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
def get_top_processes():
    try:
        # pid, %cpu, %mem, command
        out = subprocess.getoutput("ps -eo pid,pcpu,pmem,comm --sort=-pcpu | head -n 5").split('\n')
        return out
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

def show_action_menu(stdscr, service):
    h, w = stdscr.getmaxyx()
    menu_h, menu_w = 11, 54
    menu_y, menu_x = (h - menu_h) // 2, (w - menu_w) // 2

    win = curses.newwin(menu_h, menu_w, menu_y, menu_x)
    win.keypad(True)
    win.bkgd(' ', curses.color_pair(5))
    win.box()

    actions = [
        (L['act_start'], "CMD", f"/etc/init.d/{service['name']} start"),
        (L['act_stop'], "CMD", f"/etc/init.d/{service['name']} stop"),
        (L['act_restart'], "CMD", f"/etc/init.d/{service['name']} restart"),
        (L['act_zap'], "CMD", f"/etc/init.d/{service['name']} zap"),
        (L['act_pid'], "PID", service['name']),
        (L['act_add_auto'], "CMD", f"rc-update add {service['name']} default"),
        (L['act_del_auto'], "CMD", f"rc-update del {service['name']} default"),
        (L['act_cancel'], "CANCEL", "")
    ]

    sel_idx = 0
    while True:
        win.addstr(1, 2, L['menu_title'].format(service['name']), curses.A_BOLD | curses.color_pair(5))
        win.addstr(2, 2, "="*(menu_w-4), curses.color_pair(5))

        for idx, (label, _, _) in enumerate(actions):
            attr = curses.color_pair(4) if idx == sel_idx else curses.color_pair(5)
            win.addstr(3 + idx, 4, f" {label} ".ljust(menu_w-8), attr)

        win.refresh()
        key = win.getch()

        if key == curses.KEY_UP and sel_idx > 0: sel_idx -= 1
        elif key == curses.KEY_DOWN and sel_idx < len(actions) - 1: sel_idx += 1
        elif key in [curses.KEY_ENTER, 10, 13]: return actions[sel_idx][1], actions[sel_idx][2]
        elif key == 27: return "CANCEL", ""

def main(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.timeout(2000) # Обновление интерфейса каждые 2 секунды (для top)
    curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(6, curses.COLOR_WHITE, -1)
    curses.init_pair(7, curses.COLOR_MAGENTA, -1)
    curses.init_pair(8, curses.COLOR_YELLOW, curses.COLOR_BLUE) # Новая пара для избранного с приоритетом

    favs = get_list(FAV_FILE)
    bl_set = get_list(BLACKLIST_FILE)
    prio_dict = get_dict(PRIO_FILE)
    
    show_blacklist = False
    services = get_services(favs, bl_set, prio_dict, show_blacklist)
    sel_idx = 0
    log_messages = [L['msg_welcome']]
    
    top_procs_cache = get_top_processes()
    last_top_update = time.time()

    pending_action = None
    pending_payload = None

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        max_w = w - 1

        if h < 24 or max_w < 70:
            stdscr.addstr(0, 0, L['err_small'])
            stdscr.refresh()
            stdscr.getch()
            break

        # Заголовок
        stdscr.addstr(0, 0, L['title'].center(max_w), curses.color_pair(4) | curses.A_BOLD)
        stdscr.addstr(1, 0, "-" * max_w)

        # TOP процессов
        show_top = h >= 30  
        list_start_y = 3
        if show_top:
            stdscr.addstr(2, 2, L['top_title'], curses.A_BOLD | curses.color_pair(3))
            for idx, proc in enumerate(top_procs_cache[:5]):
                attr = curses.color_pair(6) if idx > 0 else curses.color_pair(4)
                stdscr.addstr(3 + idx, 4, proc[:max_w-8], attr)
            stdscr.addstr(8, 0, "-" * max_w)
            list_start_y = 9

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
            if idx >= len(services): break
            svc = services[idx]
            
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
            
            # Логика приоритетов и избранного
            if svc['is_fav'] and svc['priority'] == 1:
                prefix = "[★]"
                prefix_color = curses.color_pair(8) | curses.A_BOLD  # Желтый на синем фоне
                name_color = curses.color_pair(3) | curses.A_BOLD    # Имя остается просто желтым
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
                # Отрисовка префикса и имени раздельно для разных цветов
                stdscr.addstr(y, x_offset + 2, prefix, prefix_color)
                
                space_left = 32 - len(prefix) - 1
                safe_name_only = svc['name'][:space_left]
                stdscr.addstr(y, x_offset + 2 + len(prefix) + 1, safe_name_only.ljust(space_left), name_color)
                
                stdscr.addstr(y, x_offset + 35, safe_status.ljust(15), status_color | curses.A_BOLD)
                stdscr.addstr(y, x_offset + 51, safe_runlevel, curses.color_pair(3))

        # Окно логов
        stdscr.addstr(h - bottom_h, 0, "-" * max_w)
        bl_ind = " (Вкл. скрытые)" if show_blacklist else ""
        stdscr.addstr(h - bottom_h + 1, 2, L['log_title'] + bl_ind, curses.A_BOLD | curses.color_pair(6))

        for idx, log_msg in enumerate(log_messages[-log_lines_count:]):
            draw_colorized_log(stdscr, h - bottom_h + 2 + idx, 2, log_msg, max_w)

        # Подсказки
        try: stdscr.addstr(h - 1, 0, L['bottom_hint'].center(max_w), curses.color_pair(4))
        except curses.error: pass

        stdscr.refresh()

        if pending_action:
            if pending_action == "CMD":
                res = execute_command(pending_payload)
                for line in res.split('\n'):
                    if line.strip(): log_messages.append(line.strip())
            elif pending_action == "PID":
                cmds = [
                    f"rm -f /run/{pending_payload}.pid",
                    f"rm -f /var/run/{pending_payload}.pid",
                    f"rm -rf /run/openrc/daemons/{pending_payload}"
                ]
                execute_command("; ".join(cmds))
                log_messages.append(L['msg_pid_del'].format(pending_payload))

            pending_action = None
            pending_payload = None
            services = get_services(favs, bl_set, prio_dict, show_blacklist)
            continue 

        key = stdscr.getch()

        current_time = time.time()
        if current_time - last_top_update > 2.0:
            top_procs_cache = get_top_processes()
            last_top_update = current_time

        if key == -1: continue 

        if key in (ord('q'), ord('Q')): break
        elif key == curses.KEY_UP and sel_idx > 0: sel_idx -= 1
        elif key == curses.KEY_DOWN and sel_idx < len(services) - 1: sel_idx += 1
        elif key == curses.KEY_NPAGE: sel_idx = min(len(services) - 1, sel_idx + 5) 
        elif key == curses.KEY_PPAGE: sel_idx = max(0, sel_idx - 5)                 
        
        elif key in (ord('r'), ord('R')):
            log_messages.append(L['msg_refresh'])
            services = get_services(favs, bl_set, prio_dict, show_blacklist)
            
        elif key in (ord('l'), ord('L')):
            show_blacklist = not show_blacklist
            status_txt = "Отображаются" if show_blacklist else "Скрыты"
            log_messages.append(L['msg_bl_mode'].format(status_txt))
            services = get_services(favs, bl_set, prio_dict, show_blacklist)
            sel_idx = min(sel_idx, max(0, len(services) - 1))

        elif key in (ord('b'), ord('B')):
            if services:
                svc_name = services[sel_idx]['name']
                if svc_name in bl_set: bl_set.discard(svc_name)
                else: bl_set.add(svc_name)
                save_list(BLACKLIST_FILE, bl_set)
                log_messages.append(L['msg_bl'].format(svc_name))
                services = get_services(favs, bl_set, prio_dict, show_blacklist)
                sel_idx = min(sel_idx, max(0, len(services) - 1))

        elif key in (ord('p'), ord('P')):
            if services:
                svc_name = services[sel_idx]['name']
                curr_prio = prio_dict.get(svc_name, 0)
                new_prio = 1 if curr_prio == 0 else (-1 if curr_prio == 1 else 0)
                
                if new_prio == 0 and svc_name in prio_dict: del prio_dict[svc_name]
                else: prio_dict[svc_name] = new_prio
                
                save_dict(PRIO_FILE, prio_dict)
                log_messages.append(L['msg_prio'].format(svc_name))
                services = get_services(favs, bl_set, prio_dict, show_blacklist)
                
        elif key in (ord('f'), ord('F')):
            if services:
                svc_name = services[sel_idx]['name']
                if svc_name in favs: favs.discard(svc_name)
                else: favs.add(svc_name)
                save_list(FAV_FILE, favs)
                log_messages.append(L['msg_fav'].format(svc_name))
                services = get_services(favs, bl_set, prio_dict, show_blacklist)
                
        elif key in [curses.KEY_ENTER, 10, 13]:
            if not services: continue
            action_type, payload = show_action_menu(stdscr, services[sel_idx])
            if action_type in ("CMD", "PID"):
                if action_type == "CMD": log_messages.append(L['msg_exec'].format(payload))
                pending_action, pending_payload = action_type, payload

        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
                if actual_list_start <= my < actual_list_start + list_h:
                    row = my - actual_list_start
                    col = mx // col_w
                    if col < col_count:
                        clicked_idx = scroll_offset + (col * list_h) + row if col_count == 2 else scroll_offset + row
                        if clicked_idx < len(services):
                            if sel_idx != clicked_idx:
                                sel_idx = clicked_idx
                            elif bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED | curses.BUTTON1_PRESSED):
                                action_type, payload = show_action_menu(stdscr, services[sel_idx])
                                if action_type in ("CMD", "PID"):
                                    if action_type == "CMD": log_messages.append(L['msg_exec'].format(payload))
                                    pending_action, pending_payload = action_type, payload
            except curses.error: pass

if __name__ == "__main__":
    curses.wrapper(main)
