#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================
   Servicetop OpenRC Manager v3
========================================================================
   Quick setup:
   $ sudo ln -s /opt/servicetop/servicetop.py /usr/local/bin/servicetop
   
   Usage:
   $ sudo servicetop
========================================================================
"""

import curses
import subprocess
import os
import sys
import json

# Рабочая директория
BASE_DIR = "/opt/servicetop"
FAV_FILE = os.path.join(BASE_DIR, "favorites.list")
LANG_FILE = os.path.join(BASE_DIR, "lang.json")

# Проверка на root
if os.geteuid() != 0:
    print("Ошибка: servicetop должен запускаться от root!")
    sys.exit(1)

# Создаем папку, если вдруг ее нет
os.makedirs(BASE_DIR, exist_ok=True)

# Базовый словарь (сохранится в lang.json при первом запуске)
DEFAULT_LANG_DATA = {
    "current_lang": "ru",
    "ru": {
        "title": " Servicetop (Gentoo/OpenRC) ",
        "col_service": "СЕРВИС",
        "col_status": "СТАТУС",
        "col_autorun": "АВТОЗАПУСК",
        "log_title": "Лог действий:",
        "bottom_hint": " [Клик] Выбор  [Enter] Меню  [F] Избранное  [PgUp/Dn] Прокрутка  [R] Обновить  [Q] Выход ",
        "act_start": "Start (Запуск)",
        "act_stop": "Stop (Остановка)",
        "act_restart": "Restart (Перезапуск)",
        "act_zap": "ZAP (Сброс статуса)",
        "act_pid": "Удалить PID (Форс. очистка)",
        "act_add_auto": "Добавить в автозапуск",
        "act_del_auto": "Удалить из автозапуска",
        "act_add_fav": "Добавить в избранное [★]",
        "act_del_fav": "Убрать из избранного",
        "act_cancel": "Отмена",
        "menu_title": " Управление: {} ",
        "msg_welcome": "Добро пожаловать в ServiceTop! Сбор данных завершен.",
        "msg_refresh": "Обновление списка сервисов...",
        "msg_exec": "Выполняю: {}",
        "msg_pid_del": "PID файлы для {} удалены.",
        "msg_fav_add": "{} добавлен в избранное.",
        "msg_fav_del": "{} удален из избранного.",
        "err_small": "Окно терминала слишком маленькое!"
    },
    "en": {
        "title": " Servicetop (Gentoo/OpenRC) ",
        "col_service": "SERVICE",
        "col_status": "STATUS",
        "col_autorun": "AUTORUN",
        "log_title": "Action Log:",
        "bottom_hint": " [Click] Select  [Enter] Menu  [F] Favorite  [PgUp/Dn] Scroll  [R] Refresh  [Q] Quit ",
        "act_start": "Start",
        "act_stop": "Stop",
        "act_restart": "Restart",
        "act_zap": "ZAP (Reset status)",
        "act_pid": "Delete PID (Force clean)",
        "act_add_auto": "Add to autorun",
        "act_del_auto": "Remove from autorun",
        "act_add_fav": "Add to Favorites [★]",
        "act_del_fav": "Remove from Favorites",
        "act_cancel": "Cancel",
        "menu_title": " Manage: {} ",
        "msg_welcome": "Welcome to ServiceTop! Data collection complete.",
        "msg_refresh": "Refreshing service list...",
        "msg_exec": "Executing: {}",
        "msg_pid_del": "PID files for {} deleted.",
        "msg_fav_add": "{} added to favorites.",
        "msg_fav_del": "{} removed from favorites.",
        "err_small": "Terminal window is too small!"
    }
}

def load_language():
    if not os.path.exists(LANG_FILE):
        try:
            with open(LANG_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_LANG_DATA, f, indent=4, ensure_ascii=False)
        except:
            pass
        return DEFAULT_LANG_DATA["ru"]
    
    try:
        with open(LANG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            lang_code = data.get("current_lang", "ru")
            return data.get(lang_code, DEFAULT_LANG_DATA["ru"])
    except:
        return DEFAULT_LANG_DATA["ru"]

L = load_language()

def get_favorites():
    if not os.path.exists(FAV_FILE):
        return set()
    try:
        with open(FAV_FILE, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except:
        return set()

def save_favorites(favs):
    try:
        with open(FAV_FILE, 'w') as f:
            for fav in sorted(list(favs)):
                f.write(f"{fav}\n")
    except:
        pass

def get_services(favs):
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
                    state = parts[state_idx]
                except ValueError:
                    state = "unknown"
                status_map[name] = state

    rc_update_out = subprocess.getoutput("rc-update show").split('\n')
    runlevel_map = {}
    for line in rc_update_out:
        if '|' in line:
            parts = line.split('|')
            name = parts[0].strip()
            rl = parts[1].strip()
            runlevel_map[name] = rl

    for file in sorted(os.listdir('/etc/init.d/')):
        if file in ['functions.sh', 'net.lo'] or file.startswith('.'):
            continue
        filepath = os.path.join('/etc/init.d/', file)
        if os.path.isfile(filepath) and os.access(filepath, os.X_OK):
            status = status_map.get(file, "stopped")
            runlevel = runlevel_map.get(file, "")
            is_fav = file in favs
            services.append({
                "name": file, 
                "status": status, 
                "runlevel": runlevel,
                "is_fav": is_fav
            })

    services.sort(key=lambda x: (not x['is_fav'], x['name']))
    return services

def execute_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        output = result.stdout.strip() + " " + result.stderr.strip()
        return output if output else f"Успешно: {cmd}"
    except Exception as e:
        return f"Ошибка: {e}"

def show_action_menu(stdscr, service):
    h, w = stdscr.getmaxyx()
    menu_h, menu_w = 12, 54
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
    ]
    
    if service['is_fav']:
        actions.append((L['act_del_fav'], "FAV_DEL", service['name']))
    else:
        actions.append((L['act_add_fav'], "FAV_ADD", service['name']))
        
    actions.append((L['act_cancel'], "CANCEL", ""))

    sel_idx = 0
    while True:
        title = L['menu_title'].format(service['name'])
        win.addstr(1, 2, title, curses.A_BOLD | curses.color_pair(5))
        win.addstr(2, 2, "="*(menu_w-4), curses.color_pair(5))

        for idx, (label, _, _) in enumerate(actions):
            attr = curses.color_pair(4) if idx == sel_idx else curses.color_pair(5)
            win.addstr(3 + idx, 4, f" {label} ".ljust(menu_w-8), attr)

        win.refresh()
        key = win.getch()

        if key == curses.KEY_UP and sel_idx > 0:
            sel_idx -= 1
        elif key == curses.KEY_DOWN and sel_idx < len(actions) - 1:
            sel_idx += 1
        elif key in [curses.KEY_ENTER, 10, 13]:
            return actions[sel_idx][1], actions[sel_idx][2]
        elif key == 27:
            return "CANCEL", ""
        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
                if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED):
                    if menu_y + 3 <= my < menu_y + 3 + len(actions) and menu_x <= mx <= menu_x + menu_w:
                        clicked_idx = my - (menu_y + 3)
                        return actions[clicked_idx][1], actions[clicked_idx][2]
            except:
                pass

def main(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)   
    curses.init_pair(2, curses.COLOR_RED, -1)     
    curses.init_pair(3, curses.COLOR_YELLOW, -1)  
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_CYAN) 
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE) 
    curses.init_pair(6, curses.COLOR_WHITE, -1)   

    favs = get_favorites()
    services = get_services(favs)
    sel_idx = 0
    log_messages = [L['msg_welcome']]

    while True:
        stdscr.erase() # Используем erase() вместо clear() для устранения мерцания
        h, w = stdscr.getmaxyx()
        max_w = w - 1

        if h < 16 or max_w < 70:
            stdscr.addstr(0, 0, L['err_small'])
            stdscr.refresh()
            stdscr.getch()
            break

        # Динамическая ширина (2 колонки, если ширина >= 135)
        col_count = 2 if max_w >= 135 else 1
        col_w = max_w // col_count

        # Шапка
        stdscr.addstr(0, 0, L['title'].center(max_w), curses.color_pair(4) | curses.A_BOLD)
        
        header_str = f"{L['col_service'].ljust(32)} {L['col_status'].ljust(15)} {L['col_autorun']}"
        if col_count == 2:
            stdscr.addstr(1, 2, header_str[:col_w - 4], curses.A_BOLD)
            stdscr.addstr(1, 2 + col_w, header_str[:col_w - 4], curses.A_BOLD)
        else:
            stdscr.addstr(1, 2, header_str, curses.A_BOLD)
            
        stdscr.addstr(2, 0, "-" * max_w)

        # Вычисление области списка
        list_start_y = 3
        list_h = h - 11 
        items_per_page = list_h * col_count

        # Логика страничной прокрутки
        current_page = sel_idx // items_per_page
        scroll_offset = current_page * items_per_page

        # Отрисовка списка (сверху вниз, слева направо)
        for i in range(items_per_page):
            idx = scroll_offset + i
            if idx >= len(services):
                break

            svc = services[idx]
            
            if col_count == 2:
                row_idx = i % list_h
                col_idx = i // list_h
            else:
                row_idx = i
                col_idx = 0
                
            y = list_start_y + row_idx
            x_offset = col_idx * col_w

            status_color = curses.color_pair(6)
            if "started" in svc['status']: status_color = curses.color_pair(1)
            elif "crashed" in svc['status']: status_color = curses.color_pair(3)
            elif "stopped" in svc['status']: status_color = curses.color_pair(2)

            display_name = f"[★] {svc['name']}" if svc['is_fav'] else f"    {svc['name']}"
            safe_name = display_name[:32]
            safe_status = svc['status'][:13]
            safe_runlevel = svc['runlevel'][:15]

            if idx == sel_idx:
                stdscr.addstr(y, x_offset, " " * (col_w - 1), curses.color_pair(4))
                stdscr.addstr(y, x_offset + 2, safe_name.ljust(32), curses.color_pair(4) | curses.A_BOLD)
                stdscr.addstr(y, x_offset + 35, safe_status.ljust(15), curses.color_pair(4))
                stdscr.addstr(y, x_offset + 51, safe_runlevel, curses.color_pair(4))
            else:
                name_color = curses.color_pair(3) | curses.A_BOLD if svc['is_fav'] else curses.color_pair(6)
                stdscr.addstr(y, x_offset + 2, safe_name.ljust(32), name_color)
                stdscr.addstr(y, x_offset + 35, safe_status.ljust(15), status_color | curses.A_BOLD)
                stdscr.addstr(y, x_offset + 51, safe_runlevel, curses.color_pair(3))

        # Окно логов
        stdscr.addstr(h-8, 0, "-" * max_w)
        stdscr.addstr(h-7, 2, L['log_title'], curses.A_BOLD)

        for idx, log_msg in enumerate(log_messages[-5:]):
            safe_msg = log_msg[:max_w-4].replace('\n', ' ')
            stdscr.addstr(h-6+idx, 2, safe_msg, curses.color_pair(3))

        # Подсказки внизу
        try:
            stdscr.addstr(h-1, 0, L['bottom_hint'].center(max_w), curses.color_pair(4))
        except curses.error:
            pass

        stdscr.refresh()

        key = stdscr.getch()

        if key in (ord('q'), ord('Q')):
            break
        elif key == curses.KEY_UP and sel_idx > 0:
            sel_idx -= 1
        elif key == curses.KEY_DOWN and sel_idx < len(services) - 1:
            sel_idx += 1
        elif key == curses.KEY_NPAGE: 
            sel_idx = min(len(services) - 1, sel_idx + items_per_page)
        elif key == curses.KEY_PPAGE: 
            sel_idx = max(0, sel_idx - items_per_page)
        elif key in (ord('r'), ord('R')):
            log_messages.append(L['msg_refresh'])
            services = get_services(favs)
        elif key in (ord('f'), ord('F')): # Горячая клавиша добавления в избранное
            if services:
                svc = services[sel_idx]
                if svc['is_fav']:
                    favs.discard(svc['name'])
                    log_messages.append(L['msg_fav_del'].format(svc['name']))
                else:
                    favs.add(svc['name'])
                    log_messages.append(L['msg_fav_add'].format(svc['name']))
                save_favorites(favs)
                services = get_services(favs)
        elif key in [curses.KEY_ENTER, 10, 13]:
            if not services: continue
            action_type, payload = show_action_menu(stdscr, services[sel_idx])
            
            if action_type == "CMD":
                log_messages.append(L['msg_exec'].format(payload))
                stdscr.refresh()
                res = execute_command(payload)
                log_messages.append(res)
            elif action_type == "PID":
                cmds = [
                    f"rm -f /run/{payload}.pid",
                    f"rm -f /var/run/{payload}.pid",
                    f"rm -rf /run/openrc/daemons/{payload}"
                ]
                execute_command("; ".join(cmds))
                log_messages.append(L['msg_pid_del'].format(payload))
            elif action_type == "FAV_ADD":
                favs.add(payload)
                save_favorites(favs)
                log_messages.append(L['msg_fav_add'].format(payload))
            elif action_type == "FAV_DEL":
                favs.discard(payload)
                save_favorites(favs)
                log_messages.append(L['msg_fav_del'].format(payload))
            
            services = get_services(favs) 

        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
                if list_start_y <= my < list_start_y + list_h:
                    row = my - list_start_y
                    col = mx // col_w
                    
                    if col < col_count:
                        if col_count == 2:
                            clicked_idx = scroll_offset + (col * list_h) + row
                        else:
                            clicked_idx = scroll_offset + row
                            
                        if clicked_idx < len(services):
                            if sel_idx != clicked_idx:
                                sel_idx = clicked_idx
                            elif bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED | curses.BUTTON1_PRESSED):
                                action_type, payload = show_action_menu(stdscr, services[sel_idx])
                                
                                if action_type == "CMD":
                                    log_messages.append(L['msg_exec'].format(payload))
                                    stdscr.refresh()
                                    res = execute_command(payload)
                                    log_messages.append(res)
                                elif action_type == "PID":
                                    cmds = [
                                        f"rm -f /run/{payload}.pid",
                                        f"rm -f /var/run/{payload}.pid",
                                        f"rm -rf /run/openrc/daemons/{payload}"
                                    ]
                                    execute_command("; ".join(cmds))
                                    log_messages.append(L['msg_pid_del'].format(payload))
                                elif action_type == "FAV_ADD":
                                    favs.add(payload)
                                    save_favorites(favs)
                                    log_messages.append(L['msg_fav_add'].format(payload))
                                elif action_type == "FAV_DEL":
                                    favs.discard(payload)
                                    save_favorites(favs)
                                    log_messages.append(L['msg_fav_del'].format(payload))
                                    
                                services = get_services(favs)
            except curses.error:
                pass

if __name__ == "__main__":
    curses.wrapper(main)
