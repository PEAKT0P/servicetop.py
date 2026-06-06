#!/usr/bin/env python3
#b1
# -*- coding: utf-8 -*-

import curses
import subprocess
import os
import sys

# Проверка на root
if os.geteuid() != 0:
    print("Ошибка: servicetop должен запускаться от root!")
    sys.exit(1)

def get_services():
    """Собирает список сервисов из /etc/init.d/ и их статус"""
    services = []

    # Получаем все статусы через rc-status
    status_out = subprocess.getoutput("rc-status -a").split('\n')
    status_map = {}
    for line in status_out:
        if '[' in line and ']' in line:
            parts = line.strip().split()
            if len(parts) >= 3:
                name = parts[0]
                try:
                    # Ищем индекс скобки '[' и берем следующее за ней слово
                    state_idx = parts.index('[') + 1
                    state = parts[state_idx]
                except ValueError:
                    state = "unknown"
                status_map[name] = state

    # Получаем runlevels
    rc_update_out = subprocess.getoutput("rc-update show").split('\n')
    runlevel_map = {}
    for line in rc_update_out:
        if '|' in line:
            parts = line.split('|')
            name = parts[0].strip()
            rl = parts[1].strip()
            runlevel_map[name] = rl

    # Собираем все из init.d
    for file in sorted(os.listdir('/etc/init.d/')):
        if file in ['functions.sh', 'net.lo'] or file.startswith('.'):
            continue
        filepath = os.path.join('/etc/init.d/', file)
        if os.path.isfile(filepath) and os.access(filepath, os.X_OK):
            status = status_map.get(file, "stopped")
            runlevel = runlevel_map.get(file, "")
            services.append({"name": file, "status": status, "runlevel": runlevel})

    return services

def execute_command(cmd):
    """Выполняет команду и возвращает результат"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        output = result.stdout.strip() + " " + result.stderr.strip()
        return output if output else f"Успешно: {cmd}"
    except Exception as e:
        return f"Ошибка: {e}"

def show_action_menu(stdscr, service):
    """Всплывающее окно подтверждения (защита от мисскликов)"""
    h, w = stdscr.getmaxyx()
    menu_h, menu_w = 10, 50
    menu_y, menu_x = (h - menu_h) // 2, (w - menu_w) // 2

    win = curses.newwin(menu_h, menu_w, menu_y, menu_x)
    win.keypad(True)
    win.bkgd(' ', curses.color_pair(5))
    win.box()

    actions = [
        ("Start", f"/etc/init.d/{service['name']} start"),
        ("Stop", f"/etc/init.d/{service['name']} stop"),
        ("Restart", f"/etc/init.d/{service['name']} restart"),
        ("ZAP (Сброс статуса)", f"/etc/init.d/{service['name']} zap"),
        ("Добавить в автозапуск", f"rc-update add {service['name']} default"),
        ("Удалить из автозапуска", f"rc-update del {service['name']} default"),
        ("Отмена", "")
    ]

    sel_idx = 0
    while True:
        win.addstr(1, 2, f" Управление: {service['name']} ", curses.A_BOLD | curses.color_pair(5))
        win.addstr(2, 2, "="*(menu_w-4), curses.color_pair(5))

        for idx, (label, _) in enumerate(actions):
            attr = curses.color_pair(4) if idx == sel_idx else curses.color_pair(5)
            win.addstr(3 + idx, 4, f" {label} ".ljust(menu_w-8), attr)

        win.refresh()
        key = win.getch()

        if key == curses.KEY_UP and sel_idx > 0:
            sel_idx -= 1
        elif key == curses.KEY_DOWN and sel_idx < len(actions) - 1:
            sel_idx += 1
        elif key in [curses.KEY_ENTER, 10, 13]:
            return actions[sel_idx][1]
        elif key == 27: # ESC
            return ""
        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
                if bstate & curses.BUTTON1_CLICKED or bstate & curses.BUTTON1_PRESSED:
                    if menu_y + 3 <= my < menu_y + 3 + len(actions) and menu_x <= mx <= menu_x + menu_w:
                        clicked_idx = my - (menu_y + 3)
                        return actions[clicked_idx][1]
            except:
                pass

def main(stdscr):
    # Настройки curses
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

    # Цвета (как в mc/htop)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)   # Started
    curses.init_pair(2, curses.COLOR_RED, -1)     # Stopped
    curses.init_pair(3, curses.COLOR_YELLOW, -1)  # Crashed/Warning
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_CYAN) # Выделение
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE) # Всплывающее меню
    curses.init_pair(6, curses.COLOR_WHITE, -1)   # Обычный текст

    services = get_services()
    sel_idx = 0
    scroll_offset = 0
    log_messages = ["Добро пожаловать в ServiceTop! Сбор данных завершен."]

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        max_w = w - 1 # Безопасная ширина (избегаем правого края)

        # Защита от слишком маленького окна
        if h < 12 or max_w < 65:
            stdscr.addstr(0, 0, "Окно терминала слишком маленькое!")
            stdscr.refresh()
            stdscr.getch()
            break

        # Шапка
        stdscr.addstr(0, 0, " Servicetop (Gentoo/OpenRC) ".center(max_w), curses.color_pair(4) | curses.A_BOLD)
        stdscr.addstr(1, 2, f"{'СЕРВИС'.ljust(30)} {'СТАТУС'.ljust(15)} {'АВТОЗАПУСК'}", curses.A_BOLD)
        stdscr.addstr(2, 0, "-" * max_w)

        # Вычисление области списка
        list_start_y = 3
        list_h = h - 8 # Оставляем место внизу для логов

        # Обновление прокрутки
        if sel_idx < scroll_offset:
            scroll_offset = sel_idx
        elif sel_idx >= scroll_offset + list_h:
            scroll_offset = sel_idx - list_h + 1

        # Отрисовка списка
        for i in range(list_h):
            idx = scroll_offset + i
            if idx >= len(services):
                break

            svc = services[idx]
            y = list_start_y + i

            # Цвета статуса
            status_color = curses.color_pair(6)
            if "started" in svc['status']: status_color = curses.color_pair(1)
            elif "crashed" in svc['status']: status_color = curses.color_pair(3)
            elif "stopped" in svc['status']: status_color = curses.color_pair(2)

            # Ограничиваем длину строк, чтобы ничего не съехало
            safe_name = svc['name'][:28]
            safe_status = svc['status'][:13]
            safe_runlevel = svc['runlevel'][:15]

            # Выделение строки
            if idx == sel_idx:
                stdscr.addstr(y, 0, " " * max_w, curses.color_pair(4)) # Фон строки
                stdscr.addstr(y, 2, safe_name.ljust(30), curses.color_pair(4) | curses.A_BOLD)
                stdscr.addstr(y, 33, safe_status.ljust(15), curses.color_pair(4))
                stdscr.addstr(y, 49, safe_runlevel, curses.color_pair(4))
            else:
                stdscr.addstr(y, 2, safe_name.ljust(30), curses.color_pair(6))
                stdscr.addstr(y, 33, safe_status.ljust(15), status_color | curses.A_BOLD)
                stdscr.addstr(y, 49, safe_runlevel, curses.color_pair(3))

        # Окно логов (внизу)
        stdscr.addstr(h-5, 0, "-" * max_w)
        stdscr.addstr(h-4, 2, "Лог действий:", curses.A_BOLD)

        # Показываем последние 2 строки лога
        for idx, log_msg in enumerate(log_messages[-2:]):
            safe_msg = log_msg[:max_w-4].replace('\n', ' ')
            stdscr.addstr(h-3+idx, 2, safe_msg, curses.color_pair(3))

        # Подсказки с защитой от вылета на последней строке
        try:
            bottom_line = " [Мышь/Enter] Выбрать  [R] Обновить  [Q] Выход ".center(max_w)
            stdscr.addstr(h-1, 0, bottom_line, curses.color_pair(4))
        except curses.error:
            pass

        stdscr.refresh()

        # Обработка ввода
        key = stdscr.getch()

        if key == ord('q') or key == ord('Q'):
            break
        elif key == curses.KEY_UP and sel_idx > 0:
            sel_idx -= 1
        elif key == curses.KEY_DOWN and sel_idx < len(services) - 1:
            sel_idx += 1
        elif key == ord('r') or key == ord('R'):
            log_messages.append("Обновление списка сервисов...")
            services = get_services()
        elif key in [curses.KEY_ENTER, 10, 13]:
            # Нажатие Enter - открываем меню
            cmd = show_action_menu(stdscr, services[sel_idx])
            if cmd:
                log_messages.append(f"Выполняю: {cmd}")
                stdscr.refresh()
                res = execute_command(cmd)
                log_messages.append(res)
                services = get_services() # Обновляем статус после действия
        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
                # Если кликнули в области списка
                if list_start_y <= my < list_start_y + list_h:
                    clicked_idx = scroll_offset + (my - list_start_y)
                    if clicked_idx < len(services):
                        sel_idx = clicked_idx
                        # Если одинарный клик или двойной - открываем меню
                        if bstate & curses.BUTTON1_CLICKED or bstate & curses.BUTTON1_DOUBLE_CLICKED or bstate & curses.BUTTON1_PRESSED:
                            cmd = show_action_menu(stdscr, services[sel_idx])
                            if cmd:
                                log_messages.append(f"Выполняю: {cmd}")
                                stdscr.refresh()
                                res = execute_command(cmd)
                                log_messages.append(res)
                                services = get_services()
            except curses.error:
                pass

if __name__ == "__main__":
    curses.wrapper(main)
