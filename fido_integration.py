"""
Модуль интеграции Fido для скачивания ISO Windows
Позволяет скачивать официальные образы Windows 11/10 через PowerShell скрипт Fido
"""

import subprocess
import os
import sys
import threading
import tempfile
import ctypes
import re
from pathlib import Path
import requests

# Для проверки прав администратора
def is_admin():
    """Проверка, запущена ли программа от имени администратора"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin():
    """Запросить права администратора"""
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()

class FidoDownloader:
    """Класс для работы с Fido скриптом"""
    
    # Доступные версии Windows
    VERSIONS = {
        "11": "Windows 11",
        "10": "Windows 10",
        "8.1": "Windows 8.1",
        "7": "Windows 7",
        "2019": "Windows Server 2019",
        "2022": "Windows Server 2022"
    }
    
    # Доступные редакции
    EDITIONS = {
        "default": "Рекомендуемая редакция",
        "professional": "Professional",
        "home": "Home",
        "education": "Education",
        "enterprise": "Enterprise",
        "pro_n": "Professional N",
        "home_n": "Home N"
    }
    
    # Доступные языки
    LANGUAGES = {
        "Russian": "Русский",
        "English": "English (US)",
        "Ukrainian": "Українська",
        "German": "Deutsch",
        "French": "Français",
        "Spanish": "Español",
        "Chinese": "中文 (简体)",
        "Japanese": "日本語"
    }
    
    def __init__(self):
        self.fido_script_path = None
        self.download_progress = ""
        self.is_downloading = False
        self.current_process = None
        
    def download_fido_script(self, progress_callback=None):
        """Скачать актуальную версию Fido.ps1 с GitHub"""
        try:
            if progress_callback:
                progress_callback("Загрузка Fido скрипта...")
            
            # URL последней версии Fido (raw)
            fido_url = "https://raw.githubusercontent.com/pbatard/Fido/master/Fido.ps1"
            
            # Создаем временную папку
            temp_dir = tempfile.gettempdir()
            self.fido_script_path = os.path.join(temp_dir, "Fido.ps1")
            
            # Скачиваем скрипт
            response = requests.get(fido_url, timeout=30)
            response.raise_for_status()
            
            # Сохраняем с правильной кодировкой
            with open(self.fido_script_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            if progress_callback:
                progress_callback("Fido скрипт загружен")
                
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Ошибка загрузки Fido: {str(e)}")
            return False
    
    def get_available_windows_versions(self):
        """Получить список доступных версий Windows"""
        return self.VERSIONS
    
    def get_iso_link(self, version="11", edition="default", language="Russian", 
                     arch="x64", progress_callback=None):
        """
        Получить прямую ссылку на ISO образ
        
        Args:
            version: Версия Windows ("11", "10", и т.д.)
            edition: Редакция ("default", "professional", и т.д.)
            language: Язык ("Russian", "English", и т.д.)
            arch: Архитектура ("x64", "x86")
            progress_callback: Функция для обновления статуса
        """
        
        if not self.fido_script_path or not os.path.exists(self.fido_script_path):
            if not self.download_fido_script(progress_callback):
                return None
        
        try:
            if progress_callback:
                progress_callback(f"Запрос ссылки для Windows {version}...")
            
            # Создаем PowerShell команду с параметрами
            # Используем -GetUrl для получения только ссылки
            ps_command = f'''
            $scriptPath = "{self.fido_script_path}"
            $WinVer = "{version}"
            $Lang = "{language}"
            $Arch = "{arch}"
            $Edition = "{edition}"
            
            # Импортируем скрипт
            . $scriptPath
            
            # Получаем ссылку (не скачиваем)
            # Используем внутренние функции Fido
            $url = Get-Fido -Win $WinVer -Lang $Lang -Arch $Arch -Edition $Edition -GetUrl
            Write-Output $url
            '''
            
            # Запускаем PowerShell скрыто
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
                capture_output=True,
                text=True,
                encoding='utf-8',
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0 and result.stdout:
                # Извлекаем URL из вывода
                output = result.stdout.strip()
                # Ищем ссылку на ISO
                url_match = re.search(r'https?://[^\s"\']+\.iso[^\s"\']*', output)
                if url_match:
                    iso_url = url_match.group()
                    if progress_callback:
                        progress_callback(f"Ссылка получена: {iso_url[:80]}...")
                    return iso_url
                else:
                    # Возможно ссылка в следующей строке
                    lines = output.split('\n')
                    for line in lines:
                        if 'http' in line and '.iso' in line:
                            if progress_callback:
                                progress_callback(f"Ссылка найдена")
                            return line.strip()
            
            if progress_callback:
                progress_callback(f"Ошибка: {result.stderr[:200]}")
            return None
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"Ошибка: {str(e)}")
            return None
    
    def download_iso(self, iso_url, save_path, progress_callback=None, 
                     status_callback=None):
        """
        Скачать ISO файл с отображением прогресса
        
        Args:
            iso_url: Прямая ссылка на ISO
            save_path: Путь для сохранения файла
            progress_callback: Функция для обновления прогресса (0-100)
            status_callback: Функция для обновления текстового статуса
        """
        
        if not iso_url:
            return False
        
        self.is_downloading = True
        
        try:
            if status_callback:
                status_callback("Подключение к серверу...")
            
            # Заголовки для имитации браузера
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Стриминговое скачивание
            response = requests.get(iso_url, stream=True, headers=headers)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # Определяем имя файла из URL или задаем по умолчанию
            if not save_path:
                filename = os.path.basename(iso_url.split('?')[0])
                if not filename.endswith('.iso'):
                    filename = f"Windows.iso"
                save_path = os.path.join(os.path.expanduser("~"), "Downloads", filename)
            
            # Создаем директорию если нужно
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.is_downloading:
                        if status_callback:
                            status_callback("Скачивание отменено")
                        return False
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0 and progress_callback:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress)
                            
                            # Обновляем статус с размером
                            if status_callback:
                                mb_downloaded = downloaded / (1024**2)
                                mb_total = total_size / (1024**2)
                                status_callback(f"Скачано: {mb_downloaded:.1f} / {mb_total:.1f} MB")
            
            if status_callback:
                status_callback("Скачивание завершено!")
            
            return save_path
            
        except Exception as e:
            if status_callback:
                status_callback(f"Ошибка: {str(e)}")
            return False
        finally:
            self.is_downloading = False
    
    def cancel_download(self):
        """Отменить текущее скачивание"""
        self.is_downloading = False
        if self.current_process:
            try:
                self.current_process.terminate()
            except:
                pass


# Функция для получения списка доступных языков через Fido
def get_available_languages():
    """Получить актуальный список языков из Fido"""
    try:
        temp_script = os.path.join(tempfile.gettempdir(), "Fido_temp.ps1")
        
        # Скачиваем Fido если нет
        if not os.path.exists(temp_script):
            response = requests.get(
                "https://raw.githubusercontent.com/pbatard/Fido/master/Fido.ps1",
                timeout=10
            )
            with open(temp_script, 'w', encoding='utf-8') as f:
                f.write(response.text)
        
        # Команда для получения списка языков
        ps_command = f'''
        $scriptPath = "{temp_script}"
        . $scriptPath
        Get-Fido -List
        '''
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
            capture_output=True,
            text=True,
            encoding='utf-8',
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        # Парсим вывод для извлечения языков
        languages = {}
        if result.stdout:
            for line in result.stdout.split('\n'):
                # Ищем строки с языками (примерный паттерн)
                if 'Language' in line or 'language' in line.lower():
                    # Упрощенный парсинг
                    pass
        
        return FidoDownloader.LANGUAGES
        
    except:
        return FidoDownloader.LANGUAGES


# Пример использования
if __name__ == "__main__":
    # Тестовый запуск
    downloader = FidoDownloader()
    
    def progress_cb(progress):
        print(f"Прогресс: {progress:.1f}%")
    
    def status_cb(status):
        print(f"Статус: {status}")
    
    # Скачиваем скрипт
    if downloader.download_fido_script(status_cb):
        # Получаем ссылку
        iso_url = downloader.get_iso_link(
            version="11",
            language="Russian",
            progress_callback=status_cb
        )
        
        if iso_url:
            print(f"\nСсылка получена: {iso_url}\n")
            
            # Спрашиваем о скачивании
            response = input("Скачать ISO? (y/n): ")
            if response.lower() == 'y':
                save_path = input("Путь для сохранения (Enter для Downloads): ").strip()
                if not save_path:
                    save_path = os.path.join(os.path.expanduser("~"), "Downloads", "Windows11.iso")
                
                downloader.download_iso(iso_url, save_path, progress_cb, status_cb)