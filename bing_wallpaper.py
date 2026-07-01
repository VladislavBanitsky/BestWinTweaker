import requests
import ctypes
import os
import tempfile
import traceback
from pathlib import Path
from datetime import datetime

class BingWallpaper:
    """Класс для работы с Bing Wallpaper API"""
    
    API_URL = "https://bing.biturl.top/"
    
    @staticmethod
    def get_wallpaper_info(resolution="UHD", mkt="ru-RU", index=0):
        """
        Получает информацию об изображении от API.
        
        Args:
            resolution (str): Разрешение. По умолчанию "UHD".
            mkt (str): Регион. По умолчанию "ru-RU".
            index (int): Индекс изображения. 0 - сегодня, 1 - вчера, и т.д.
            
        Returns:
            dict: Словарь с информацией об изображении или None в случае ошибки.
        """
        try:
            params = {
                "format": "json",
                "resolution": resolution,
                "mkt": mkt,
                "index": index
            }
            
            response = requests.get(BingWallpaper.API_URL, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # Проверяем, что URL начинается с https://www.bing.com
            if data.get("url") and data["url"].startswith("https://www.bing.com"):
                return data
            else:
                print(f"Получен некорректный URL: {data.get('url')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Ошибка сети при получении обоев: {e}")
            return None
        except ValueError as e:
            print(f"Ошибка парсинга JSON: {e}")
            return None
        except Exception as e:
            print(f"Непредвиденная ошибка: {e}")
            traceback.print_exc()
            return None
    
    @staticmethod
    def download_wallpaper(image_info, save_path=None):
        """
        Скачивает изображение по URL из информации.
        
        Args:
            image_info (dict): Словарь с информацией об изображении.
            save_path (str, optional): Путь для сохранения. 
                                       Если None, сохраняется во временную папку.
            
        Returns:
            tuple: (путь_к_файлу, словарь_с_информацией) или (None, None)
        """
        if not image_info or "url" not in image_info:
            return None, None
        
        try:
            image_url = image_info["url"]
            
            # Получаем расширение файла из URL
            ext = os.path.splitext(image_url)[1]
            if not ext:
                ext = ".jpg"  # По умолчанию
            
            # Формируем имя файла: Bing_YYYY-MM-DD.ext
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"Bing_{date_str}{ext}"
            
            if save_path:
                # Если указан путь, сохраняем туда
                file_path = os.path.join(save_path, filename)
                os.makedirs(save_path, exist_ok=True)
            else:
                # Иначе во временную папку
                temp_dir = tempfile.gettempdir()
                file_path = os.path.join(temp_dir, filename)
            
            # Скачиваем изображение
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"Обои сохранены: {file_path}")
            return file_path, image_info
            
        except requests.exceptions.RequestException as e:
            print(f"Ошибка сети при скачивании обоев: {e}")
            return None, None
        except Exception as e:
            print(f"Ошибка при сохранении файла: {e}")
            traceback.print_exc()
            return None, None
    
    @staticmethod
    def set_wallpaper(file_path):
        """
        Устанавливает изображение как обои рабочего стола Windows.
        
        Args:
            file_path (str): Путь к файлу изображения.
            
        Returns:
            bool: True в случае успеха, False в случае ошибки.
        """
        try:
            if not os.path.exists(file_path):
                print(f"Файл не найден: {file_path}")
                return False
            
            # Используем ctypes для вызова Windows API
            # SPI_SETDESKWALLPAPER = 0x0014 (20)
            # SPIF_UPDATEINIFILE = 0x01
            # SPIF_SENDWININICHANGE = 0x02
            result = ctypes.windll.user32.SystemParametersInfoW(20, 0, file_path, 3)
            
            if result:
                print(f"Обои успешно установлены: {file_path}")
            else:
                print("Не удалось установить обои.")
                
            return bool(result)
            
        except Exception as e:
            print(f"Ошибка при установке обоев: {e}")
            traceback.print_exc()
            return False
    
    @staticmethod
    def fetch_and_set_wallpaper(resolution="UHD", mkt="ru-RU", index=0, save_path=None):
        """
        Полный цикл: получение информации, скачивание и установка обоев.
        
        Args:
            resolution (str): Разрешение.
            mkt (str): Регион.
            index (int): Индекс изображения.
            save_path (str, optional): Путь для сохранения файла.
            
        Returns:
            tuple: (успех_ли_операция, сообщение_для_пользователя)
        """
        try:
            # 1. Получаем информацию
            image_info = BingWallpaper.get_wallpaper_info(resolution, mkt, index)
            if not image_info:
                return False, "Не удалось получить информацию об изображении."
            
            # 2. Скачиваем изображение
            file_path, info = BingWallpaper.download_wallpaper(image_info, save_path)
            if not file_path:
                return False, "Не удалось скачать изображение."
            
            # 3. Устанавливаем как обои
            success = BingWallpaper.set_wallpaper(file_path)
            if success:
                copyright_text = info.get("copyright", "Bing Wallpaper")
                return True, f"Обои установлены! — {copyright_text}"
            else:
                return False, "Не удалось установить изображение как обои."
                
        except Exception as e:
            print(f"Ошибка в fetch_and_set_wallpaper: {e}")
            traceback.print_exc()
            return False, f"Произошла ошибка: {str(e)}"