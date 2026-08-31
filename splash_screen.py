# splash_screen.py
import customtkinter as ctk
from PIL import Image, ImageTk
import threading

from utilities import resource_path
from version import VERSION

class SplashScreen:
    """Заставка с поддержкой фоновой загрузки данных"""
    
    def __init__(self, initial_data=None, theme="Light"):
        self.theme = theme
        ctk.set_appearance_mode(self.theme)
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.overrideredirect(True)
        
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
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill='both', expand=True)
        
        center_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        center_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Логотип и название

        img = Image.open(resource_path('./resources/images/BestWinTweaker.png'))
        desired_size = (100, 100)
        img = img.resize(desired_size, Image.Resampling.LANCZOS)
        self.logo = ctk.CTkImage(light_image=img, dark_image=img, size=desired_size)
        logo_label = ctk.CTkLabel(center_frame, image=self.logo, text="")
        logo_label.image = self.logo
        logo_label.pack(pady=(0, 20))

        name_label = ctk.CTkLabel(
            center_frame,
            text="BestWinTweaker",
            font=('Segoe UI', 28, 'bold'),
            text_color='#00b4d8'
        )
        name_label.pack()
        
        ctk.CTkLabel(
            center_frame,
            text="Системный монитор и оптимизатор",
            font=('Segoe UI', 14),
            text_color='gray'
        ).pack()
        
        # Прогресс бар
        self.progress = ctk.CTkProgressBar(
            center_frame,
            width=350,
            height=12,
            mode='determinate'
        )
        self.progress.pack(pady=(15, 8))
        
        # Статус
        self.status_var = ctk.StringVar(value="Инициализация...")
        self.status_label = ctk.CTkLabel(
            center_frame,
            textvariable=self.status_var,
            font=('Segoe UI', 11),
            text_color='gray'
        )
        self.status_label.pack()
        
        # Версия
        ctk.CTkLabel(
            main_frame,
            text=f"BestWinTweaker {VERSION}",
            font=('Segoe UI', 12),
            text_color='gray'
        ).place(x=10, y=self.height - 25)
        
    def set_status(self, status, progress=None):
        """Обновление статуса"""
        self.status_var.set(status)
        if progress is not None:
            # CTkProgressBar принимает значения от 0.0 до 1.0
            # Преобразуем проценты (0-100) в дробное значение (0.0-1.0)
            progress_value = progress / 100.0
            # Ограничиваем значения в допустимых пределах
            progress_value = max(0.0, min(1.0, progress_value))
            self.progress.set(progress_value)
            # Принудительно обновляем UI
            self.root.update_idletasks()
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