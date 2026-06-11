import webbrowser
import tempfile
import requests
import sys
import os
from tkinter import messagebox
import subprocess
import traceback

# Функция для корректного поиска файлов
def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсу, работает для dev и для PyInstaller """
    if hasattr(sys, '_MEIPASS'):  # Если запущено из EXE
        base_path = sys._MEIPASS
    else:  # Если запущено из скрипта
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Функция для открытия ссылки в браузере
def callback(url):
    webbrowser.open_new(url)

# Функция для получения текущей версии Windows
def get_windows_version():
    try:
        version = sys.getwindowsversion()
        major = version.major
        if major >= 10:
            return "10/11"
        elif major == 6 and version.minor == 1:
            return "7"
        elif major == 6 and version.minor == 2:
            return "8"
        elif major == 6 and version.minor == 3:
            return "8.1"
        else:
            return "old"
    except:
        return "unknown"

# Функция для скачивания актуальной версии Fido.ps1 с GitHub
def download_fido_script():
    try:       
        fido_url = "https://raw.githubusercontent.com/pbatard/Fido/master/Fido.ps1"
        temp_dir = tempfile.gettempdir()
        fido_script_path = os.path.join(temp_dir, "Fido.ps1")
        
        print(f"Скачивание Fido из: {fido_url}")
        response = requests.get(fido_url, timeout=30)
        response.raise_for_status()
        
        with open(fido_script_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"Fido сохранен в: {fido_script_path}")
        return fido_script_path
        
    except Exception as e:
        print(f"Ошибка загрузки Fido: {str(e)}")
        traceback.print_exc()
        return ""

# Функция для скачивания ISO Windows
def start_download():
    print("start_download() вызвана")
    
    try:
        # Проверка Windows 7
        win_ver = get_windows_version()
        print(f"Версия Windows: {win_ver}")
        
        if win_ver == "7":
            url = "https://www.microsoft.com/ru-ru/software-download/windows11"
            webbrowser.open(url)
            messagebox.showinfo("Открыт браузер", "Windows 7 не поддерживает автоматическое скачивание.\nСтраница загрузки Windows открыта в браузере.")
            return
        
        # Скачиваем Fido
        fido_script_path = download_fido_script()
        print(f"Путь к Fido: {fido_script_path}")
        
        if fido_script_path and os.path.exists(fido_script_path):
            # Создаем PowerShell скрипт, который покажет окно и не закроется сразу
            ps_script_path = os.path.join(tempfile.gettempdir(), "download_windows.ps1")
            with open(ps_script_path, 'w', encoding='utf-8') as f:
                f.write(f'''
# Импортируем Fido
. "{fido_script_path}"

# Ждем нажатия клавиши перед закрытием
Write-Host ""
Write-Host "===================================="
Write-Host "Скрипт Fido завершил работу"
Write-Host "Нажмите любую клавишу для закрытия..."
Write-Host "===================================="
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
''')
            
            # Запускаем PowerShell с видимым окном (без windowed режима)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            subprocess.Popen([
                "powershell.exe",
                "-ExecutionPolicy", "Bypass",
                "-File", ps_script_path
            ], startupinfo=startupinfo)
            
            messagebox.showinfo("Запущено", "Открыто окно PowerShell со скриптом Fido.\nСледуйте инструкциям для скачивания Windows.")
        else:
            url = "https://www.microsoft.com/ru-ru/software-download/windows11"
            webbrowser.open(url)
            messagebox.showinfo("Открыт браузер", "Автоматическое скачивание недоступно.\nСтраница загрузки Windows открыта в браузере.")
    
    except Exception as e:
        print(f"Ошибка в start_download: {str(e)}")
        traceback.print_exc()
        messagebox.showerror("Ошибка", f"Произошла ошибка:\n{str(e)}")