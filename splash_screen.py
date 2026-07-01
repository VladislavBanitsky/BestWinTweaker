# splash_screen.py
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading

class SplashScreen:
    """Заставка с поддержкой фоновой загрузки данных"""
    
    def __init__(self, initial_data=None):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg='#1a1a2e')
        
        # Размеры
        self.width = 500
        self.height = 300
        
        # Центрируем
        x = (self.root.winfo_screenwidth() - self.width) // 2
        y = (self.root.winfo_screenheight() - self.height) // 2
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.attributes('-topmost', True)
        
        # Данные для загрузки
        self.loaded_data = initial_data or {}
        self.loading_complete = False
        
        # Создаем UI
        self.setup_ui()
        
    def setup_ui(self):
        """Создание интерфейса"""
        main_frame = tk.Frame(self.root, bg='#1a1a2e')
        main_frame.pack(fill='both', expand=True)
        
        center_frame = tk.Frame(main_frame, bg='#1a1a2e')
        center_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Логотип
        try:
            img = Image.open('./resources/images/BestWinTweaker.png')
            img = img.resize((100, 100), Image.Resampling.LANCZOS)
            self.logo = ImageTk.PhotoImage(img)
            logo_label = tk.Label(center_frame, image=self.logo, bg='#1a1a2e')
            logo_label.pack(pady=(0, 20))
        except:
            logo_label = tk.Label(
                center_frame,
                text="BestWinTweaker",
                font=('Segoe UI', 24, 'bold'),
                fg='#00b4d8',
                bg='#1a1a2e'
            )
            logo_label.pack(pady=(0, 10))
            
            tk.Label(
                center_frame,
                text="Системный монитор и оптимизатор",
                font=('Segoe UI', 11),
                fg='#a0a0a0',
                bg='#1a1a2e'
            ).pack(pady=(0, 30))
        
        # Прогресс бар
        self.progress = ttk.Progressbar(
            center_frame,
            length=350,
            mode='determinate'
        )
        self.progress.pack(pady=(10, 5))
        
        # Статус
        self.status_var = tk.StringVar(value="Инициализация...")
        self.status_label = tk.Label(
            center_frame,
            textvariable=self.status_var,
            font=('Segoe UI', 9),
            fg='#888888',
            bg='#1a1a2e'
        )
        self.status_label.pack(pady=(5, 10))
        
        # Версия
        tk.Label(
            main_frame,
            text="BestWinTweaker 1.9.7",
            font=('Segoe UI', 8),
            fg='#666666',
            bg='#1a1a2e'
        ).place(x=10, y=self.height - 25)
        
    def set_status(self, status, progress=None):
        """Обновление статуса"""
        self.status_var.set(status)
        if progress is not None:
            self.progress['value'] = progress
        self.root.update()
        
    def set_loading_data(self, key, value):
        """Сохранить загруженные данные"""
        self.loaded_data[key] = value
        
    def get_loading_data(self):
        """Получить все загруженные данные"""
        return self.loaded_data
        
    def is_loading_complete(self):
        """Проверить, завершена ли загрузка"""
        return self.loading_complete
        
    def complete_loading(self):
        """Завершить загрузку"""
        self.loading_complete = True
        
    def close(self):
        """Закрытие заставки"""
        self.root.destroy()
        
    def run(self):
        """Запуск заставки"""
        self.root.mainloop()