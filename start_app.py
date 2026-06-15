# start_app.py
import multiprocessing
import threading
import time
from splash_screen import SplashScreen
from data_loader import DataLoader

class AppLauncher:
    """Класс для запуска приложения с заставкой и фоновой загрузкой"""
    
    def __init__(self):
        self.splash = None
        self.app = None
        self.loaded_data = None
        
    def start(self):
        """Запуск процесса загрузки"""      
        # Создаем заставку
        self.splash = SplashScreen()
        
        # Запускаем загрузку данных в отдельном потоке
        loading_thread = threading.Thread(target=self.load_data_in_background)
        loading_thread.daemon = True
        loading_thread.start()
        
        # Запускаем главный цикл заставки
        self.splash.run()
        
    def load_data_in_background(self):
        """Загрузка данных в фоновом режиме"""
        try:
            # Создаем загрузчик данных
            loader = DataLoader(self.splash)
            
            # Загружаем все данные
            self.loaded_data = loader.load_all_data()
            
            # Ждем немного для плавности
            time.sleep(0.5)
            
            # Запускаем основное приложение
            self.splash.root.after(0, self.start_app)
            
        except Exception as e:
            self.splash.set_status(f"Ошибка: {str(e)[:40]}", 100)
            self.splash.root.after(2000, lambda: self.splash.close())
            print(f"Ошибка загрузки: {e}")
            
    def start_app(self):
        """Запуск основного приложения с переданными данными"""
        try:
            self.splash.close()
            
            # Импортируем BestWinTweaker после загрузки
            from BestWinTweaker import BestWinTweaker
            
            # Запускаем приложение с предзагруженными данными
            self.app = BestWinTweaker(initial_data=self.loaded_data)
            self.app.run()
            
        except Exception as e:
            print(f"Ошибка запуска: {e}")

def main():
    """Главная функция"""
    launcher = AppLauncher()
    launcher.start()

if __name__ == "__main__":
    # Pyinstaller fix
    multiprocessing.freeze_support()
    main()