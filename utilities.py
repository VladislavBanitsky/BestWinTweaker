# Дополнительные утилиты

import webbrowser
import tempfile
import requests
import sys
import os
import wmi
from tkinter import messagebox
import subprocess
import traceback
import pythoncom

# Функция для проверки типа диска
def get_disk_type(drive_letter='C:'):
    """Определение типа диска в Windows (работает в потоках)"""
    pythoncom.CoInitialize()  # инициализируем COM для текущего потока (важно!)
    try:
        c = wmi.WMI()
        drive_letter_clean = drive_letter[0] if drive_letter else 'C'
        
        # Получаем информацию о физическом диске (# Windows 7)
        for disk in c.Win32_DiskDrive():
            disk_type = ""
            # Находим соответствие между диском и буквой
            for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
                for logical_disk in partition.associators("Win32_LogicalDiskToPartition"):
                    if logical_disk.DeviceID == f"{drive_letter_clean}:":
                        model = disk.Model.lower() if disk.Model else ""
                        # Анализируем модель диска
                        if any(ssd_indicator in model for ssd_indicator in ['ssd', 'nvme', 'solid state', 'xpg', 'adata']):
                            disk_type = 'SSD '
                        elif any(hdd_indicator in model for hdd_indicator in ['hdd', 'st1000', 'wd10', 'hgst']):
                            disk_type = 'HDD '
                        else:
                            # Получаем информацию о диске через PowerShell (# Windows 8-11)
                            cmd = f'powershell "Get-PhysicalDisk | Where-Object {{$_.DeviceId -eq (Get-Partition -DriveLetter {drive_letter[0]} | Get-Disk).Number}} | Select-Object MediaType"'
                            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                            if 'SSD' in result.stdout:  
                                disk_type = 'SSD '
                            elif 'HDD' in result.stdout:
                                disk_type = 'HDD '                        
                        # Если по модели не определили, пробуем через другие поля
                        if hasattr(disk, 'MediaType') and disk.MediaType:
                            if 'SSD' in disk.MediaType:
                                disk_type = 'SSD '           
                        return disk_type + disk.Model if disk.Model else 'Unknown'  # возвращаем тип и модель для информации           
    except Exception as e:
        print(f"Ошибка при определении типа диска: {e}")
        traceback.print_exc()
    finally:
        # Обязательно освобождаем COM
        pythoncom.CoUninitialize()
    return 'Unknown'

# Функция для получения информации об оперативной памяти
def get_ddr_info():
            """
            Получает информацию о модулях памяти через WMI на Windows.
            Возвращает список словарей с данными о каждом модуле.
            """
            c = wmi.WMI()
            memory_modules = []

            # Значения идентификации типа памяти из Win32_PhysicalMemory
            memory_type_map = {
                0: "Unknown",
                1: "Other",
                2: "DRAM",
                3: "Synchronous DRAM",
                4: "Cache DRAM",
                5: "EDO",
                6: "EDRAM",
                7: "VRAM",
                8: "SRAM",
                9: "RAM",
                10: "ROM",
                11: "Flash",
                12: "EEPROM",
                13: "FEPROM",
                14: "EPROM",
                15: "CDRAM",
                16: "3DRAM",
                17: "SDRAM",
                18: "SGRAM",
                19: "RDRAM",
                20: "DDR",        # DDR (DDR1)
                21: "DDR2",
                22: "DDR2 FB-DIMM",
                24: "DDR3",       # DDR3
                25: "FBD2",
                26: "DDR4",       # DDR4
                27: "LPDDR",
                28: "LPDDR2",
                29: "LPDDR3",
                30: "LPDDR4",
                31: "DDR5",       # DDR5 (современные системы)
            }

            for mem in c.Win32_PhysicalMemory():
                mem_type = memory_type_map.get(mem.MemoryType, "Unknown")
                capacity_bytes = getattr(mem, 'Capacity', 0)
                if capacity_bytes:
                    capacity_gb = int(capacity_bytes) / (1024 ** 3)
                else:
                    capacity_gb = 0

                speed = getattr(mem, 'Speed', None)
                manufacturer = getattr(mem, 'Manufacturer', 'Unknown')
                part_number = getattr(mem, 'PartNumber', 'Unknown')
                bank_label = getattr(mem, 'BankLabel', 'Unknown')
                device_locator = getattr(mem, 'DeviceLocator', 'Unknown')

                memory_modules.append({
                    "type": mem_type,
                    "capacity_gb": capacity_gb,
                    "speed_mhz": speed if speed and speed > 0 else None,
                    "manufacturer": manufacturer.strip() if manufacturer else "Unknown",
                    "part_number": part_number.strip() if part_number else "Unknown",
                    "bank": bank_label,
                    "slot": device_locator,
                })           
            return memory_modules

# Функция для получения типа оперативной памяти
def get_ddr_type():
    """Определение типа DDR с поддержкой Windows 7"""
    ddr_list = get_ddr_info()
    ddr_type = ""
    if not ddr_list:
        ddr_type = "Unknown"
        return ddr_type
    
    memory_info = ddr_list[0]
    
    # 1. Сначала пробуем MemoryType
    ddr_type = memory_info.get('type', 'Unknown')
    
    # 2. Пробуем извлечь из PartNumber
    part_number = memory_info.get('part_number', '')
    if part_number and part_number != "Unknown":
        # Ищем индикаторы в PartNumber
        part_upper = part_number.upper()
        if 'PC2' in part_upper:
            ddr_type = 'DDR2 '
        elif 'PC3' in part_upper:
            ddr_type = 'DDR3 '
        elif 'PC4' in part_upper:
            ddr_type = 'DDR4 '
        elif 'PC5' in part_upper:
            ddr_type = 'DDR5 '
    
    # 3. Пробуем определить по скорости (Speed)
    speed = memory_info.get('speed_mhz', 0)
    if speed:
        if 400 <= speed <= 800:
            ddr_type = 'DDR2 '
        elif 800 <= speed <= 1600:
            ddr_type = 'DDR3 '
        elif 1600 <= speed <= 3200:
            ddr_type = 'DDR4 '
        elif 3200 <= speed <= 6400:
            ddr_type = 'DDR5 '
            
    return ddr_type + str(speed) +"МГц (" + part_number + ")"

# Функция для получения модели материнской платы      
def get_board_model():
    c = wmi.WMI()
    # Запрашиваем информацию о материнской плате (BaseBoard)
    for board in c.Win32_BaseBoard():
        board_brand = board.Manufacturer
        board_model = board.Product  # Модель обычно хранится в Product
    return board_brand + " " + board_model

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