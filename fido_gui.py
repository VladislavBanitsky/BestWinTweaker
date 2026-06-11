"""
GUI компонент для интеграции Fido в BestWinTweaker
Добавляет вкладку "Скачать Windows" в основное приложение
"""

import customtkinter as ctk
import threading
import os
import webbrowser
import tkinter as tk
from tkinter import messagebox, filedialog
from fido_integration import FidoDownloader, is_admin, request_admin, get_windows_version


class FidoDownloadTab:
    """Класс для вкладки скачивания Windows через Fido"""
    
    def __init__(self, parent, parent_app=None):
        self.parent = parent
        self.parent_app = parent_app
        self.downloader = FidoDownloader()
        self.is_downloading = False
        self.current_iso_url = None
        self.is_loading_data = False
        
        self.setup_ui()
        self.load_available_data()
        
    def setup_ui(self):
        """Настройка интерфейса вкладки"""
        
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
            text="Загрузка с официальных серверов Microsoft",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        subtitle_label.pack(pady=(0, 20))
        
        # Предупреждение о Windows 7
        if get_windows_version() == "7":
            warning_frame = ctk.CTkFrame(self.container, fg_color="orange", corner_radius=10)
            warning_frame.pack(fill="x", padx=20, pady=10)
            
            warning_label = ctk.CTkLabel(
                warning_frame,
                text="⚠️ Windows 7 не поддерживает автоматическое скачивание через Fido.\nБудет открыта страница загрузки Microsoft в браузере.",
                font=ctk.CTkFont(size=12),
                text_color="black"
            )
            warning_label.pack(pady=10)
        
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
        
        self.version_var = ctk.StringVar(value="Загрузка...")
        self.version_menu = ctk.CTkOptionMenu(
            params_frame,
            values=["Загрузка..."],
            variable=self.version_var,
            width=150,
            state="disabled"
        )
        self.version_menu.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # Редакция Windows
        edition_label = ctk.CTkLabel(
            params_frame,
            text="Редакция:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        edition_label.grid(row=0, column=2, padx=10, pady=10, sticky="w")
        
        self.edition_var = ctk.StringVar(value="Загрузка...")
        self.edition_menu = ctk.CTkOptionMenu(
            params_frame,
            values=["Загрузка..."],
            variable=self.edition_var,
            width=180,
            state="disabled"
        )
        self.edition_menu.grid(row=0, column=3, padx=10, pady=10, sticky="w")
        
        # Язык
        lang_label = ctk.CTkLabel(
            params_frame,
            text="Язык:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lang_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        
        self.lang_var = ctk.StringVar(value="Загрузка...")
        self.lang_menu = ctk.CTkOptionMenu(
            params_frame,
            values=["Загрузка..."],
            variable=self.lang_var,
            width=150,
            state="disabled"
        )
        self.lang_menu.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        # Архитектура
        arch_label = ctk.CTkLabel(
            params_frame,
            text="Архитектура:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        arch_label.grid(row=1, column=2, padx=10, pady=10, sticky="w")
        
        self.arch_var = ctk.StringVar(value="x64")
        self.arch_menu = ctk.CTkOptionMenu(
            params_frame,
            values=["x64", "x86", "arm64"],
            variable=self.arch_var,
            width=100
        )
        self.arch_menu.grid(row=1, column=3, padx=10, pady=10, sticky="w")
        
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
        
        self.download_btn = ctk.CTkButton(
            actions_frame,
            text="Скачать ISO",
            command=self.start_download,
            width=200,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
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
            text="Загрузка списка доступных версий...",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(pady=5)
        
    def load_available_data(self):
        """Загрузить доступные данные из Fido"""
        
        def load_thread():
            if self.is_loading_data:
                return
            self.is_loading_data = True
            
            try:
                data = self.downloader.get_available_data_from_fido(
                    lambda msg: self.parent.after(0, lambda: self.status_label.configure(text=msg))
                )
                
                self.parent.after(0, lambda: self.update_menus(data))
            except Exception as e:
                self.parent.after(0, lambda: self.status_label.configure(text=f"Ошибка: {str(e)}"))
            finally:
                self.is_loading_data = False
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def update_menus(self, data):
        """Обновить выпадающие списки"""
        # Обновляем версии
        versions = data.get("versions", {"11": "Windows 11", "10": "Windows 10"})
        version_values = list(versions.keys())
        version_display = [f"{k} - {v}" for k, v in versions.items()]
        
        self.version_menu.configure(values=version_display, state="normal")
        if version_display:
            self.version_var.set(version_display[0])
        
        # Обновляем редакции
        editions = data.get("editions", {
            "professional": "Professional",
            "home": "Home",
            "education": "Education",
            "enterprise": "Enterprise"
        })
        edition_display = [f"{k}: {v}" for k, v in editions.items()]
        
        self.edition_menu.configure(values=edition_display, state="normal")
        if edition_display:
            self.edition_var.set(edition_display[0])
        
        # Обновляем языки
        languages = data.get("languages", {
            "Russian": "Русский",
            "English": "English (US)"
        })
        lang_display = [f"{k}: {v}" for k, v in languages.items()]
        
        self.lang_menu.configure(values=lang_display, state="normal")
        if lang_display:
            self.lang_var.set(lang_display[0])
        
        # Обновляем архитектуры
        arches = data.get("arches", ["x64", "x86", "arm64"])
        self.arch_menu.configure(values=arches, state="normal")
        
        self.status_label.configure(text="Выберите параметры и нажмите 'Скачать ISO'")
    
    def get_selected_version(self):
        """Получить выбранную версию (ключ)"""
        selected = self.version_var.get()
        if " - " in selected:
            return selected.split(" - ")[0]
        return "11"
    
    def get_selected_edition(self):
        """Получить выбранную редакцию (ключ)"""
        selected = self.edition_var.get()
        if ": " in selected:
            return selected.split(": ")[0]
        return "professional"
    
    def get_selected_language(self):
        """Получить выбранный язык (ключ)"""
        selected = self.lang_var.get()
        if ": " in selected:
            return selected.split(": ")[0]
        return "Russian"
    
    def browse_folder(self):
        """Выбор папки для сохранения"""
        folder = filedialog.askdirectory(title="Выберите папку для сохранения ISO")
        if folder:
            self.path_var.set(folder)
    
    def start_download(self):
        """Начать скачивание ISO"""
        
        # Проверка поддержки Fido на Windows 7
        if get_windows_version() == "7":
            version = self.get_selected_version()
            url = self.downloader.get_microsoft_download_url(version)
            webbrowser.open(url)
            messagebox.showinfo(
                "Открыт браузер",
                f"Windows 7 не поддерживает автоматическое скачивание.\n"
                f"Страница загрузки Windows {version} открыта в браузере."
            )
            return
        
        # Проверка прав администратора
        if not is_admin():
            result = messagebox.askyesno(
                "Требуются права администратора",
                "Для скачивания Windows через Fido требуются права администратора.\n\n"
                "Запросить права администратора?"
            )
            if result:
                request_admin()
            return
        
        # Запрашиваем имя файла
        version = self.get_selected_version()
        edition = self.get_selected_edition()
        lang = self.get_selected_language()
        
        filename = f"Windows{version}_{lang}_{edition}.iso"
        
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
                self.download_btn.configure(state="disabled", text="Получение ссылки...")
                self.cancel_btn.configure(state="normal")
                
                # Получаем ссылку
                def progress_msg(msg):
                    self.parent.after(0, lambda: self.status_label.configure(text=msg))
                
                iso_url = self.downloader.get_iso_link(
                    version=self.get_selected_version(),
                    edition=self.get_selected_edition(),
                    language=self.get_selected_language(),
                    arch=self.arch_var.get(),
                    progress_callback=progress_msg
                )
                
                if not iso_url:
                    self.parent.after(0, lambda: self.status_label.configure(
                        text="❌ Не удалось получить ссылку. Возможно, выбранные параметры недоступны.",
                        text_color="red"
                    ))
                    messagebox.showerror("Ошибка", "Не удалось получить ссылку на ISO.\n\nПопробуйте другие параметры.")
                    return
                
                self.current_iso_url = iso_url
                
                # Скачиваем
                self.parent.after(0, lambda: self.download_btn.configure(text="Скачивание..."))
                
                def progress_cb(progress):
                    self.parent.after(0, lambda: self.progress_bar.set(progress / 100))
                    self.parent.after(0, lambda: self.status_label.configure(
                        text=f"Скачивание... {progress:.1f}%"
                    ))
                
                def status_cb(status):
                    self.parent.after(0, lambda: self.status_label.configure(text=status))
                
                result = self.downloader.download_iso(
                    self.current_iso_url,
                    save_file,
                    progress_cb,
                    status_cb
                )
                
                if result:
                    self.parent.after(0, lambda: self.progress_bar.set(1))
                    self.parent.after(0, lambda: self.status_label.configure(
                        text=f"✅ Скачивание завершено! Файл сохранен: {result}",
                        text_color="green"
                    ))
                    messagebox.showinfo(
                        "Успех",
                        f"ISO образ успешно скачан!\n\n"
                        f"Файл сохранен: {result}\n\n"
                        f"Вы можете использовать этот ISO для установки Windows."
                    )
                elif not self.is_downloading:
                    self.parent.after(0, lambda: self.status_label.configure(
                        text="Скачивание отменено",
                        text_color="orange"
                    ))
                else:
                    self.parent.after(0, lambda: self.status_label.configure(
                        text="❌ Ошибка при скачивании",
                        text_color="red"
                    ))
                    
            except Exception as e:
                self.parent.after(0, lambda: self.status_label.configure(
                    text=f"❌ Ошибка: {str(e)}",
                    text_color="red"
                ))
                messagebox.showerror("Ошибка", str(e))
            finally:
                self.is_downloading = False
                self.parent.after(0, lambda: self.download_btn.configure(
                    state="normal", text="Скачать ISO"
                ))
                self.parent.after(0, lambda: self.cancel_btn.configure(state="disabled"))
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def cancel_download(self):
        """Отменить скачивание"""
        self.downloader.cancel_download()
        self.is_downloading = False
        self.status_label.configure(text="Отмена скачивания...", text_color="orange")