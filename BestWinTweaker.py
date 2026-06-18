import psutil
import platform
import datetime
import threading
import time
from PIL import Image
import cpuinfo
import json
import re
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from utilities import no_show_gpu, get_disk_type, get_ddr_info, get_ddr_type, get_board_model, resource_path, callback, get_windows_version, start_download
from uwpremover import *
from TweakerTools import *

# Настройка внешнего вида customtkinter
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

VERSION = "1.9.2"

# Для скрытого опроса видеокарты
import subprocess
import os

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


class BestWinTweaker:
    """Класс графического интерфейса"""
    
    def __init__(self, initial_data):
        self.initial_data = initial_data or {}
        self.window = ctk.CTk()
        self.window.title("BestWinTweaker - Системный монитор и оптимизатор")
        self.window.geometry("1400x750")
        self.window.iconbitmap(resource_path('./resources/images/BestWinTweaker.ico'))

        # Переменные для обновления
        self.running = True
        self.update_interval = 2000
        self._gpu_detected = False  # Добавьте эту строку
        
        # Флаги для потоков
        self._disk_updating = False
        self._ram_updating = False
        self._disk_cache = {}
        self._ram_cache = {}
        
        # Загружаем предварительные данные
        self.preloaded_disks = self.initial_data.get('Диски', {})
        self.preloaded_ram = self.initial_data.get('Оперативная память', {})
        self.preloaded_cpu = self.initial_data.get('CPU', {})
        self.preloaded_gpu = self.initial_data.get('Видеокарта', [])
        self.preloaded_network = self.initial_data.get('Сеть', {})
        self.preloaded_board = self.initial_data.get('Материнская плата', {})
        self.preloaded_autostart = self.initial_data.get('Автозагрузка', [])
        self.preloaded_uwp = self.initial_data.get('UWP приложения', [])

        self.setup_ui()
        self.apply_preloaded_data()  # Применяем предзагруженные данные
        self.start_updates()
    
    def apply_preloaded_data(self):
        """Применяет данные, загруженные во время заставки"""
        
        # Применяем CPU данные
        if self.preloaded_cpu and 'name' in self.preloaded_cpu:
            self.cpu_name.configure(text=self.preloaded_cpu['name'])
            self.cores_label.configure(
                text=f"Ядер: {self.preloaded_cpu.get('cores_logical', 0)} логических, "
                     f"{self.preloaded_cpu.get('cores_physical', 0)} физических"
            )
        
        # Применяем RAM данные
        if self.preloaded_ram and 'ddr_type' in self.preloaded_ram:
            # Обновляем заголовок RAM с типом
            self.update_ram_header()
        
        # Применяем данные дисков
        if self.preloaded_disks:
            self._disk_cache = self.preloaded_disks
            self._update_disk_ui()
        
        # Применяем данные GPU
        if self.preloaded_gpu:
            self._update_gpu_ui(self.preloaded_gpu)
        
        # Применяем данные сети
        if self.preloaded_network:
            total_download_gb = self.preloaded_network.get('bytes_recv_gb', 0)
            total_upload_gb = self.preloaded_network.get('bytes_sent_gb', 0)
            self.total_download_label.configure(text=f"Всего скачано: {total_download_gb:.2f} GB")
            self.total_upload_label.configure(text=f"Всего отправлено: {total_upload_gb:.2f} GB")
            adapter_model = self.preloaded_network.get('adapter_model', 'Не обнаружено')
            self.network_adapter_label.configure(text=f"{adapter_model}")
        
        # Применяем данные материнской платы
        if self.preloaded_board and 'model' in self.preloaded_board:
            self.board_label.configure(text=self.preloaded_board['model'])
        
        # Применяем данные автозагрузки
        if self.preloaded_autostart:
            self.autostart_programs = self.preloaded_autostart
            self.load_autostart_programs()
        
        # Применяем UWP данные
        if self.preloaded_uwp:
            self.uwp_apps = self.preloaded_uwp
            self.display_uwp_apps_fixed()
    
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

        # Новая вкладка: Удаление UWP-приложений
        self.uwp_tab = self.tabview.add("UWP-приложения")
        self.setup_uwp_tab()

        # Вкладка О программе
        self.about_tab = self.tabview.add("О программе")
        self.setup_about_tab()

        # Нижняя панель
        self.create_footer()
        self.load_autostart_programs()
        self.load_uwp_apps()
        

    def setup_uwp_tab(self):
        """Настройка вкладки управления UWP-приложениями"""
        # Создаем экземпляр класса удаления
        self.uwp_remover = UWPRemover(self.window)
        
        # Основной контейнер
        main_frame = ctk.CTkFrame(self.uwp_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Верхняя панель
        top_frame = ctk.CTkFrame(main_frame)
        top_frame.pack(fill="x", padx=10, pady=5)
        
        # Заголовок
        title_label = ctk.CTkLabel(
            top_frame,
            text="Управление UWP-приложениями",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(side="left", padx=10)
        
        # Кнопка обновления
        self.refresh_uwp_btn = ctk.CTkButton(
            top_frame,
            text="Обновить список",
            command=self.load_uwp_apps,
            width=120
        )
        self.refresh_uwp_btn.pack(side="right", padx=10)
        
        # Контейнер со скроллом
        self.uwp_container = ctk.CTkScrollableFrame(main_frame)
        self.uwp_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Переменные
        self.uwp_apps = []
        self.uwp_vars = {}

    def load_uwp_apps(self):
        """Загрузка UWP-приложений"""
        # Очищаем контейнер в главном потоке
        for widget in self.uwp_container.winfo_children():
            widget.destroy()
        
        self.status_label.configure(text="Загрузка списка приложений...", text_color="orange")
        self.refresh_uwp_btn.configure(state="disabled")
        
        def load_in_thread():
            try:
                # Получаем приложения
                apps = self.uwp_remover.get_removable_apps()
                self.uwp_apps = apps
                
                # Обновляем UI в главном потоке
                self.window.after(0, self.display_uwp_apps_fixed)
                
            except Exception as e:
                error_msg = f"Ошибка: {str(e)}"
                self.window.after(0, lambda: self.status_label.configure(text=error_msg, text_color="red"))
                self.window.after(0, lambda: self.refresh_uwp_btn.configure(state="normal"))
        
        # Запускаем в потоке
        threading.Thread(target=load_in_thread, daemon=True).start()

    def display_uwp_apps_fixed(self):
        """Отображение UWP-приложений"""
        # Очищаем контейнер
        for widget in self.uwp_container.winfo_children():
            widget.destroy()
        
        self.uwp_vars.clear()
        
        if not self.uwp_apps:
            empty_label = ctk.CTkLabel(
                self.uwp_container,
                text="Не найдено приложений для удаления",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            empty_label.pack(pady=50)
            self.status_label.configure(text="Приложения не найдены")
            self.refresh_uwp_btn.configure(state="normal")
            return
        
        # Статистика
        safe_count = sum(1 for app in self.uwp_apps if app['is_safe'])
        stats_text = f"Найдено: {len(self.uwp_apps)} | Можно удалить: {safe_count}"
        self.status_label.configure(text=stats_text, text_color="green")
        
        # Отображаем каждое приложение
        for app in self.uwp_apps:
            app_frame = ctk.CTkFrame(self.uwp_container)
            app_frame.pack(fill="x", padx=5, pady=3)
            
            # Чекбокс
            var = tk.BooleanVar()
            self.uwp_vars[app['package_name']] = var
            
            checkbox = ctk.CTkCheckBox(app_frame, text="", variable=var)
            checkbox.pack(side="left", padx=5)
            
            # Иконка
            icon = "✓" if app['is_safe'] else "⚠"
            icon_label = ctk.CTkLabel(
                app_frame, 
                text=icon,
                text_color="green" if app['is_safe'] else "orange",
                font=ctk.CTkFont(size=14)
            )
            icon_label.pack(side="left", padx=5)
            
            # Информация
            info_frame = ctk.CTkFrame(app_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True)
            
            name_label = ctk.CTkLabel(
                info_frame,
                text=app['name'],
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w"
            )
            name_label.pack(anchor="w")
            
            details = f"Версия: {app['version']}"
            if not app['is_safe']:
                details += " | Удаляйте осторожно"
            
            details_label = ctk.CTkLabel(
                info_frame,
                text=details,
                font=ctk.CTkFont(size=10),
                text_color="gray",
                anchor="w"
            )
            details_label.pack(anchor="w")
            
            # Кнопка удаления
            remove_btn = ctk.CTkButton(
                app_frame,
                text="Удалить",
                width=70,
                height=25,
                fg_color="red",
                hover_color="darkred",
                command=lambda p=app['package_name'], n=app['name']: self.remove_uwp_app(p, n)
            )
            remove_btn.pack(side="right", padx=5)
        
        self.refresh_uwp_btn.configure(state="normal")

    def remove_uwp_app(self, package_name, app_name):
        """Удаление UWP-приложения"""
        if not messagebox.askyesno("Подтверждение", f"Удалить '{app_name}'?\n\nЭто действие нельзя отменить."):
            return
        
        self.status_label.configure(text=f"Удаление {app_name}...", text_color="orange")
        self.refresh_uwp_btn.configure(state="disabled")
        
        def remove_thread():
            success = self.uwp_remover.remove_app(package_name)
            
            def update_ui():
                if success:
                    self.status_label.configure(text=f"✓ {app_name} удалено", text_color="green")
                    # Обновляем список
                    self.load_uwp_apps()
                else:
                    self.status_label.configure(text=f"✗ Ошибка при удалении {app_name}", text_color="red")
                    self.refresh_uwp_btn.configure(state="normal")
            
            self.window.after(0, update_ui)
        
        threading.Thread(target=remove_thread, daemon=True).start()
    
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
        self.create_board_section(right_column)
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
            text="Скачать Windows",
            command=self.action_win_download,
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
        self.status_label = ctk.CTkLabel(
            self.autostart_tab,
            text="Загрузка списка программ...",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(pady=(0, 10))

        # Загружаем программы
        self.autostart_programs = []
        self.autostart_vars = {}
        self.load_autostart_programs()

    def load_autostart_programs(self):
        """Загрузить программы из автозагрузки"""
        # Очищаем контейнер
        for widget in self.autostart_container.winfo_children():
            widget.destroy()

        self.autostart_programs = TweakerTools.get_all_startup_programs()
        self.autostart_vars.clear()

        if not self.autostart_programs:
            empty_label = ctk.CTkLabel(
                self.autostart_container,
                text="Программы в автозагрузке не найдены",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            empty_label.pack(pady=50)
            self.status_label.configure(text="Программы не найдены")
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

        self.status_label.configure(
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
                        success = TweakerTools.enable_registry_program(program)
                    else:
                        success = TweakerTools.disable_registry_program(program)
                else:
                    if current_state:
                        success = TweakerTools.enable_folder_program(program)
                    else:
                        success = TweakerTools.disable_folder_program(program)

                if success:
                    changes_count += 1
                    program["is_disabled"] = not current_state

        if changes_count > 0:
            self.status_label.configure(
                text=f"Изменено программ: {changes_count}. Для полного эффекта перезагрузите компьютер.",
                text_color="green"
            )
            messagebox.showinfo("Успех",
                                f"Изменения применены для {changes_count} программ(ы)!\n\n"
                                "Для полного эффекта рекомендуется перезагрузить компьютер.")
            self.load_autostart_programs()
        else:
            self.status_label.configure(text="Изменений не было")
            messagebox.showinfo("Информация", "Изменений не было")

    def update_indexing_button_text(self):
        """Обновить текст кнопки индексации"""
        if TweakerTools.is_indexing_enabled():
            self.indexing_btn_text.set("Отключить индексацию дисков")
        else:
            self.indexing_btn_text.set("Включить индексацию дисков")

    def action_clear_temp(self):
        """Очистка временных файлов"""
        self.status_label.configure(text="Очистка временных файлов...", text_color="orange")
        self.window.update()

        deleted, error = TweakerTools.clear_temp()

        if error:
            self.status_label.configure(text=f"Ошибка: {error}", text_color="red")
            messagebox.showerror("Ошибка", f"Не удалось очистить временные файлы:\n{error}")
        else:
            self.status_label.configure(text=f"Очищено {deleted} файлов", text_color="green")
            messagebox.showinfo("Успех", f"Очищено {deleted} временных файлов")

    def action_disable_telemetry(self):
        """Отключение телеметрии"""
        self.status_label.configure(text="Отключение служб телеметрии...", text_color="orange")
        self.window.update()

        disabled, errors = TweakerTools.disable_telemetry_services()

        if errors:
            self.status_label.configure(text=f"Отключено {disabled} из {disabled + len(errors)} служб",
                                                 text_color="orange")
            messagebox.showwarning("Предупреждение",
                                   f"Отключено {disabled} служб.\nНе удалось отключить: {', '.join(errors)}")
        else:
            self.status_label.configure(text=f"Отключено {disabled} служб телеметрии", text_color="green")
            messagebox.showinfo("Успех", f"Успешно отключено {disabled} служб телеметрии")

    def action_flush_dns(self):
        """Очистка DNS"""
        self.status_label.configure(text="Очистка DNS кэша...", text_color="orange")
        self.window.update()

        success, error = TweakerTools.flush_dns()

        if success:
            self.status_label.configure(text="DNS кэш очищен", text_color="green")
            messagebox.showinfo("Успех", "DNS кэш успешно очищен")
        else:
            self.status_label.configure(text="Ошибка очистки DNS", text_color="red")
            messagebox.showerror("Ошибка", f"Не удалось очистить DNS кэш:\n{error}")

    def action_fix_updates(self):
        """Исправление обновлений"""
        self.status_label.configure(text="Исправление ошибок обновлений...", text_color="orange")
        self.window.update()

        success, error = TweakerTools.fix_updates()

        if success:
            self.status_label.configure(text="Обновления исправлены, запущена проверка", text_color="green")
            messagebox.showinfo("Информация",
                                "Проверка обновлений запущена (может занять время).\n"
                                "Проверьте Центр обновлений Windows для отслеживания статуса.")
        else:
            self.status_label.configure(text="Ошибка при исправлении", text_color="red")
            messagebox.showerror("Ошибка", f"Не удалось исправить ошибки обновлений:\n{error}")

    def action_toggle_indexing(self):
        """Переключение индексации"""
        if TweakerTools.is_indexing_enabled():
            self.status_label.configure(text="Отключение индексации...", text_color="orange")
            self.window.update()
            TweakerTools.disable_indexing()
            self.status_label.configure(text="Индексация дисков отключена", text_color="green")
            messagebox.showinfo("Готово", "Индексация дисков отключена.\nЭто снизит нагрузку на диск.")
        else:
            self.status_label.configure(text="Включение индексации...", text_color="orange")
            self.window.update()
            TweakerTools.enable_indexing()
            self.status_label.configure(text="Индексация дисков включена", text_color="green")
            messagebox.showinfo("Готово", "Индексация дисков включена.\nПоиск файлов будет быстрее.")

        self.update_indexing_button_text()

    def action_win_download(self):
        """Скачать ISO Windows"""
        start_download()

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
        self.cpu_name.pack(anchor="w", padx=20, pady=(5, 0))

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
                
        ctk.CTkLabel(ram_header, text=f"RAM - Оперативная память",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        self.ram_name = ctk.CTkLabel(ram_frame, text=f"{get_ddr_type()}",
                                     font=ctk.CTkFont(size=16, weight="bold"))
        self.ram_name.pack(anchor="w", padx=20, pady=(5, 0))
        
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
    
    def create_board_section(self, parent):
        board_frame = ctk.CTkFrame(parent)
        board_frame.pack(fill="x", padx=10, pady=5)

        board_header = ctk.CTkFrame(board_frame, height=40)
        board_header.pack(fill="x", padx=10, pady=(10, 5))
        board_header.pack_propagate(False)
        ctk.CTkLabel(board_header, text=f"Материнская плата",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        self.board_label = ctk.CTkLabel(board_frame, text=get_board_model(), font=ctk.CTkFont(size=16, weight="bold"))
        self.board_label.pack(side="left", padx=20)
        
        
    def create_network_section(self, parent):
        net_frame = ctk.CTkFrame(parent)
        net_frame.pack(fill="x", padx=10, pady=5)

        net_header = ctk.CTkFrame(net_frame, height=40)
        net_header.pack(fill="x", padx=10, pady=(10, 5))
        net_header.pack_propagate(False)

        ctk.CTkLabel(net_header, text="СЕТЬ",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        self.network_adapter_label = ctk.CTkLabel(
            net_frame, 
            text="Загрузка...", 
            font=ctk.CTkFont(size=16, weight="bold"), justify="left"
        )
        self.network_adapter_label.pack(anchor="w", padx=20, pady=(5, 0))
        
        info_frame = ctk.CTkFrame(net_frame)
        info_frame.pack(fill="x", padx=20, pady=5)

        self.download_label = ctk.CTkLabel(info_frame, text="Загрузка: 0 MB/s",
                                           font=ctk.CTkFont(size=16))
        self.download_label.pack(side="left", pady=3)

        self.upload_label = ctk.CTkLabel(info_frame, text="Отдача: 0 MB/s",
                                         font=ctk.CTkFont(size=16))
        self.upload_label.pack(side="right", pady=3)

        traffic_frame = ctk.CTkFrame(net_frame)
        traffic_frame.pack(fill="x", padx=20, pady=5)

        self.total_download_label = ctk.CTkLabel(traffic_frame, text="Всего скачано: 0 GB",
                                                 font=ctk.CTkFont(size=16))
        self.total_download_label.pack(side="left", pady=2)

        self.total_upload_label = ctk.CTkLabel(traffic_frame, text="Всего отправлено: 0 GB",
                                               font=ctk.CTkFont(size=16))
        self.total_upload_label.pack(side="right", pady=2)

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
        
        # Добавляем индикатор загрузки
        self.disk_loading_label = ctk.CTkLabel(
            self.disk_container,
            text="Загрузка информации о дисках...",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.disk_loading_label.pack(pady=10)

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
        self.status_label = ctk.CTkLabel(
            footer,
            text="Готов",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(side="left", padx=20)

    def update_stats(self):
        while self.running:
            try:
                self.window.after(0, self.update_cpu_info)
                self.window.after(0, self.update_network_info)
                self.window.after(0, self.update_gpu_info)
                self.window.after(0, self.update_time_info)
                
                # Запускаем обновление RAM и дисков в отдельных потоках
                self.update_ram_async()
                self.update_disk_async()

                time.sleep(self.update_interval / 1000)
            except Exception as e:
                print(f"Error in update thread: {e}")
                time.sleep(1)

    def update_ram_async(self):
        """Асинхронное обновление информации об ОЗУ"""
        if self._ram_updating:
            return
        
        self._ram_updating = True
        
        def _update_ram_in_thread():
            try:
                ram = psutil.virtual_memory()
                self._ram_cache = {
                    'percent': ram.percent,
                    'used_gb': ram.used / (1024 ** 3),
                    'total_gb': ram.total / (1024 ** 3)
                }
                # Обновляем UI в главном потоке
                self.window.after(0, self._update_ram_ui)
            except Exception as e:
                print(f"RAM update error in thread: {e}")
            finally:
                self._ram_updating = False
        
        threading.Thread(target=_update_ram_in_thread, daemon=True).start()
    
    def _update_ram_ui(self):
        """Обновление UI с информацией об ОЗУ"""
        try:
            if self._ram_cache:
                self.ram_progress.set(self._ram_cache['percent'] / 100)
                self.ram_percent_label.configure(text=f"Использовано: {self._ram_cache['percent']:.1f}%")
                self.ram_usage_label.configure(
                    text=f"Использовано: {self._ram_cache['used_gb']:.1f} GB / {self._ram_cache['total_gb']:.1f} GB"
                )
        except Exception as e:
            print(f"RAM UI update error: {e}")

    def update_disk_async(self):
        """Асинхронное обновление информации о дисках"""
        if self._disk_updating:
            return
        
        self._disk_updating = True
        
        def _update_disk_in_thread():
            try:
                current_disks = {}
                for partition in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        current_disks[partition.device] = {
                            'mount': partition.mountpoint,
                            'percent': usage.percent,
                            'used': usage.used,
                            'total': usage.total,
                            'type': get_disk_type(partition.device)
                        }
                    except:
                        pass
                self._disk_cache = current_disks
                # Обновляем UI в главном потоке
                if self.running:
                    self.window.after(0, self._update_disk_ui)
            except Exception as e:
                print(f"Disk update error in thread: {e}")
            finally:
                self._disk_updating = False
        
        threading.Thread(target=_update_disk_in_thread, daemon=True).start()
    
    def _update_disk_ui(self):
        """Обновление UI с информацией о дисках"""
        try:
            if not self.running:
                return
                
            # Удаляем индикатор загрузки, если он есть
            if hasattr(self, 'disk_loading_label') and self.disk_loading_label.winfo_exists():
                self.disk_loading_label.destroy()
            
            current_disks = self._disk_cache
            
            # Удаляем виджеты для дисков, которые больше не существуют
            for device in list(self.disk_widgets.keys()):
                if device not in current_disks:
                    for widget in self.disk_widgets[device]:
                        widget.destroy()
                    del self.disk_widgets[device]

            # Создаем или обновляем виджеты для существующих дисков
            for device, info in current_disks.items():
                if device not in self.disk_widgets:
                    disk_frame = ctk.CTkFrame(self.disk_container)
                    disk_frame.pack(fill="x", pady=2)

                    name_label = ctk.CTkLabel(disk_frame, text=f"{device} ({info['type']})",
                                              font=ctk.CTkFont(size=16, weight="bold"))
                    name_label.pack(anchor="w", padx=5, pady=(2, 0))

                    progress = ctk.CTkProgressBar(disk_frame, height=20)
                    progress.pack(fill="x", padx=5, pady=2)

                    info_label = ctk.CTkLabel(disk_frame, text="",
                                              font=ctk.CTkFont(size=16))
                    info_label.pack(anchor="w", padx=5, pady=(0, 2))

                    self.disk_widgets[device] = [disk_frame, name_label, progress, info_label]

                _, _, progress, info_label = self.disk_widgets[device]
                
                # Безопасное получение значений
                if 'used' in info and 'total' in info:
                    used_gb = info['used'] / (1024 ** 3)
                    total_gb = info['total'] / (1024 ** 3)
                else:
                    used_gb = info.get('used_gb', 0)
                    total_gb = info.get('total_gb', 0)

                progress.set(info['percent'] / 100)
                info_label.configure(text=f"Использовано: {info['percent']:.1f}% ({used_gb:.1f}/{total_gb:.1f} GB)")
        except Exception as e:
            print(f"Disk UI update error: {e}")

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

    def update_gpu_info(self):
        """Обновление информации о GPU"""
        try:
            if self._gpu_updating:
                return

            self._gpu_updating = True

            def _update_gpu_in_thread():
                try:
                    import concurrent.futures
                    gpus = []
                    
                    # Пробуем GPUtil
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(GPUtil.getGPUs)
                        try:
                            gpus = future.result(timeout=2.0)
                        except (concurrent.futures.TimeoutError, Exception) as e:
                            print(f"GPUtil error: {e}")
                            gpus = []
                    
                    # Если GPUtil не нашел GPU, пробуем WMI
                    if not gpus:
                        try:
                            import wmi
                            import pythoncom
                            pythoncom.CoInitialize()
                            c = wmi.WMI()
                            gpu_wmi = c.Win32_VideoController()
                            pythoncom.CoUninitialize()
                            
                            if gpu_wmi:
                                for wmi_gpu in gpu_wmi:
                                    gpu_name = getattr(wmi_gpu, 'Name', '')
                                    if gpu_name and not no_show_gpu(gpu_name):
                                        # Создаем словарь вместо объекта
                                        gpu_dict = {
                                            'name': gpu_name,
                                            'load': 0.0,
                                            'temperature': 0.0,
                                            'memory_used': 0,
                                            'memory_total': 0,
                                            'memory_util': 0.0
                                        }
                                        # Пробуем получить память
                                        ram_bytes = getattr(wmi_gpu, 'AdapterRAM', 0)
                                        if ram_bytes and ram_bytes > 0:
                                            gpu_dict['memory_total'] = ram_bytes / (1024 ** 2)
                                        gpus.append(gpu_dict)
                        except Exception as e:
                            print(f"WMI GPU fallback error: {e}")
                    
                    self.window.after(0, lambda: self._update_gpu_ui(gpus))
                    self._gpu_updating = False

                except Exception as e:
                    print(f"GPU check error: {e}")
                    self.window.after(0, lambda: self._update_gpu_ui([]))
                    self._gpu_updating = False

            threading.Thread(target=_update_gpu_in_thread, daemon=True).start()

        except Exception as e:
            print(f"GPU update error: {e}")
            self._gpu_updating = False

    def _update_gpu_ui(self, gpus):
        """Обновление UI с информацией о GPU (выполняется в главном потоке)"""
        try:
            # ФИЛЬТРУЕМ ВСТРОЙКИ
            filtered_gpus = []
            integrated_keywords = ['Intel', 'UHD', 'HD Graphics', 'Iris', 'Radeon Graphics', 'AMD Radeon']
            
            for gpu in gpus:
                gpu_name = ""
                if hasattr(gpu, 'name'):
                    gpu_name = gpu.name
                elif isinstance(gpu, dict):
                    gpu_name = gpu.get('name', '')
                
                # Пропускаем встройки
                if any(keyword in gpu_name for keyword in integrated_keywords):
                    print(f"Пропускаем встройку: {gpu_name}")
                    continue
                
                filtered_gpus.append(gpu)
        
            gpus = filtered_gpus  # Заменяем на отфильтрованный список
            
            # Проверяем, есть ли данные
            if not gpus or (isinstance(gpus, list) and len(gpus) == 0):
                if hasattr(self, '_gpu_detected') and self._gpu_detected:
                    return
                
                for widget in self.gpu_container.winfo_children():
                    widget.destroy()
                
                self.gpu_label = ctk.CTkLabel(
                    self.gpu_container, 
                    text="GPU не обнаружен",
                    font=ctk.CTkFont(size=16)
                )
                self.gpu_label.pack(pady=10)
                return
            
            self._gpu_detected = True
            
            # Удаляем все старые виджеты
            for widget in self.gpu_container.winfo_children():
                widget.destroy()
            
            # Создаем виджеты для каждого GPU
            for i, gpu in enumerate(gpus):
                gpu_id = f"gpu_{i}"
                
                # Получаем данные в зависимости от типа объекта
                if hasattr(gpu, 'name'):  # Объект с атрибутами
                    gpu_name = gpu.name
                    gpu_load = gpu.load * 100 if hasattr(gpu, 'load') else 0
                    gpu_temp = gpu.temperature if hasattr(gpu, 'temperature') else 0
                    gpu_memory_used = gpu.memoryUsed if hasattr(gpu, 'memoryUsed') else 0
                    gpu_memory_total = gpu.memoryTotal if hasattr(gpu, 'memoryTotal') else 0
                    gpu_memory_util = gpu.memoryUtil * 100 if hasattr(gpu, 'memoryUtil') else 0
                elif isinstance(gpu, dict):  # Словарь
                    gpu_name = gpu.get('name', 'Unknown GPU')
                    gpu_load = gpu.get('load', 0)
                    gpu_temp = gpu.get('temperature', 0)
                    gpu_memory_used = gpu.get('memory_used', 0)
                    gpu_memory_total = gpu.get('memory_total', 0)
                    gpu_memory_util = gpu.get('memory_util', 0)
                else:
                    continue
                
                gpu_card_frame = ctk.CTkFrame(self.gpu_container)
                gpu_card_frame.pack(fill="x", pady=3)
                
                name_label = ctk.CTkLabel(
                    gpu_card_frame, 
                    text=gpu_name,
                    font=ctk.CTkFont(size=16, weight="bold")
                )
                name_label.pack(anchor="w", padx=10, pady=(5, 0))
                
                load_progress = ctk.CTkProgressBar(gpu_card_frame, height=20)
                load_progress.pack(fill="x", padx=10, pady=5)
                
                info_label = ctk.CTkLabel(
                    gpu_card_frame, 
                    text="",
                    font=ctk.CTkFont(size=14)
                )
                info_label.pack(anchor="w", padx=10, pady=(0, 5))
                
                self.gpu_widgets[gpu_id] = [gpu_card_frame, name_label, load_progress, info_label]
                
                # Обновляем данные
                load_progress.set(gpu_load / 100 if gpu_load > 0 else 0)
                
                if gpu_memory_total > 0:
                    info_text = f"Загрузка: {gpu_load:.1f}% | Температура: {gpu_temp:.0f}°C | "
                    info_text += f"Память: {gpu_memory_util:.1f}% | VRAM: {gpu_memory_used:.0f}/{gpu_memory_total:.0f} MB"
                else:
                    info_text = f"Загрузка: {gpu_load:.1f}% | Температура: {gpu_temp:.0f}°C"
                
                info_label.configure(text=info_text)
                    
        except Exception as e:
            print(f"GPU UI update error: {e}")
            import traceback
            traceback.print_exc()

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
        # Добавляем переменные для отслеживания потоков
        self._gpu_updating = False

    def run(self):
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()

    def on_closing(self):
        self.running = False
        self.window.quit()
        self.window.destroy()