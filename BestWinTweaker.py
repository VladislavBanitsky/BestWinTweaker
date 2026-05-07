# ==============================================================================================
# Простое оконное приложение для оптимизации ПК.
# Почистите мусор в системных папках, отключите службы телеметрии, сбросьте DNS, 
# исправьте ошибки центра обновлений Windows или отключите индексацию на медленном HDD.
# Ускорение ПК в пару кликов!
# GitHub: https://github.com/VladislavBanitsky/BestWinTweaker
# Разработчик: Владислав Баницкий
# Версия: 0.0.6
# Обновлено: 15.01.2026  
# ==============================================================================================

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import shutil
import winreg
from PIL import Image, ImageTk
from utilities import *

VERSION = "0.0.6"
WIDTH = 300
HEIGHT = 300

class WindowsTweaker:
    def __init__(self, root):
        self.root = root
        self.root.title("BestWinTweaker")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)
        self.root.iconbitmap(resource_path('./resources/images/BestWinTweaker.ico'))
                
        # Основные кнопки-действия
        buttons_frame = ttk.Frame(self.root)
        buttons_frame.pack(pady=10, padx=20, fill="x")       
        
        self.clear_button = ttk.Button(
            buttons_frame,
            text="Очистить временные файлы",
            command=self.clear_temp,
            width=40
        )
        self.clear_button.grid(row=0, column=0, pady=5, padx=5)
        
        # Привязываем события
        self.clear_button.bind("<Enter>", lambda event: self.status_var.set("Очистка папок temp, SoftwareDistribution и Prefetch"))
        self.clear_button.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        
        self.button_disable_services = ttk.Button(
            buttons_frame,
            text="Отключить службы телеметрии",
            command=self.disable_services,
            width=40
        )
        self.button_disable_services.grid(row=1, column=0, pady=5)
        
        # Привязываем события
        self.button_disable_services.bind("<Enter>", lambda event: self.status_var.set("Отключение служб DiagTrack и dmwappushservice"))
        self.button_disable_services.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        
        self.button_flush_dns = ttk.Button(
            buttons_frame,
            text="Очистить DNS",
            command=self.flush_dns,
            width=40
        )
        self.button_flush_dns.grid(row=2, column=0, pady=5)
        
        # Привязываем события
        self.button_flush_dns.bind("<Enter>", lambda event: self.status_var.set("Исправление проблем с доступом к сайтам"))
        self.button_flush_dns.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        
        self.fix_updates_button = ttk.Button(
            buttons_frame,
            text="Исправить ошибки обновлений",
            command=self.fix_updates,
            width=40
        )
        self.fix_updates_button.grid(row=3, column=0, pady=5)
        
        # Привязываем события
        self.fix_updates_button.bind("<Enter>", lambda event: self.status_var.set("Исправление ошибок Центра обновлений"))
        self.fix_updates_button.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        
        # Кнопка для управления автозагрузкой
        self.manage_autostart_button = ttk.Button(
            buttons_frame,
            text="Управление автозагрузкой",
            command=self.manage_autostart,
            width=40
        )
        self.manage_autostart_button.grid(row=4, column=0, pady=5)
        
        # Привязываем события
        self.manage_autostart_button.bind("<Enter>", lambda event: self.status_var.set("Выбор программ для автозагрузки (реестр + папка Startup)"))
        self.manage_autostart_button.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        
        if self.is_indexing_enabled():
            self.disable_indexing_button = ttk.Button(
                buttons_frame,
                text="Отключить индексацию",
                command=self.disable_indexing,
                width=40
            )
            self.disable_indexing_button.grid(row=5, column=0, pady=5)
            
            # Привязываем события
            self.disable_indexing_button.bind("<Enter>", lambda event: self.status_var.set("Снижение нагрузки на HDD/SSD"))
            self.disable_indexing_button.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        else:
            self.enable_indexing_button = ttk.Button(
                buttons_frame,
                text="Включить индексацию",
                command=self.enable_indexing,
                width=40
            )
            self.enable_indexing_button.grid(row=5, column=0, pady=5)
            
            # Привязываем события
            self.enable_indexing_button.bind("<Enter>", lambda event: self.status_var.set("Включает поиск по содержимому файлов, именам и метаданным"))
            self.enable_indexing_button.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        
        self.about = ttk.Button(
            buttons_frame,
            text="О программе",
            command=self.about,
            width=40
        )
        self.about.grid(row=6, column=0, pady=5)
        
        # Привязываем события
        self.about.bind("<Enter>", lambda event: self.status_var.set("Сведения о программе :)"))
        self.about.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        
        # Статус-бар
        self.status_var = tk.StringVar()
        self.status_var.set("Готов")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief="flat",
            anchor="center",
            font=("TkDefaultFont", 9),
            background="#00f000"
        )
        status_bar.pack(side="bottom", fill="x")
        
    def run_cmd(self, cmd):
        """Выполнить командную строку и вернуть результат"""
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                check=True,
                encoding='cp866'
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"!Ошибка: {e}"

    def clear_temp(self, msg=True):
        """Очистить временные файлы Windows"""
        try:
            temp_dirs = [
                os.environ.get('TEMP'),
                os.environ.get('TMP'),
                r"C:\Windows\Temp",
                r"C:\Windows\SoftwareDistribution\Download",
                r"C:\Windows\Prefetch"
            ]

            deleted = 0
            for temp_dir in temp_dirs:
                if temp_dir and os.path.exists(temp_dir):
                    for item in os.listdir(temp_dir):
                        item_path = os.path.join(temp_dir, item)
                        try:
                            if os.path.isfile(item_path):
                                os.remove(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            deleted += 1
                        except:
                            pass  # Пропускаем недоступные файлы
            
            if msg == True:
                self.status_var.set(f"Очищено {deleted} временных файлов")
                messagebox.showinfo("Успех", f"Очищено {deleted} файлов")
        except Exception as e:
            self.status_var.set(f"Ошибка очистки: {e}")
            messagebox.showerror("Ошибка", str(e))
    
    def disable_services(self):
        """Отключить некоторые ненужные службы (пример: телеметрия)"""
        services = [
            "DiagTrack",      # Служба диагностики
            "dmwappushservice" # Телеметрия
        ]
        
        disabled = 0
        for service in services:
            cmd = f'sc config "{service}" start= disabled'
            result = self.run_cmd(cmd)
            if "успешно" in result.lower() or "success" in result.lower():
                disabled += 1
        
        self.status_var.set(f"Отключено {disabled} служб")
        messagebox.showinfo("Готово", f"Отключено {disabled} служб")

    def flush_dns(self):
        """Обновить/очистить DNS-кэш"""
        cmd = "ipconfig /flushdns"
        result = self.run_cmd(cmd)
        if "успешно" in result.lower() or "successful" in result.lower():
            self.status_var.set("DNS-кэш очищен")
            messagebox.showinfo("Готово", "DNS-кэш очищен")
        else:
            self.status_var.set("Ошибка очистки DNS")
            messagebox.showerror("Ошибка", result)
    
    def fix_updates(self):
        """Исправление ошибок обновлений Windows"""
        # Останавливаем службы обновлений
        cmds = ["net stop wuauserv", "net stop cryptSvc", "net stop bits", "net stop msiserver"]
        for cmd in cmds:
            result = self.run_cmd(cmd)
        # Очищаем файлы обновлений
        self.clear_temp(False)
        # Включаем службы обновлений
        cmds = ["net start wuauserv", "net start cryptSvc", "net start bits", "net start msiserver"]
        for cmd in cmds:
            result = self.run_cmd(cmd)
        self.status_var.set("Исправление ошибок обновлений выполнено")
        cmd = "wuauclt /detectnow"  # для Windows 7/8
        result = self.run_cmd(cmd)
        cmd = "UsoClient ScanInstallWait" # для Windows 10/11
        result = self.run_cmd(cmd)
        self.status_var.set("Проверка обновлений запущена")
        messagebox.showinfo("Информация", "Проверка обновлений запущена (может занять время). Проверьте Центр обновлений Windows :)")
    
    def get_startup_folder_programs(self):
        """Получить программы из папки Startup"""
        startup_programs = []
        
        # Правильные пути к папке Startup
        # Для текущего пользователя: %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
        # Для всех пользователей: %PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Startup
        
        startup_paths = [
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'),
            os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'),
            # Альтернативный путь для некоторых версий Windows
            os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Roaming', 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        ]
        
        # Убираем дубликаты
        startup_paths = list(dict.fromkeys(startup_paths))
        
        print("=== Поиск папок Startup ===")
        for startup_path in startup_paths:
            print(f"Проверяем путь: {startup_path}")
            if os.path.exists(startup_path):
                print(f"  ✅ Папка найдена!")
                try:
                    items = os.listdir(startup_path)
                    print(f"  Найдено элементов: {len(items)}")
                    
                    for item in items:
                        item_path = os.path.join(startup_path, item)
                        # Проверяем, что это файл
                        if os.path.isfile(item_path):
                            # Показываем только .lnk, .exe, .bat, .cmd, .vbs
                            if item.lower().endswith(('.lnk', '.exe', '.bat', '.cmd', '.vbs', '.ps1')):
                                print(f"    - {item}")
                                startup_programs.append({
                                    "type": "folder",
                                    "display_name": os.path.splitext(item)[0],
                                    "filename": item,
                                    "full_path": item_path,
                                    "startup_path": startup_path,
                                    "is_disabled": False,
                                    "backup_path": None
                                })
                            else:
                                print(f"    - {item} (пропущен, не является исполняемым файлом)")
                except Exception as e:
                    print(f"  ❌ Ошибка при чтении папки: {e}")
            else:
                print(f"  ❌ Папка не найдена")
        
        print(f"✅ Всего найдено программ в папке Startup: {len(startup_programs)}")
        return startup_programs
    
    def get_startup_registry_programs(self):
        """Получить программы из реестра"""
        startup_programs = []
        
        # Пути к автозагрузке в реестре
        registry_paths = [
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run")
        ]
        
        print("\n=== Поиск программ в реестре ===")
        for hive, reg_path in registry_paths:
            try:
                key = winreg.OpenKey(hive, reg_path, 0, winreg.KEY_READ)
                i = 0
                count = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        # Проверяем, не отключена ли уже программа
                        is_disabled = name.startswith("Disabled_")
                        original_name = name[9:] if is_disabled else name
                        actual_name = original_name if is_disabled else name
                        
                        print(f"  Найдено: {actual_name} -> {value[:50]}...")
                        
                        startup_programs.append({
                            "type": "registry",
                            "display_name": actual_name,
                            "original_name": name,
                            "path": value,
                            "reg_hive": hive,
                            "reg_path": reg_path,
                            "is_disabled": is_disabled
                        })
                        i += 1
                        count += 1
                    except WindowsError:
                        break
                winreg.CloseKey(key)
                print(f"  Всего в {reg_path}: {count} записей")
            except WindowsError:
                print(f"  Путь {reg_path} не найден")
        
        print(f"✅ Всего найдено программ в реестре: {len(startup_programs)}")
        return startup_programs
    
    def get_all_startup_programs(self):
        """Получить все программы из автозагрузки (реестр + папка)"""
        all_programs = []
        
        print("\n" + "="*50)
        print("ПОИСК ПРОГРАММ В АВТОЗАГРУЗКЕ")
        print("="*50)
        
        # Программы из реестра
        registry_programs = self.get_startup_registry_programs()
        all_programs.extend(registry_programs)
        
        # Программы из папки Startup
        folder_programs = self.get_startup_folder_programs()
        all_programs.extend(folder_programs)
        
        print("\n" + "="*50)
        print(f"ИТОГО НАЙДЕНО: {len(all_programs)} программ")
        print("="*50 + "\n")
        
        return all_programs
    
    def manage_autostart(self):
        """Открыть окно управления автозагрузкой с выбором программ"""
        # Получаем список программ
        programs = self.get_all_startup_programs()
        
        if not programs:
            messagebox.showinfo("Информация", "Программы в автозагрузке не найдены!\n\nПроверьте:\n- Папку Startup\n- Реестр Windows")
            return
        
        # Создаем окно
        autostart_window = tk.Toplevel(self.root)
        autostart_window.title("Управление автозагрузкой")
        autostart_window.geometry("650x550")
        autostart_window.resizable(False, False)
        
        # Инструкция
        info_label = tk.Label(
            autostart_window, 
            text=f"Выберите программы, которые хотите отключить в автозагрузке (найдено: {len(programs)})",
            font=("TkDefaultFont", 10, "bold"),
            pady=10
        )
        info_label.pack()
        
        # Фрейм с чекбоксами (с прокруткой)
        frame_canvas = tk.Frame(autostart_window)
        frame_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        canvas = tk.Canvas(frame_canvas)
        scrollbar = ttk.Scrollbar(frame_canvas, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill=tk.BOTH, expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Список чекбоксов
        checkboxes = []
        
        # Разделитель для реестра
        reg_programs = [p for p in programs if p["type"] == "registry"]
        if reg_programs:
            reg_label = tk.Label(
                scrollable_frame,
                text=f"Программы из реестра ({len(reg_programs)}):",
                font=("TkDefaultFont", 9, "bold"),
                fg="blue",
                pady=5
            )
            reg_label.pack(anchor="w", padx=5)
        
        for program in reg_programs:
            var = tk.BooleanVar(value=program["is_disabled"])
            cb_frame = tk.Frame(scrollable_frame)
            cb_frame.pack(fill="x", padx=20, pady=2)
            
            cb = tk.Checkbutton(
                cb_frame,
                text=program["display_name"],
                variable=var,
                anchor="w"
            )
            cb.pack(side="left")
            
            # Индикатор статуса
            if program["is_disabled"]:
                status_label = tk.Label(cb_frame, text=" [ОТКЛЮЧЕНА]", fg="red", font=("TkDefaultFont", 8))
                status_label.pack(side="left", padx=5)
            
            cb_frame.pack(fill="x", padx=5)
            
            # Подпись с путем
            path_text = program["path"][:80] + "..." if len(program["path"]) > 80 else program["path"]
            path_label = tk.Label(
                scrollable_frame,
                text=f"  {path_text}",
                font=("TkDefaultFont", 8),
                fg="gray",
                anchor="w",
                wraplength=600
            )
            path_label.pack(fill="x", padx=35, pady=5)
            
            checkboxes.append({
                "program": program,
                "var": var,
                "type": "registry"
            })
        
        # Разделитель для папки Startup
        folder_programs = [p for p in programs if p["type"] == "folder"]
        if folder_programs:
            folder_label = tk.Label(
                scrollable_frame,
                text=f"Программы из папки Startup ({len(folder_programs)}):",
                font=("TkDefaultFont", 9, "bold"),
                fg="green",
                pady=5
            )
            folder_label.pack(anchor="w", padx=5)
        
        for program in folder_programs:
            var = tk.BooleanVar(value=False)
            cb_frame = tk.Frame(scrollable_frame)
            cb_frame.pack(fill="x", padx=20, pady=2)
            
            cb = tk.Checkbutton(
                cb_frame,
                text=program["display_name"],
                variable=var,
                anchor="w"
            )
            cb.pack(side="left")
            
            # Показываем тип файла
            file_ext = os.path.splitext(program["filename"])[1].upper()
            type_label = tk.Label(cb_frame, text=f" [{file_ext}]", fg="orange", font=("TkDefaultFont", 8))
            type_label.pack(side="left", padx=5)
            
            cb_frame.pack(fill="x", padx=5)
            
            # Подпись с путем
            path_label = tk.Label(
                scrollable_frame,
                text=f"  {program['full_path']}",
                font=("TkDefaultFont", 8),
                fg="gray",
                anchor="w",
                wraplength=600
            )
            path_label.pack(fill="x", padx=35, pady=(0, 5))
            
            checkboxes.append({
                "program": program,
                "var": var,
                "type": "folder"
            })
        
        # Если нет программ в папке, покажем сообщение
        if not folder_programs and reg_programs:
            info_folder = tk.Label(
                scrollable_frame,
                text="  ℹ️ В папке Startup нет программ",
                font=("TkDefaultFont", 8, "italic"),
                fg="gray",
                anchor="w"
            )
            info_folder.pack(fill="x", padx=35, pady=5)
        
        # Кнопки действий
        button_frame = tk.Frame(autostart_window)
        button_frame.pack(pady=10)
        
        def apply_changes():
            """Применить изменения"""
            changes_made = False
            for item in checkboxes:
                program = item["program"]
                should_be_disabled = item["var"].get()
                
                if program["type"] == "registry":
                    if should_be_disabled and not program["is_disabled"]:
                        # Отключаем программу из реестра
                        self.disable_single_program(program)
                        changes_made = True
                    elif not should_be_disabled and program["is_disabled"]:
                        # Включаем программу обратно в реестр
                        self.enable_single_program(program)
                        changes_made = True
                
                elif program["type"] == "folder":
                    if should_be_disabled and not program.get("is_disabled", False):
                        # Перемещаем ярлык в папку Disabled_Startup
                        self.disable_folder_program(program)
                        changes_made = True
                    elif not should_be_disabled and program.get("is_disabled", False):
                        # Восстанавливаем ярлык из папки Disabled_Startup
                        self.enable_folder_program(program)
                        changes_made = True
            
            if changes_made:
                self.status_var.set("Изменения в автозагрузке применены")
                messagebox.showinfo("Успех", "Изменения в автозагрузке применены!\nДля полного эффекта рекомендуется перезагрузить компьютер.")
                autostart_window.destroy()
            else:
                messagebox.showinfo("Информация", "Изменений не было")
                autostart_window.destroy()
        
        def select_all():
            """Выбрать все"""
            for item in checkboxes:
                item["var"].set(True)
        
        def deselect_all():
            """Снять все"""
            for item in checkboxes:
                item["var"].set(False)
        
        ttk.Button(button_frame, text="Применить", command=apply_changes).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Выбрать всё", command=select_all).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Снять всё", command=deselect_all).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Отмена", command=autostart_window.destroy).pack(side="left", padx=5)
    
    def disable_single_program(self, program):
        """Отключить одну программу из реестра"""
        try:
            key = winreg.OpenKey(program["reg_hive"], program["reg_path"], 0, winreg.KEY_SET_VALUE)
            if not program["original_name"].startswith("Disabled_"):
                winreg.SetValueEx(key, f"Disabled_{program['original_name']}", 0, winreg.REG_SZ, program["path"])
                winreg.DeleteValue(key, program["original_name"])
            winreg.CloseKey(key)
            program["is_disabled"] = True
        except WindowsError as e:
            print(f"Ошибка при отключении {program['display_name']}: {e}")
    
    def enable_single_program(self, program):
        """Включить одну программу обратно в реестр"""
        try:
            key = winreg.OpenKey(program["reg_hive"], program["reg_path"], 0, winreg.KEY_SET_VALUE)
            if program["original_name"].startswith("Disabled_"):
                original_name = program["original_name"][9:]
                winreg.SetValueEx(key, original_name, 0, winreg.REG_SZ, program["path"])
                winreg.DeleteValue(key, program["original_name"])
            winreg.CloseKey(key)
            program["is_disabled"] = False
        except WindowsError as e:
            print(f"Ошибка при включении {program['display_name']}: {e}")
    
    def disable_folder_program(self, program):
        """Отключить программу из папки Startup (переместить в папку Disabled_Startup)"""
        try:
            # Создаем папку для отключенных программ
            disabled_folder = os.path.join(program["startup_path"], "..", "Disabled_Startup")
            disabled_folder = os.path.normpath(disabled_folder)
            
            if not os.path.exists(disabled_folder):
                os.makedirs(disabled_folder)
                print(f"Создана папка: {disabled_folder}")
            
            # Новый путь для файла
            new_path = os.path.join(disabled_folder, program["filename"])
            
            # Перемещаем файл
            shutil.move(program["full_path"], new_path)
            print(f"Перемещён файл: {program['filename']} -> {disabled_folder}")
            
            # Сохраняем информацию для восстановления
            program["backup_path"] = new_path
            program["is_disabled"] = True
            
        except Exception as e:
            print(f"Ошибка при отключении {program['display_name']}: {e}")
            messagebox.showerror("Ошибка", f"Не удалось отключить {program['display_name']}: {str(e)}")
    
    def enable_folder_program(self, program):
        """Включить программу обратно в папку Startup"""
        try:
            if program.get("backup_path") and os.path.exists(program["backup_path"]):
                # Перемещаем обратно
                shutil.move(program["backup_path"], program["full_path"])
                print(f"Восстановлен файл: {program['filename']}")
                program["is_disabled"] = False
                program["backup_path"] = None
        except Exception as e:
            print(f"Ошибка при включении {program['display_name']}: {e}")
            messagebox.showerror("Ошибка", f"Не удалось включить {program['display_name']}: {str(e)}")
    
    def is_indexing_enabled(self):
        try:
            # Выполняем команду sc query для службы Windows Search
            cmd = 'sc query "wsearch"'
            result = self.run_cmd(cmd)
            # Проверяем, есть ли в выводе STATE : 4 RUNNING
            if '4  RUNNING' in result:
                return True
            else:
                return False
        except Exception as e:
            print(f"Ошибка при проверке состояния индексации: {e}")
            return False
    
    def disable_indexing(self):
        """Отключить индексацию"""
        cmd = 'sc config "wsearch" start= disabled'
        result = self.run_cmd(cmd)        
        self.status_var.set("Индексация дисков отключена")
        messagebox.showinfo("Готово", "Индексация дисков отключена")
    
    def enable_indexing(self):
        """Включить индексацию"""
        cmd = 'sc config "wsearch" start=delayed-auto && sc start "wsearch"'
        result = self.run_cmd(cmd)        
        self.status_var.set("Индексация дисков включена")
        messagebox.showinfo("Готово", "Индексация дисков включена")
    
    def about(self):
        """ Окно с данными об устройстве """
        pc_window = tk.Toplevel(self.root)
        pc_window.title(f"BestWinTweaker О программе")
        pc_window.resizable(width=False, height=False)
        pc_window.iconbitmap(resource_path('./resources/images/BestWinTweaker.ico'))
        pc_window.geometry(f"{WIDTH}x{HEIGHT}")
        logo_img = Image.open(resource_path('./resources/images/BestWinTweaker.png'))
        logo_img = logo_img.resize((180, 180), Image.LANCZOS)
        logo_photo = ImageTk.PhotoImage(logo_img)
        logo_label = tk.Label(pc_window, image=logo_photo)
        logo_label.image = logo_photo
        logo_label.pack()
        tk.Label(pc_window, text="Ускорение ПК в пару кликов!").pack()
        tk.Label(pc_window, text=f"BestWinTweaker, v. {VERSION}").pack()
        GitHubLink = tk.Label(pc_window, text="VladislavBanitsky", fg="blue", cursor="hand2", font=["Segoe UI", 9, "underline"])
        GitHubLink.pack()
        GitHubLink.bind("<Button-1>", lambda e: callback("https://github.com/VladislavBanitsky/BestWinTweaker"))
    
        
if __name__ == "__main__":
    root = tk.Tk()
    app = WindowsTweaker(root)
    root.mainloop()