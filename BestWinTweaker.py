import psutil
import platform
import datetime
import customtkinter as ctk
import threading
import time
import tkinter as tk
from tkinter import messagebox
import shutil
import winreg
from PIL import Image
import cpuinfo
import multiprocessing

from utilities import *

# Для скрытого опроса видеокарты
import subprocess
import os

# Импортируем Fido интеграцию
from fido_gui import FidoDownloadTab

# Модифицируем subprocess.Popen глобально для всего приложения
_original_popen = subprocess.Popen


def _silent_popen(*args, **kwargs):
    """Глобально скрываем все консольные окна"""
    # Настройки для скрытия окон
    if 'startupinfo' not in kwargs:
        kwargs['startupinfo'] = subprocess.STARTUPINFO()
        kwargs['startupinfo'].dwFlags = subprocess.STARTF_USESHOWWINDOW
        kwargs['startupinfo'].wShowWindow = subprocess.SW_HIDE

    kwargs['creationflags'] = kwargs.get('creationflags', 0) | subprocess.CREATE_NO_WINDOW
    kwargs['stdin'] = subprocess.DEVNULL

    return _original_popen(*args, **kwargs)


# Применяем патч глобально
subprocess.Popen = _silent_popen

# Импортируем GPUtil после патча
import GPUtil

# Настройка внешнего вида customtkinter
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

VERSION = "1.9 beta"


class WindowsTweaker:
    """Класс с инструментами оптимизации Windows"""

    @staticmethod
    def run_cmd(cmd):
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

    @staticmethod
    def clear_temp():
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
                            pass

            return deleted, None
        except Exception as e:
            return 0, str(e)

    @staticmethod
    def disable_telemetry_services():
        """Отключить службы телеметрии"""
        services = [
            "DiagTrack",
            "dmwappushservice"
        ]

        disabled = 0
        errors = []
        for service in services:
            cmd = f'sc config "{service}" start= disabled'
            result = WindowsTweaker.run_cmd(cmd)
            if "успешно" in result.lower() or "success" in result.lower():
                disabled += 1
            else:
                errors.append(service)

        return disabled, errors

    @staticmethod
    def flush_dns():
        """Очистить DNS-кэш"""
        cmd = "ipconfig /flushdns"
        result = WindowsTweaker.run_cmd(cmd)
        if "успешно" in result.lower() or "successful" in result.lower():
            return True, None
        else:
            return False, result

    @staticmethod
    def fix_updates():
        """Исправить ошибки обновлений Windows"""
        try:
            # Останавливаем службы
            stop_cmds = ["net stop wuauserv", "net stop cryptSvc", "net stop bits", "net stop msiserver"]
            for cmd in stop_cmds:
                WindowsTweaker.run_cmd(cmd)

            # Очищаем временные файлы обновлений
            WindowsTweaker.clear_temp()

            # Запускаем службы
            start_cmds = ["net start wuauserv", "net start cryptSvc", "net start bits", "net start msiserver"]
            for cmd in start_cmds:
                WindowsTweaker.run_cmd(cmd)

            # Запускаем поиск обновлений
            WindowsTweaker.run_cmd("wuauclt /detectnow")
            WindowsTweaker.run_cmd("UsoClient ScanInstallWait")

            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def is_indexing_enabled():
        """Проверить включена ли индексация"""
        try:
            cmd = 'sc query "wsearch"'
            result = WindowsTweaker.run_cmd(cmd)
            return '4  RUNNING' in result
        except:
            return False

    @staticmethod
    def disable_indexing():
        """Отключить индексацию"""
        cmd = 'sc config "wsearch" start= disabled'
        WindowsTweaker.run_cmd(cmd)

    @staticmethod
    def enable_indexing():
        """Включить индексацию"""
        cmd = 'sc config "wsearch" start= delayed-auto && sc start "wsearch"'
        WindowsTweaker.run_cmd(cmd)

    @staticmethod
    def get_disabled_folder_path(startup_path):
        """Получить путь к папке с отключенными программами"""
        return os.path.join(os.path.dirname(startup_path), "Disabled_Startup")

    @staticmethod
    def get_startup_folder_programs():
        """Получить программы из папки Startup"""
        startup_programs = []

        startup_paths = [
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'),
            os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'Microsoft', 'Windows', 'Start Menu',
                         'Programs', 'Startup'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Roaming', 'Microsoft', 'Windows', 'Start Menu',
                         'Programs', 'Startup')
        ]

        startup_paths = list(dict.fromkeys(startup_paths))

        for startup_path in startup_paths:
            if os.path.exists(startup_path):
                try:
                    for item in os.listdir(startup_path):
                        item_path = os.path.join(startup_path, item)
                        if os.path.isfile(item_path) and item.lower().endswith(
                                ('.lnk', '.exe', '.bat', '.cmd', '.vbs', '.ps1')):
                            disabled_folder = WindowsTweaker.get_disabled_folder_path(startup_path)
                            disabled_path = os.path.join(disabled_folder, item)

                            startup_programs.append({
                                "type": "folder",
                                "display_name": os.path.splitext(item)[0],
                                "filename": item,
                                "full_path": item_path,
                                "startup_path": startup_path,
                                "disabled_path": disabled_path,
                                "is_disabled": False
                            })
                except Exception:
                    pass

        for startup_path in startup_paths:
            disabled_folder = WindowsTweaker.get_disabled_folder_path(startup_path)
            if os.path.exists(disabled_folder):
                try:
                    for item in os.listdir(disabled_folder):
                        item_path = os.path.join(disabled_folder, item)
                        if os.path.isfile(item_path) and item.lower().endswith(
                                ('.lnk', '.exe', '.bat', '.cmd', '.vbs', '.ps1')):
                            existing = any(
                                p["filename"] == item and p["startup_path"] == startup_path for p in startup_programs)
                            if not existing:
                                startup_programs.append({
                                    "type": "folder",
                                    "display_name": os.path.splitext(item)[0],
                                    "filename": item,
                                    "full_path": os.path.join(startup_path, item),
                                    "startup_path": startup_path,
                                    "disabled_path": item_path,
                                    "is_disabled": True
                                })
                except Exception:
                    pass

        return startup_programs

    @staticmethod
    def get_startup_registry_programs():
        """Получить программы из реестра"""
        startup_programs = []

        registry_paths = [
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run")
        ]

        for hive, reg_path in registry_paths:
            try:
                key = winreg.OpenKey(hive, reg_path, 0, winreg.KEY_READ)
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        is_disabled = name.startswith("Disabled_")
                        original_name = name[9:] if is_disabled else name

                        startup_programs.append({
                            "type": "registry",
                            "display_name": original_name,
                            "original_name": name,
                            "path": value,
                            "reg_hive": hive,
                            "reg_path": reg_path,
                            "is_disabled": is_disabled
                        })
                        i += 1
                    except WindowsError:
                        break
                winreg.CloseKey(key)
            except WindowsError:
                pass

        return startup_programs

    @staticmethod
    def get_all_startup_programs():
        """Получить все программы из автозагрузки"""
        all_programs = WindowsTweaker.get_startup_registry_programs()
        all_programs.extend(WindowsTweaker.get_startup_folder_programs())
        return all_programs

    @staticmethod
    def disable_registry_program(program):
        """Отключить программу из реестра"""
        try:
            key = winreg.OpenKey(program["reg_hive"], program["reg_path"], 0, winreg.KEY_SET_VALUE)
            if not program["original_name"].startswith("Disabled_"):
                winreg.SetValueEx(key, f"Disabled_{program['original_name']}", 0, winreg.REG_SZ, program["path"])
                winreg.DeleteValue(key, program["original_name"])
            winreg.CloseKey(key)
            return True
        except:
            return False

    @staticmethod
    def enable_registry_program(program):
        """Включить программу в реестре"""
        try:
            key = winreg.OpenKey(program["reg_hive"], program["reg_path"], 0, winreg.KEY_SET_VALUE)
            if program["original_name"].startswith("Disabled_"):
                original_name = program["original_name"][9:]
                winreg.SetValueEx(key, original_name, 0, winreg.REG_SZ, program["path"])
                winreg.DeleteValue(key, program["original_name"])
            winreg.CloseKey(key)
            return True
        except:
            return False

    @staticmethod
    def disable_folder_program(program):
        """Отключить программу из папки Startup"""
        try:
            disabled_folder = WindowsTweaker.get_disabled_folder_path(program["startup_path"])
            if not os.path.exists(disabled_folder):
                os.makedirs(disabled_folder)
            if os.path.exists(program["full_path"]):
                shutil.move(program["full_path"], program["disabled_path"])
                return True
            return False
        except:
            return False

    @staticmethod
    def enable_folder_program(program):
        """Включить программу в папку Startup"""
        try:
            if os.path.exists(program["disabled_path"]):
                if not os.path.exists(program["startup_path"]):
                    os.makedirs(program["startup_path"])
                shutil.move(program["disabled_path"], program["full_path"])
                return True
            return False
        except:
            return False


class ModernSystemMonitor:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("BestWinTweaker - Системный монитор и оптимизатор")
        self.window.geometry("1400x750")
        self.window.iconbitmap(resource_path('./resources/images/BestWinTweaker.ico'))

        # Переменные для обновления
        self.running = True
        self.update_interval = 2000

        self.setup_ui()
        self.start_updates()

    def setup_ui(self):
        # Главный контейнер
        self.main_container = ctk.CTkFrame(self.window)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Верхняя панель с заголовком
        self.create_header()

        # Создание вкладок
        self.tabview = ctk.CTkTabview(self.main_container)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Вкладка мониторинга
        self.monitor_tab = self.tabview.add("Мониторинг")
        self.setup_monitor_tab()

        # Вкладка оптимизации
        self.optimize_tab = self.tabview.add("Оптимизация")
        self.setup_optimize_tab()

        # Вкладка автозагрузки
        self.autostart_tab = self.tabview.add("Автозагрузка")
        self.setup_autostart_tab()

        # НОВАЯ ВКЛАДКА: Скачивание Windows через Fido
        self.download_tab = self.tabview.add("Скачать Windows")
        self.fido_widget = FidoDownloadTab(self.download_tab, self)

        # Вкладка О программе
        self.about_tab = self.tabview.add("О программе")
        self.setup_about_tab()

        # Нижняя панель
        self.create_footer()

    def setup_monitor_tab(self):
        """Настройка вкладки мониторинга"""
        # Левая колонка
        left_column = ctk.CTkFrame(self.monitor_tab)
        left_column.pack(side="left", fill="both", expand=True, padx=5)

        # Правая колонка
        right_column = ctk.CTkFrame(self.monitor_tab)
        right_column.pack(side="right", fill="both", expand=True, padx=5)

        # Создаем секции
        self.create_cpu_section(left_column)
        self.create_ram_section(left_column)
        self.create_gpu_section(left_column)
        self.create_network_section(right_column)
        self.create_disk_section(right_column)

    def setup_optimize_tab(self):
        """Настройка вкладки оптимизации"""
        # Контейнер для кнопок
        buttons_container = ctk.CTkFrame(self.optimize_tab)
        buttons_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Заголовок
        title_label = ctk.CTkLabel(
            buttons_container,
            text="Инструменты оптимизации системы",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 20))

        # Фрейм для кнопок (сетка 2x3)
        buttons_grid = ctk.CTkFrame(buttons_container)
        buttons_grid.pack(expand=True)

        # Кнопка очистки временных файлов
        self.clear_temp_btn = ctk.CTkButton(
            buttons_grid,
            text="Очистить временные файлы",
            command=self.action_clear_temp,
            width=250,
            height=60,
            font=ctk.CTkFont(size=14)
        )
        self.clear_temp_btn.grid(row=0, column=0, padx=15, pady=15)

        # Кнопка отключения телеметрии
        self.disable_telemetry_btn = ctk.CTkButton(
            buttons_grid,
            text="Отключить службы телеметрии",
            command=self.action_disable_telemetry,
            width=250,
            height=60,
            font=ctk.CTkFont(size=14)
        )
        self.disable_telemetry_btn.grid(row=0, column=1, padx=15, pady=15)

        # Кнопка очистки DNS
        self.flush_dns_btn = ctk.CTkButton(
            buttons_grid,
            text="Очистить DNS кэш",
            command=self.action_flush_dns,
            width=250,
            height=60,
            font=ctk.CTkFont(size=14)
        )
        self.flush_dns_btn.grid(row=1, column=0, padx=15, pady=15)

        # Кнопка исправления обновлений
        self.fix_updates_btn = ctk.CTkButton(
            buttons_grid,
            text="Исправить ошибки обновлений",
            command=self.action_fix_updates,
            width=250,
            height=60,
            font=ctk.CTkFont(size=14)
        )
        self.fix_updates_btn.grid(row=1, column=1, padx=15, pady=15)

        # Кнопка управления индексацией
        self.indexing_btn_text = ctk.StringVar()
        self.update_indexing_button_text()

        self.indexing_btn = ctk.CTkButton(
            buttons_grid,
            textvariable=self.indexing_btn_text,
            command=self.action_toggle_indexing,
            width=250,
            height=60,
            font=ctk.CTkFont(size=14)
        )
        self.indexing_btn.grid(row=2, column=0, padx=15, pady=15)

        # Кнопка открытия папки Temp
        self.open_temp_btn = ctk.CTkButton(
            buttons_grid,
            text="Открыть папку Temp",
            command=self.action_open_temp,
            width=250,
            height=60,
            font=ctk.CTkFont(size=14)
        )
        self.open_temp_btn.grid(row=2, column=1, padx=15, pady=15)

    def setup_about_tab(self):
        """Настройка вкладки О программе"""
        # Заголовок
        header_frame = ctk.CTkFrame(self.about_tab)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        title_label = ctk.CTkLabel(
            header_frame,
            text="О программе",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(side="top")

        # Центральный фрейм для логотипа
        logo_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        logo_frame.pack(pady=0)

        try:
            logo_img = Image.open(resource_path('./resources/images/BestWinTweaker.png'))
            desired_size = (256, 256)
            logo_img = logo_img.resize(desired_size, Image.Resampling.LANCZOS)
            logo_photo = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=desired_size)
            logo_label = ctk.CTkLabel(logo_frame, image=logo_photo, text="")
            logo_label.image = logo_photo
            logo_label.pack()
        except Exception as e:
            print(f"Ошибка загрузки логотипа: {e}")

        ctk.CTkLabel(header_frame, text="Ускорение ПК в пару кликов!", font=ctk.CTkFont(size=14)).pack()
        ctk.CTkLabel(header_frame, text=f"BestWinTweaker, v. {VERSION}", font=ctk.CTkFont(size=14)).pack()
        GitHubLink = ctk.CTkLabel(header_frame, text="VladislavBanitsky", cursor="hand2", font=ctk.CTkFont(size=14))
        GitHubLink.pack()
        GitHubLink.bind("<Button-1>", lambda e: callback("https://github.com/VladislavBanitsky/BestWinTweaker"))

    def setup_autostart_tab(self):
        """Настройка вкладки автозагрузки"""
        # Заголовок
        header_frame = ctk.CTkFrame(self.autostart_tab)
        header_frame.pack(fill="x", padx=20, pady=(20, 0))

        title_label = ctk.CTkLabel(
            header_frame,
            text="Управление автозагрузкой",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(side="left")

        # Кнопка обновления
        self.refresh_autostart_btn = ctk.CTkButton(
            header_frame,
            text="Обновить",
            command=self.load_autostart_programs,
            width=120
        )
        self.refresh_autostart_btn.pack(side="right")

        # Контейнер со скроллом для списка программ
        self.autostart_container = ctk.CTkScrollableFrame(self.autostart_tab)
        self.autostart_container.pack(fill="both", expand=True, padx=20, pady=0)

        # Кнопки управления
        control_frame = ctk.CTkFrame(self.autostart_tab)
        control_frame.pack(fill="x", padx=20, pady=0)

        self.apply_autostart_btn = ctk.CTkButton(
            control_frame,
            text="Применить изменения",
            command=self.apply_autostart_changes,
            width=150,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.apply_autostart_btn.pack(side="left", padx=5)

        self.select_all_btn = ctk.CTkButton(
            control_frame,
            text="Выбрать все",
            command=self.select_all_autostart,
            width=120
        )
        self.select_all_btn.pack(side="left", padx=5)

        self.deselect_all_btn = ctk.CTkButton(
            control_frame,
            text="Снять все",
            command=self.deselect_all_autostart,
            width=120
        )
        self.deselect_all_btn.pack(side="left", padx=5)

        # Статус
        self.autostart_status_label = ctk.CTkLabel(
            self.autostart_tab,
            text="Загрузка списка программ...",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.autostart_status_label.pack(pady=(0, 10))

        # Загружаем программы
        self.autostart_programs = []
        self.autostart_vars = {}
        self.load_autostart_programs()

    def load_autostart_programs(self):
        """Загрузить программы из автозагрузки"""
        # Очищаем контейнер
        for widget in self.autostart_container.winfo_children():
            widget.destroy()

        self.autostart_programs = WindowsTweaker.get_all_startup_programs()
        self.autostart_vars.clear()

        if not self.autostart_programs:
            empty_label = ctk.CTkLabel(
                self.autostart_container,
                text="Программы в автозагрузке не найдены",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            empty_label.pack(pady=50)
            self.autostart_status_label.configure(text="Программы не найдены")
            return

        # Сортируем программы по имени
        self.autostart_programs.sort(key=lambda x: x["display_name"].lower())

        # Создаем виджеты для каждой программы
        for program in self.autostart_programs:
            program_frame = ctk.CTkFrame(self.autostart_container)
            program_frame.pack(fill="x", padx=10, pady=3)

            # Чекбокс
            var = tk.BooleanVar(value=not program["is_disabled"])
            self.autostart_vars[self.get_program_key(program)] = var

            checkbox = ctk.CTkCheckBox(
                program_frame,
                text=program["display_name"][:30],  # первые 30 символов названия проги
                variable=var,
                font=ctk.CTkFont(size=13)
            )
            checkbox.pack(side="left", padx=10)

            # Статус
            if program["is_disabled"]:
                status_label = ctk.CTkLabel(
                    program_frame,
                    text="Отключена",
                    text_color="red",
                    font=ctk.CTkFont(size=11)
                )
            else:
                status_label = ctk.CTkLabel(
                    program_frame,
                    text="Включена",
                    text_color="green",
                    font=ctk.CTkFont(size=11)
                )
            status_label.pack(side="left", padx=10)

            # Тип программы
            type_text = "Реестр" if program["type"] == "registry" else "Папка"
            type_label = ctk.CTkLabel(
                program_frame,
                text=type_text,
                text_color="orange",
                font=ctk.CTkFont(size=11)
            )
            type_label.pack(side="left", padx=10)

            # Путь (всплывающая подсказка)
            path = program.get("path") or program.get("full_path") or ""
            if path:
                short_path = path[:120] + "..." if len(path) > 120 else path
                path_label = ctk.CTkLabel(
                    program_frame,
                    text=short_path,
                    text_color="gray",
                    font=ctk.CTkFont(size=10)
                )
                path_label.pack(side="right", padx=10)

        self.autostart_status_label.configure(
            text=f"Найдено программ: {len(self.autostart_programs)}"
        )

    def get_program_key(self, program):
        """Получить уникальный ключ программы"""
        if program["type"] == "registry":
            return f"reg_{program['reg_hive']}_{program['reg_path']}_{program['original_name']}"
        else:
            return f"folder_{program['startup_path']}_{program['filename']}"

    def select_all_autostart(self):
        """Выбрать все программы"""
        for var in self.autostart_vars.values():
            var.set(True)

    def deselect_all_autostart(self):
        """Снять все программы"""
        for var in self.autostart_vars.values():
            var.set(False)

    def apply_autostart_changes(self):
        """Применить изменения автозагрузки"""
        changes_count = 0

        for program in self.autostart_programs:
            key = self.get_program_key(program)
            current_state = self.autostart_vars[key].get()  # True - должна быть включена
            actual_state = not program["is_disabled"]  # True - включена

            if current_state != actual_state:
                if program["type"] == "registry":
                    if current_state:
                        success = WindowsTweaker.enable_registry_program(program)
                    else:
                        success = WindowsTweaker.disable_registry_program(program)
                else:
                    if current_state:
                        success = WindowsTweaker.enable_folder_program(program)
                    else:
                        success = WindowsTweaker.disable_folder_program(program)

                if success:
                    changes_count += 1
                    program["is_disabled"] = not current_state

        if changes_count > 0:
            self.autostart_status_label.configure(
                text=f"Изменено программ: {changes_count}. Для полного эффекта перезагрузите компьютер.",
                text_color="green"
            )
            messagebox.showinfo("Успех",
                                f"Изменения применены для {changes_count} программ(ы)!\n\n"
                                "Для полного эффекта рекомендуется перезагрузить компьютер.")
            self.load_autostart_programs()
        else:
            self.autostart_status_label.configure(text="Изменений не было")
            messagebox.showinfo("Информация", "Изменений не было")

    def update_indexing_button_text(self):
        """Обновить текст кнопки индексации"""
        if WindowsTweaker.is_indexing_enabled():
            self.indexing_btn_text.set("Отключить индексацию дисков")
        else:
            self.indexing_btn_text.set("Включить индексацию дисков")

    def action_clear_temp(self):
        """Очистка временных файлов"""
        self.optimize_status_label.configure(text="Очистка временных файлов...", text_color="orange")
        self.window.update()

        deleted, error = WindowsTweaker.clear_temp()

        if error:
            self.optimize_status_label.configure(text=f"Ошибка: {error}", text_color="red")
            messagebox.showerror("Ошибка", f"Не удалось очистить временные файлы:\n{error}")
        else:
            self.optimize_status_label.configure(text=f"Очищено {deleted} файлов", text_color="green")
            messagebox.showinfo("Успех", f"Очищено {deleted} временных файлов")

    def action_disable_telemetry(self):
        """Отключение телеметрии"""
        self.optimize_status_label.configure(text="Отключение служб телеметрии...", text_color="orange")
        self.window.update()

        disabled, errors = WindowsTweaker.disable_telemetry_services()

        if errors:
            self.optimize_status_label.configure(text=f"Отключено {disabled} из {disabled + len(errors)} служб",
                                                 text_color="orange")
            messagebox.showwarning("Предупреждение",
                                   f"Отключено {disabled} служб.\nНе удалось отключить: {', '.join(errors)}")
        else:
            self.optimize_status_label.configure(text=f"Отключено {disabled} служб телеметрии", text_color="green")
            messagebox.showinfo("Успех", f"Успешно отключено {disabled} служб телеметрии")

    def action_flush_dns(self):
        """Очистка DNS"""
        self.optimize_status_label.configure(text="Очистка DNS кэша...", text_color="orange")
        self.window.update()

        success, error = WindowsTweaker.flush_dns()

        if success:
            self.optimize_status_label.configure(text="DNS кэш очищен", text_color="green")
            messagebox.showinfo("Успех", "DNS кэш успешно очищен")
        else:
            self.optimize_status_label.configure(text="Ошибка очистки DNS", text_color="red")
            messagebox.showerror("Ошибка", f"Не удалось очистить DNS кэш:\n{error}")

    def action_fix_updates(self):
        """Исправление обновлений"""
        self.optimize_status_label.configure(text="Исправление ошибок обновлений...", text_color="orange")
        self.window.update()

        success, error = WindowsTweaker.fix_updates()

        if success:
            self.optimize_status_label.configure(text="Обновления исправлены, запущена проверка", text_color="green")
            messagebox.showinfo("Информация",
                                "Проверка обновлений запущена (может занять время).\n"
                                "Проверьте Центр обновлений Windows для отслеживания статуса.")
        else:
            self.optimize_status_label.configure(text="Ошибка при исправлении", text_color="red")
            messagebox.showerror("Ошибка", f"Не удалось исправить ошибки обновлений:\n{error}")

    def action_toggle_indexing(self):
        """Переключение индексации"""
        if WindowsTweaker.is_indexing_enabled():
            self.optimize_status_label.configure(text="Отключение индексации...", text_color="orange")
            self.window.update()
            WindowsTweaker.disable_indexing()
            self.optimize_status_label.configure(text="Индексация дисков отключена", text_color="green")
            messagebox.showinfo("Готово", "Индексация дисков отключена.\nЭто снизит нагрузку на диск.")
        else:
            self.optimize_status_label.configure(text="Включение индексации...", text_color="orange")
            self.window.update()
            WindowsTweaker.enable_indexing()
            self.optimize_status_label.configure(text="Индексация дисков включена", text_color="green")
            messagebox.showinfo("Готово", "Индексация дисков включена.\nПоиск файлов будет быстрее.")

        self.update_indexing_button_text()

    def action_open_temp(self):
        """Открыть папку Temp"""
        temp_path = os.environ.get('TEMP', r"C:\Windows\Temp")
        if os.path.exists(temp_path):
            os.startfile(temp_path)
            self.optimize_status_label.configure(text=f"Открыта папка {temp_path}", text_color="green")
        else:
            self.optimize_status_label.configure(text="Папка Temp не найдена", text_color="red")
            messagebox.showerror("Ошибка", "Папка Temp не найдена")

    def create_header(self):
        header = ctk.CTkFrame(self.main_container, height=60)
        header.pack(fill="x", padx=10, pady=(10, 5))
        header.pack_propagate(False)

        title = ctk.CTkLabel(header, text="BestWinTweaker",
                             font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(side="left", padx=20)

        # Фрейм для переключателя темы
        theme_frame = ctk.CTkFrame(header, fg_color="transparent")
        theme_frame.pack(side="right", padx=20)

        # Переключатель
        self.theme_switch = ctk.CTkSwitch(
            theme_frame,
            text="Светло",
            command=self.toggle_theme,
            width=40,
            height=20,
            switch_width=40,
            switch_height=20
        )
        self.theme_switch.pack(side="left", padx=5)
        self.theme_switch.select()

        sys_info = ctk.CTkLabel(header,
                                text=f"{platform.system()} {platform.release()} | {platform.machine()}",
                                font=ctk.CTkFont(size=16))
        sys_info.pack(side="right", padx=20)

    def toggle_theme(self):
        current_theme = ctk.get_appearance_mode()
        if current_theme == "Dark":
            ctk.set_appearance_mode("Light")
            self.theme_switch.configure(text="Светло")
        else:
            ctk.set_appearance_mode("Dark")
            self.theme_switch.configure(text="Темно")

    def create_cpu_section(self, parent):
        cpu_frame = ctk.CTkFrame(parent)
        cpu_frame.pack(fill="x", padx=10, pady=5)

        cpu_header = ctk.CTkFrame(cpu_frame, height=40)
        cpu_header.pack(fill="x", padx=10, pady=(10, 5))
        cpu_header.pack_propagate(False)

        ctk.CTkLabel(cpu_header, text=f"CPU - Центральный процессор",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        self.cpu_name = ctk.CTkLabel(cpu_frame, text=cpuinfo.get_cpu_info()['brand_raw'],
                                     font=ctk.CTkFont(size=16, weight="bold"))
        self.cpu_name.pack(anchor="w", padx=10, pady=(5, 0))

        self.cpu_progress = ctk.CTkProgressBar(cpu_frame, height=20)
        self.cpu_progress.pack(fill="x", pady=10, padx=20)
        self.cpu_progress.set(0)

        info_frame = ctk.CTkFrame(cpu_frame)
        info_frame.pack(fill="x", padx=20, pady=5)

        self.cpu_percent_label = ctk.CTkLabel(info_frame, text="Загрузка: 0%",
                                              font=ctk.CTkFont(size=16))
        self.cpu_percent_label.pack(side="left", padx=10)

        self.cpu_freq_label = ctk.CTkLabel(info_frame, text="Частота: 0 MHz",
                                           font=ctk.CTkFont(size=16))
        self.cpu_freq_label.pack(side="right", padx=10)

        cores_frame = ctk.CTkFrame(cpu_frame)
        cores_frame.pack(fill="x", padx=20, pady=5)

        cpu_count = psutil.cpu_count()
        self.cores_label = ctk.CTkLabel(cores_frame,
                                        text=f"Ядер: {cpu_count} логических, {psutil.cpu_count(logical=False)} физических",
                                        font=ctk.CTkFont(size=16))
        self.cores_label.pack()

    def create_ram_section(self, parent):
        ram_frame = ctk.CTkFrame(parent)
        ram_frame.pack(fill="x", padx=10, pady=5)

        ram_header = ctk.CTkFrame(ram_frame, height=40)
        ram_header.pack(fill="x", padx=10, pady=(10, 5))
        ram_header.pack_propagate(False)

        ctk.CTkLabel(ram_header, text="RAM - Оперативная память",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        self.ram_progress = ctk.CTkProgressBar(ram_frame, height=20)
        self.ram_progress.pack(fill="x", pady=10, padx=20)
        self.ram_progress.set(0)

        info_frame = ctk.CTkFrame(ram_frame)
        info_frame.pack(fill="x", padx=20, pady=5)

        self.ram_percent_label = ctk.CTkLabel(info_frame, text="Использовано: 0%",
                                              font=ctk.CTkFont(size=16))
        self.ram_percent_label.pack(side="left", padx=10)

        self.ram_usage_label = ctk.CTkLabel(info_frame, text="Использовано: 0 GB / 0 GB",
                                            font=ctk.CTkFont(size=16))
        self.ram_usage_label.pack(side="right", padx=10)

    def create_network_section(self, parent):
        net_frame = ctk.CTkFrame(parent)
        net_frame.pack(fill="x", padx=10, pady=5)

        net_header = ctk.CTkFrame(net_frame, height=40)
        net_header.pack(fill="x", padx=10, pady=(10, 5))
        net_header.pack_propagate(False)

        ctk.CTkLabel(net_header, text="СЕТЬ",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        info_frame = ctk.CTkFrame(net_frame)
        info_frame.pack(fill="x", padx=20, pady=10)

        self.download_label = ctk.CTkLabel(info_frame, text="Загрузка: 0 MB/s",
                                           font=ctk.CTkFont(size=16))
        self.download_label.pack(pady=3)

        self.upload_label = ctk.CTkLabel(info_frame, text="Отдача: 0 MB/s",
                                         font=ctk.CTkFont(size=16))
        self.upload_label.pack(pady=3)

        traffic_frame = ctk.CTkFrame(net_frame)
        traffic_frame.pack(fill="x", padx=20, pady=5)

        self.total_download_label = ctk.CTkLabel(traffic_frame, text="Всего скачано: 0 GB",
                                                 font=ctk.CTkFont(size=16))
        self.total_download_label.pack(pady=2)

        self.total_upload_label = ctk.CTkLabel(traffic_frame, text="Всего отправлено: 0 GB",
                                               font=ctk.CTkFont(size=16))
        self.total_upload_label.pack(pady=2)

        self.prev_net = psutil.net_io_counters()
        self.prev_time = time.time()

    def create_disk_section(self, parent):
        disk_frame = ctk.CTkFrame(parent)
        disk_frame.pack(fill="x", padx=10, pady=5)

        disk_header = ctk.CTkFrame(disk_frame, height=40)
        disk_header.pack(fill="x", padx=10, pady=(10, 5))
        disk_header.pack_propagate(False)

        ctk.CTkLabel(disk_header, text="ДИСКИ",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        self.disk_container = ctk.CTkFrame(disk_frame)
        self.disk_container.pack(fill="x", padx=20, pady=10)

        self.disk_widgets = {}

    def create_gpu_section(self, parent):
        gpu_frame = ctk.CTkFrame(parent)
        gpu_frame.pack(fill="x", padx=10, pady=5)

        gpu_header = ctk.CTkFrame(gpu_frame, height=40)
        gpu_header.pack(fill="x", padx=10, pady=(10, 5))
        gpu_header.pack_propagate(False)

        ctk.CTkLabel(gpu_header, text="GPU - Видеокарта",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        self.gpu_container = ctk.CTkFrame(gpu_frame)
        self.gpu_container.pack(fill="x", padx=20, pady=10)

        self.gpu_label = ctk.CTkLabel(self.gpu_container, text="Поиск GPU...",
                                      font=ctk.CTkFont(size=16))
        self.gpu_label.pack(pady=10)
        self.gpu_widgets = {}

    def create_footer(self):
        footer = ctk.CTkFrame(self.main_container, height=40)
        footer.pack(fill="x", padx=10, pady=(5, 10))
        footer.pack_propagate(False)

        self.time_label = ctk.CTkLabel(footer, text="", font=ctk.CTkFont(size=16))
        self.time_label.pack(side="right", padx=20)

        # Статус операций
        self.optimize_status_label = ctk.CTkLabel(
            footer,
            text="Готов",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.optimize_status_label.pack(side="left", padx=20)

    def update_stats(self):
        while self.running:
            try:
                self.window.after(0, self.update_cpu_info)
                self.window.after(0, self.update_ram_info)
                self.window.after(0, self.update_network_info)
                self.window.after(0, self.update_disk_info)
                self.window.after(0, self.update_gpu_info)
                self.window.after(0, self.update_time_info)

                time.sleep(self.update_interval / 1000)
            except Exception as e:
                print(f"Error in update thread: {e}")
                time.sleep(1)

    def update_cpu_info(self):
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            self.cpu_progress.set(cpu_percent / 100)
            self.cpu_percent_label.configure(text=f"Загрузка: {cpu_percent:.1f}%")

            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                self.cpu_freq_label.configure(text=f"Частота: {cpu_freq.current:.0f} MHz")
        except Exception as e:
            print(f"CPU update error: {e}")

    def update_ram_info(self):
        try:
            ram = psutil.virtual_memory()
            self.ram_progress.set(ram.percent / 100)
            self.ram_percent_label.configure(text=f"Использовано: {ram.percent:.1f}%")

            ram_used_gb = ram.used / (1024 ** 3)
            ram_total_gb = ram.total / (1024 ** 3)
            self.ram_usage_label.configure(text=f"Использовано: {ram_used_gb:.1f} GB / {ram_total_gb:.1f} GB")
        except Exception as e:
            print(f"RAM update error: {e}")

    def update_network_info(self):
        try:
            current_net = psutil.net_io_counters()
            current_time = time.time()

            time_diff = current_time - self.prev_time
            if time_diff > 0:
                download_speed = (current_net.bytes_recv - self.prev_net.bytes_recv) / time_diff / (1024 ** 2)
                upload_speed = (current_net.bytes_sent - self.prev_net.bytes_sent) / time_diff / (1024 ** 2)

                self.download_label.configure(text=f"Загрузка: {download_speed:.2f} MB/s")
                self.upload_label.configure(text=f"Отдача: {upload_speed:.2f} MB/s")

            total_download_gb = current_net.bytes_recv / (1024 ** 3)
            total_upload_gb = current_net.bytes_sent / (1024 ** 3)
            self.total_download_label.configure(text=f"Всего скачано: {total_download_gb:.2f} GB")
            self.total_upload_label.configure(text=f"Всего отправлено: {total_upload_gb:.2f} GB")

            self.prev_net = current_net
            self.prev_time = current_time
        except Exception as e:
            print(f"Network update error: {e}")

    def update_disk_info(self):
        try:
            current_disks = {}
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    current_disks[partition.device] = {
                        'mount': partition.mountpoint,
                        'percent': usage.percent,
                        'used': usage.used,
                        'total': usage.total
                    }
                except:
                    pass

            for device in list(self.disk_widgets.keys()):
                if device not in current_disks:
                    for widget in self.disk_widgets[device]:
                        widget.destroy()
                    del self.disk_widgets[device]

            for device, info in current_disks.items():
                if device not in self.disk_widgets:
                    disk_frame = ctk.CTkFrame(self.disk_container)
                    disk_frame.pack(fill="x", pady=2)

                    name_label = ctk.CTkLabel(disk_frame, text=f"{device} ({info['mount']})",
                                              font=ctk.CTkFont(size=16, weight="bold"))
                    name_label.pack(anchor="w", padx=5, pady=(2, 0))

                    progress = ctk.CTkProgressBar(disk_frame, height=20)
                    progress.pack(fill="x", padx=5, pady=2)

                    info_label = ctk.CTkLabel(disk_frame, text="",
                                              font=ctk.CTkFont(size=16))
                    info_label.pack(anchor="w", padx=5, pady=(0, 2))

                    self.disk_widgets[device] = [disk_frame, name_label, progress, info_label]

                _, _, progress, info_label = self.disk_widgets[device]
                used_gb = info['used'] / (1024 ** 3)
                total_gb = info['total'] / (1024 ** 3)

                progress.set(info['percent'] / 100)
                info_label.configure(text=f"Использовано: {info['percent']:.1f}% ({used_gb:.1f}/{total_gb:.1f} GB)")
        except Exception as e:
            print(f"Disk update error: {e}")

    def update_gpu_info(self):
        """Обновление информации о GPU в отдельном потоке (без зависаний)"""
        try:
            # Запускаем обновление в потоке
            if not hasattr(self, '_gpu_updating'):
                self._gpu_updating = False

            if self._gpu_updating:
                return  # Предыдущее обновление еще выполняется

            self._gpu_updating = True

            def _update_gpu_in_thread():
                try:
                    # Устанавливаем таймаут для GPU-запросов через отдельный поток
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(GPUtil.getGPUs)
                        try:
                            gpus = future.result(timeout=2.0)  # 2 секунды таймаут
                        except concurrent.futures.TimeoutError:
                            print("GPU check timeout")
                            gpus = []
                except Exception as e:
                    print(f"GPU check error: {e}")
                    gpus = []

                # Обновляем UI в главном потоке
                self.window.after(0, lambda: self._update_gpu_ui(gpus))
                self._gpu_updating = False

            threading.Thread(target=_update_gpu_in_thread, daemon=True).start()

        except Exception as e:
            print(f"GPU update error: {e}")
            self._gpu_updating = False

    def _update_gpu_ui(self, gpus):
        """Обновление UI с информацией о GPU (выполняется в главном потоке)"""
        try:
            if not gpus:
                for widgets in self.gpu_widgets.values():
                    for widget in widgets:
                        widget.destroy()
                self.gpu_widgets.clear()
                self.gpu_label.configure(text="GPU не обнаружен")
                self.gpu_label.pack(pady=10)
                return

            self.gpu_label.pack_forget()

            for i, gpu in enumerate(gpus):
                gpu_id = f"gpu_{i}"

                if gpu_id not in self.gpu_widgets:
                    gpu_card_frame = ctk.CTkFrame(self.gpu_container)
                    gpu_card_frame.pack(fill="x", pady=0)

                    name_label = ctk.CTkLabel(gpu_card_frame, text=gpu.name,
                                              font=ctk.CTkFont(size=16, weight="bold"))
                    name_label.pack(anchor="w", padx=10, pady=(5, 0))

                    load_progress = ctk.CTkProgressBar(gpu_card_frame, height=20)
                    load_progress.pack(fill="x", padx=10, pady=5)

                    info_label = ctk.CTkLabel(gpu_card_frame, text="",
                                              font=ctk.CTkFont(size=16))
                    info_label.pack(anchor="w", padx=10, pady=(0, 5))

                    self.gpu_widgets[gpu_id] = [gpu_card_frame, name_label, load_progress, info_label]

                _, _, load_progress, info_label = self.gpu_widgets[gpu_id]
                gpu_load = gpu.load * 100

                load_progress.set(gpu_load / 100)
                info_label.configure(
                    text=f"Загрузка: {gpu_load:.1f}% | Температура: {gpu.temperature:.0f}°C | "
                         f"Память: {gpu.memoryUtil * 100:.1f}% | VRAM: {gpu.memoryUsed:.0f}/{gpu.memoryTotal:.0f} MB"
                )

            for gpu_id in list(self.gpu_widgets.keys()):
                if int(gpu_id.split('_')[1]) >= len(gpus):
                    for widget in self.gpu_widgets[gpu_id]:
                        widget.destroy()
                    del self.gpu_widgets[gpu_id]
        except Exception as e:
            print(f"GPU UI update error: {e}")

    def update_time_info(self):
        try:
            current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.configure(text=f"{current_time_str}")
        except Exception as e:
            print(f"Time update error: {e}")

    def start_updates(self):
        """Запуск всех потоков обновления"""
        self.update_thread = threading.Thread(target=self.update_stats, daemon=True)
        self.update_thread.start()
        # Добавляем переменную для отслеживания потоков GPU
        self._gpu_updating = False

    def run(self):
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()

    def on_closing(self):
        self.running = False
        self.window.quit()
        self.window.destroy()


if __name__ == "__main__":
    # Pyinstaller fix
    multiprocessing.freeze_support()
    app = ModernSystemMonitor()
    app.run()