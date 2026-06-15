# start_app.py
# Альтернативная версия с использованием after()

import multiprocessing
import sys

from splash_screen import SplashScreen
from BestWinTweaker import BestWinTweaker

class AppLauncher:
    """Класс для запуска приложения с заставкой"""
    
    def __init__(self):
        self.splash = None
        self.app = None
        self.loading_step = 0
        
        # Этапы загрузки
        self.loading_steps = [
            ("Загрузка компонентов", 10),
            ("Инициализация модулей", 30),
            ("Настройка интерфейса", 60),
            ("Проверка системы", 80),
            ("Запуск приложения", 95)
        ]
        
    def start(self):
        """Запуск процесса загрузки"""      
        # Создаем заставку
        self.splash = SplashScreen()
        
        # Начинаем загрузку
        self.next_loading_step()
        
        # Запускаем главный цикл заставки
        self.splash.run()
        
    def next_loading_step(self):
        """Следующий шаг загрузки"""
        if self.loading_step < len(self.loading_steps):
            status, progress = self.loading_steps[self.loading_step]
            self.splash.set_status(status, progress)
            self.loading_step += 1
            # Запланировать следующий шаг через 300 мс
            self.splash.root.after(300, self.next_loading_step)
        else:
            # Загрузка завершена, запускаем приложение
            self.start_app()
            
    def start_app(self):
        """Запуск основного приложения"""
        try:            
            self.splash.set_status("Готово", 100)
            self.splash.root.after(200, self.finish_loading)
        except Exception as e:
            self.show_error(e)
            
    def finish_loading(self):
        """Завершение загрузки"""
        self.splash.close()
        # Запускаем основное приложение
        self.app = BestWinTweaker()
        self.app.run()
        
    def show_error(self, error):
        """Показать ошибку"""
        self.splash.set_status(f"Ошибка: {str(error)[:40]}", 100)
        self.splash.root.after(2000, lambda: self.splash.close())
        print(f"Ошибка: {error}")

def main():
    """Главная функция"""
    launcher = AppLauncher()
    launcher.start()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()