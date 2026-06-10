"""
GUI компонент для интеграции Fido в BestWinTweaker
Добавляет вкладку "Скачать Windows" в основное приложение
"""

import customtkinter as ctk
import threading
import os
import tkinter as tk
from tkinter import messagebox, filedialog
from fido_integration import FidoDownloader, is_admin, request_admin


class FidoDownloadTab:
    """Класс для вкладки скачивания Windows через Fido"""
    
    def __init__(self, parent, parent_app=None):
        self.parent = parent
        self.parent_app = parent_app
        self.downloader = FidoDownloader()
        self.is_downloading = False
        self.current_iso_url = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса вкладки"""
        
        # Проверка прав администратора
        if not is_admin():
            self.show_admin_warning()
        
        # Основной контейнер
        self.container = ctk.CTkFrame(self.parent)
        self.container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Заголовок
        title_label = ctk.CTkLabel(
            self.container,
            text="Скачать официальный образ Windows",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ctk.CTkLabel(
            self.container,
            text="Загрузка с официальных серверов Microsoft через Fido",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        subtitle_label.pack(pady=(0, 20))
        
        # Фрейм для параметров
        params_frame = ctk.CTkFrame(self.container)
        params_frame.pack(fill="x", padx=20, pady=10)
        
        # Версия Windows
        version_label = ctk.CTkLabel(
            params_frame,
            text="Версия Windows:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        version_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.version_var = ctk.StringVar(value="11")
        version_menu = ctk.CTkOptionMenu(
            params_frame,
            values=list(self.downloader.VERSIONS.keys()),
            variable=self.version_var,
            width=150
        )
        version_menu.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # Редакция Windows
        edition_label = ctk.CTkLabel(
            params_frame,
            text="Редакция:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        edition_label.grid(row=0, column=2, padx=10, pady=10, sticky="w")
        
        self.edition_var = ctk.StringVar(value="default")
        edition_menu = ctk.CTkOptionMenu(
            params_frame,
            values=list(self.downloader.EDITIONS.keys()),
            variable=self.edition_var,
            width=180
        )
        edition_menu.grid(row=0, column=3, padx=10, pady=10, sticky="w")
        
        # Язык
        lang_label = ctk.CTkLabel(
            params_frame,
            text="Язык:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lang_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        
        self.lang_var = ctk.StringVar(value="Russian")
        lang_menu = ctk.CTkOptionMenu(
            params_frame,
            values=list(self.downloader.LANGUAGES.keys()),
            variable=self.lang_var,
            width=150
        )
        lang_menu.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        # Архитектура
        arch_label = ctk.CTkLabel(
            params_frame,
            text="Архитектура:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        arch_label.grid(row=1, column=2, padx=10, pady=10, sticky="w")
        
        self.arch_var = ctk.StringVar(value="x64")
        arch_menu = ctk.CTkOptionMenu(
            params_frame,
            values=["x64", "x86", "arm64"],
            variable=self.arch_var,
            width=100
        )
        arch_menu.grid(row=1, column=3, padx=10, pady=10, sticky="w")
        
        # Путь сохранения
        path_label = ctk.CTkLabel(
            params_frame,
            text="Путь сохранения:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        path_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        
        self.path_var = ctk.StringVar()
        default_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.path_var.set(default_path)
        
        path_entry = ctk.CTkEntry(
            params_frame,
            textvariable=self.path_var,
            width=300
        )
        path_entry.grid(row=2, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        
        browse_btn = ctk.CTkButton(
            params_frame,
            text="Обзор...",
            command=self.browse_folder,
            width=80
        )
        browse_btn.grid(row=2, column=3, padx=10, pady=10)
        
        params_frame.columnconfigure(1, weight=1)
        params_frame.columnconfigure(2, weight=0)
        
        # Кнопки действий
        actions_frame = ctk.CTkFrame(self.container)
        actions_frame.pack(fill="x", padx=20, pady=20)
        
        self.get_link_btn = ctk.CTkButton(
            actions_frame,
            text="Получить ссылку",
            command=self.get_iso_link,
            width=180,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.get_link_btn.pack(side="left", padx=10)
        
        self.download_btn = ctk.CTkButton(
            actions_frame,
            text="Скачать ISO",
            command=self.start_download,
            width=180,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            fg_color="green"
        )
        self.download_btn.pack(side="left", padx=10)
        
        self.cancel_btn = ctk.CTkButton(
            actions_frame,
            text="Отмена",
            command=self.cancel_download,
            width=120,
            height=40,
            state="disabled",
            fg_color="red"
        )
        self.cancel_btn.pack(side="left", padx=10)
        
        # Прогресс бар
        self.progress_bar = ctk.CTkProgressBar(self.container, height=20)
        self.progress_bar.pack(fill="x", padx=20, pady=10)
        self.progress_bar.set(0)
        
        # Статус
        self.status_label = ctk.CTkLabel(
            self.container,
            text="Готов к работе",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(pady=5)
        
    def show_admin_warning(self):
        """Показать предупреждение о правах администратора"""
        
        def request_elevation():
            request_admin()
            
        warning_frame = ctk.CTkFrame(self.parent)
        warning_frame.pack(fill="x", padx=20, pady=10)
        
        warning_label = ctk.CTkLabel(
            warning_frame,
            text="⚠️ Для работы скачивания Windows требуются права администратора!",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="orange"
        )
        warning_label.pack(pady=10)
        
        elevate_btn = ctk.CTkButton(
            warning_frame,
            text="Запросить права администратора",
            command=request_elevation
        )
        elevate_btn.pack(pady=5)
        
    def browse_folder(self):
        """Выбор папки для сохранения"""
        folder = filedialog.askdirectory(title="Выберите папку для сохранения ISO")
        if folder:
            self.path_var.set(folder)
    
    def get_iso_link(self):
        """Получить ссылку на ISO"""
        
        def get_link_thread():
            try:
                self.get_link_btn.configure(state="disabled", text="Получение ссылки...")
                self.status_label.configure(text="Получение ссылки...")
                
                iso_url = self.downloader.get_iso_link(
                    version=self.version_var.get(),
                    edition=self.edition_var.get(),
                    language=self.lang_var.get(),
                    arch=self.arch_var.get(),
                    progress_callback=lambda msg: self.status_label.configure(text=msg)
                )
                
                if iso_url:
                    self.current_iso_url = iso_url
                    self.status_label.configure(
                        text=f"✅ Ссылка получена! Нажмите 'Скачать ISO' для начала загрузки",
                        text_color="green"
                    )
                    self.download_btn.configure(state="normal")
                    messagebox.showinfo(
                        "Успех",
                        f"Ссылка на ISO успешно получена!\n\n"
                        f"Размер файла: ~5-6 GB\n"
                        f"Для скачивания нажмите 'Скачать ISO'"
                    )
                else:
                    self.status_label.configure(
                        text="❌ Не удалось получить ссылку. Проверьте подключение к интернету",
                        text_color="red"
                    )
                    messagebox.showerror("Ошибка", "Не удалось получить ссылку на ISO")
                    
            except Exception as e:
                self.status_label.configure(text=f"❌ Ошибка: {str(e)}", text_color="red")
                messagebox.showerror("Ошибка", str(e))
            finally:
                self.get_link_btn.configure(state="normal", text="Получить ссылку")
        
        threading.Thread(target=get_link_thread, daemon=True).start()
    
    def start_download(self):
        """Начать скачивание ISO"""
        
        if not self.current_iso_url:
            messagebox.showwarning("Предупреждение", "Сначала получите ссылку на ISO")
            return
        
        # Запрашиваем имя файла
        filename = f"Windows{self.version_var.get()}_{self.lang_var.get()}.iso"
        
        save_file = filedialog.asksaveasfilename(
            title="Сохранить ISO как...",
            defaultextension=".iso",
            filetypes=[("ISO files", "*.iso")],
            initialfile=filename,
            initialdir=self.path_var.get()
        )
        
        if not save_file:
            return
        
        def download_thread():
            try:
                self.is_downloading = True
                self.download_btn.configure(state="disabled")
                self.cancel_btn.configure(state="normal")
                self.get_link_btn.configure(state="disabled")
                
                def progress_cb(progress):
                    self.progress_bar.set(progress / 100)
                    self.status_label.configure(
                        text=f"Скачивание... {progress:.1f}%",
                        text_color="blue"
                    )
                    # Обновляем GUI
                    self.parent.update_idletasks()
                
                def status_cb(status):
                    self.status_label.configure(text=status)
                    self.parent.update_idletasks()
                
                result = self.downloader.download_iso(
                    self.current_iso_url,
                    save_file,
                    progress_cb,
                    status_cb
                )
                
                if result:
                    self.progress_bar.set(1)
                    self.status_label.configure(
                        text=f"✅ Скачивание завершено! Файл сохранен: {result}",
                        text_color="green"
                    )
                    messagebox.showinfo(
                        "Успех",
                        f"ISO образ успешно скачан!\n\n"
                        f"Файл сохранен: {result}\n\n"
                        f"Вы можете использовать этот ISO для установки Windows."
                    )
                elif not self.is_downloading:
                    self.status_label.configure(text="Скачивание отменено", text_color="orange")
                else:
                    self.status_label.configure(text="❌ Ошибка при скачивании", text_color="red")
                    
            except Exception as e:
                self.status_label.configure(text=f"❌ Ошибка: {str(e)}", text_color="red")
                messagebox.showerror("Ошибка", str(e))
            finally:
                self.is_downloading = False
                self.download_btn.configure(state="normal", text="Скачать ISO")
                self.cancel_btn.configure(state="disabled")
                self.get_link_btn.configure(state="normal")
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def cancel_download(self):
        """Отменить скачивание"""
        self.downloader.cancel_download()
        self.is_downloading = False
        self.status_label.configure(text="Отмена скачивания...", text_color="orange")


# Функция для добавления вкладки в основной интерфейс
def add_fido_tab(tabview):
    """Добавить вкладку Fido в Tabview основного приложения"""
    fido_tab = tabview.add("Скачать Windows")
    fido_widget = FidoDownloadTab(fido_tab)
    return fido_widget


# Пример использования для модификации BestWinTweaker.py
def integrate_to_app(app_instance):
    """
    Интегрировать Fido в существующий экземпляр приложения
    Используйте этот метод для добавления вкладки в ваше приложение
    """
    # Добавляем новую вкладку
    fido_tab = app_instance.tabview.add("Скачать Windows")
    fido_widget = FidoDownloadTab(fido_tab, app_instance)
    return fido_widget