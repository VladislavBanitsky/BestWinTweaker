import psutil
import platform
import subprocess
import sys

def get_disk_type_windows(drive_letter='C:'):
    """Определение типа диска в Windows"""
    try:
        # Получаем информацию о диске через PowerShell
        cmd = f'powershell "Get-PhysicalDisk | Where-Object {{$_.DeviceId -eq (Get-Partition -DriveLetter {drive_letter[0]} | Get-Disk).Number}} | Select-Object MediaType"'
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if 'SSD' in result.stdout:
            return 'SSD'
        elif 'HDD' in result.stdout:
            return 'HDD'
    except Exception as e:
        print(f"Ошибка при определении типа диска в Windows: {e}")
    return 'Unknown'

def get_disk_type_linux(drive='/dev/sda'):
    """Определение типа диска в Linux"""
    try:
        # Проверяем через /sys/block
        disk_name = drive.replace('/dev/', '')
        
        # Метод 1: Проверка ротационности (HDD вращающиеся, SSD нет)
        rotational_path = f'/sys/block/{disk_name}/queue/rotational'
        with open(rotational_path, 'r') as f:
            is_rotational = int(f.read().strip())
            if is_rotational == 0:
                return 'SSD'
            elif is_rotational == 1:
                return 'HDD'
        
        # Метод 2: Через lsblk (альтернативный вариант)
        # result = subprocess.run(['lsblk', '-d', '-o', 'ROTA', disk_name], 
        #                        capture_output=True, text=True)
        # if '0' in result.stdout.split('\n')[1]:
        #     return 'SSD'
        # elif '1' in result.stdout.split('\n')[1]:
        #     return 'HDD'
            
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Ошибка при определении типа диска в Linux: {e}")
    return 'Unknown'

def get_disk_type_macos(drive='/dev/disk0'):
    """Определение типа диска в macOS"""
    try:
        # Используем system_profiler
        cmd = f'system_profiler SPStorageDataType | grep -A 10 "{drive}" | grep "Medium Type"'
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        if 'SSD' in result.stdout:
            return 'SSD'
        elif 'HDD' in result.stdout or 'Rotational' in result.stdout:
            return 'HDD'
        
        # Альтернативный метод через diskutil
        disk_name = drive.replace('/dev/', '')
        cmd = f'diskutil info {disk_name} | grep "Solid State"'
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if 'Yes' in result.stdout:
            return 'SSD'
        elif 'No' in result.stdout:
            return 'HDD'
            
    except Exception as e:
        print(f"Ошибка при определении типа диска в macOS: {e}")
    return 'Unknown'

def get_all_disks():
    """Получение списка всех дисков"""
    disks = []
    
    if platform.system() == 'Windows':
        # В Windows получаем все буквы дисков
        for partition in psutil.disk_partitions():
            if 'cdrom' not in partition.opts.lower():
                disks.append(partition.device)
    else:
        # В Linux/macOS получаем физические диски
        try:
            if platform.system() == 'Linux':
                # Получаем список блочных устройств
                for disk in psutil.disk_partitions():
                    if disk.device.startswith('/dev/sd') or disk.device.startswith('/dev/nvme'):
                        base_disk = disk.device.rstrip('0123456789')
                        if base_disk not in disks:
                            disks.append(base_disk)
            else:  # macOS
                for disk in psutil.disk_partitions():
                    if disk.device.startswith('/dev/disk'):
                        disks.append(disk.device)
        except:
            pass
    
    return disks if disks else ['C:' if platform.system() == 'Windows' else '/dev/sda']

def main():
    """Основная функция"""
    print("=" * 50)
    print("Определение типа накопителя (SSD/HDD)")
    print("=" * 50)
    
    system = platform.system()
    disks = get_all_disks()
    
    for disk in disks:
        if system == 'Windows':
            disk_type = get_disk_type_windows(disk)
        elif system == 'Linux':
            disk_type = get_disk_type_linux(disk)
        elif system == 'Darwin':  # macOS
            disk_type = get_disk_type_macos(disk)
        else:
            disk_type = 'Unknown'
            print(f"Неподдерживаемая ОС: {system}")
        
        print(f"Диск: {disk:<15} Тип: {disk_type}")
    
    print("=" * 50)
    
    # Дополнительная информация о дисках
    print("\nДополнительная информация о дисках:")
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            print(f"{partition.device} - {partition.mountpoint}")
            print(f"  Всего: {usage.total // (2**30)} GB")
            print(f"  Использовано: {usage.used // (2**30)} GB")
            print(f"  Свободно: {usage.free // (2**30)} GB")
            print(f"  Использовано: {usage.percent}%")
            print()
        except:
            pass

if __name__ == "__main__":
    # Проверка установки psutil
    try:
        import psutil
    except ImportError:
        print("Библиотека 'psutil' не установлена.")
        print("Установите её командой: pip install psutil")
        sys.exit(1)
    
    main()