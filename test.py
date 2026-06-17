import os
import subprocess
import re
import socket
import platform
import sys

class NetworkAdapterDetector:
    def __init__(self):
        self.system = platform.system()
        self.adapters = []
        
    def get_adapters_wmic(self):
        """Метод 1: Использование WMIC для получения информации о сетевых картах"""
        try:
            # Используем wmic для получения информации о сетевых адаптерах
            cmd = 'wmic nic where "NetEnabled=True" get Name,Index,MACAddress,Speed,NetConnectionID /format:csv'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='cp866')
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    # Пропускаем заголовок
                    for line in lines[1:]:
                        if line.strip():
                            parts = line.split(',')
                            if len(parts) >= 5:
                                adapter = {
                                    'name': parts[1] if len(parts) > 1 else 'N/A',
                                    'index': parts[2] if len(parts) > 2 else 'N/A',
                                    'mac': parts[3] if len(parts) > 3 else 'N/A',
                                    'speed': parts[4] if len(parts) > 4 else 'N/A',
                                    'connection_id': parts[5] if len(parts) > 5 else 'N/A'
                                }
                                self.adapters.append(adapter)
            return True
        except Exception as e:
            print(f"Ошибка при использовании WMIC: {e}")
            return False
    
    def get_adapters_ipconfig(self):
        """Метод 2: Использование ipconfig для получения информации"""
        try:
            cmd = 'ipconfig /all'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='cp866')
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                current_adapter = {}
                adapter_found = False
                
                for line in lines:
                    # Ищем начало описания адаптера
                    if 'Адаптер' in line or 'Ethernet adapter' in line or 'Wireless LAN adapter' in line:
                        if current_adapter and adapter_found:
                            self.adapters.append(current_adapter)
                        current_adapter = {}
                        adapter_found = True
                        # Извлекаем имя адаптера
                        name_match = re.search(r'Адаптер (.*?):|Ethernet adapter (.*?):|Wireless LAN adapter (.*?):', line)
                        if name_match:
                            name = name_match.group(1) or name_match.group(2) or name_match.group(3)
                            current_adapter['name'] = name.strip()
                        else:
                            current_adapter['name'] = 'Unknown'
                    
                    # Извлекаем MAC-адрес
                    if 'Physical Address' in line or 'Физический адрес' in line:
                        mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', line)
                        if mac_match:
                            current_adapter['mac'] = mac_match.group(0)
                    
                    # Извлекаем IP-адрес
                    if 'IPv4 Address' in line or 'IPv4-адрес' in line or 'IP Address' in line:
                        ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                        if ip_match:
                            current_adapter['ip'] = ip_match.group(0)
                    
                    # Извлекаем DHCP статус
                    if 'DHCP Enabled' in line or 'DHCP включен' in line:
                        if 'Yes' in line or 'Да' in line:
                            current_adapter['dhcp'] = 'Enabled'
                        else:
                            current_adapter['dhcp'] = 'Disabled'
                
                # Добавляем последний адаптер
                if current_adapter and adapter_found:
                    self.adapters.append(current_adapter)
            
            return True
        except Exception as e:
            print(f"Ошибка при использовании ipconfig: {e}")
            return False
    
    def get_adapters_socket(self):
        """Метод 3: Использование socket для получения локальных IP адресов"""
        try:
            hostname = socket.gethostname()
            ip_addresses = socket.gethostbyname_ex(hostname)
            
            if ip_addresses:
                adapter_info = {
                    'name': hostname,
                    'ip': ', '.join(ip_addresses[2]),
                    'method': 'socket'
                }
                self.adapters.append(adapter_info)
            return True
        except Exception as e:
            print(f"Ошибка при использовании socket: {e}")
            return False
    
    def get_adapters_netstat(self):
        """Метод 4: Использование netstat для получения активных подключений"""
        try:
            cmd = 'netstat -r'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='cp866')
            
            if result.returncode == 0:
                # Простой парсинг, чтобы показать активные маршруты
                lines = result.stdout.split('\n')
                for line in lines:
                    if '0.0.0.0' in line and '255.255.255.255' in line:
                        # Находим интерфейс
                        interface_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                        if interface_match:
                            adapter_info = {
                                'name': 'Active Interface',
                                'ip': interface_match.group(0),
                                'method': 'netstat'
                            }
                            self.adapters.append(adapter_info)
                            break
            return True
        except Exception as e:
            print(f"Ошибка при использовании netstat: {e}")
            return False
    
    def get_all_adapters(self):
        """Получение информации о всех сетевых адаптерах"""
        # Пытаемся получить информацию всеми доступными методами
        self.get_adapters_wmic()
        self.get_adapters_ipconfig()
        self.get_adapters_socket()
        self.get_adapters_netstat()
        
        # Удаляем дубликаты на основе MAC-адреса
        unique_adapters = []
        seen_mac = set()
        
        for adapter in self.adapters:
            mac = adapter.get('mac', '')
            if mac and mac not in seen_mac:
                seen_mac.add(mac)
                unique_adapters.append(adapter)
            elif not mac:
                # Если MAC нет, добавляем все равно (может быть виртуальный адаптер)
                unique_adapters.append(adapter)
        
        self.adapters = unique_adapters
        return self.adapters
    
    def display_adapters(self):
        """Отображение информации о сетевых адаптерах в читаемом формате"""
        if not self.adapters:
            print("Сетевые адаптеры не найдены!")
            return
        
        print("=" * 80)
        print("ИНФОРМАЦИЯ О СЕТЕВЫХ АДАПТЕРАХ")
        print("=" * 80)
        
        for i, adapter in enumerate(self.adapters, 1):
            print(f"\nАдаптер #{i}:")
            print("-" * 40)
            
            # Выводим всю доступную информацию
            for key, value in adapter.items():
                if value and value != 'N/A':
                    # Переводим ключи на русский для удобства
                    key_map = {
                        'name': 'Имя',
                        'index': 'Индекс',
                        'mac': 'MAC-адрес',
                        'speed': 'Скорость (бит/с)',
                        'connection_id': 'ID соединения',
                        'ip': 'IP-адрес',
                        'dhcp': 'DHCP',
                        'method': 'Метод получения'
                    }
                    display_key = key_map.get(key, key)
                    print(f"  {display_key}: {value}")
        
        print("\n" + "=" * 80)
        print(f"Всего найдено адаптеров: {len(self.adapters)}")
    
    def get_adapter_info(self, adapter_name=None):
        """Получение информации о конкретном адаптере"""
        if not adapter_name:
            # Если имя не указано, возвращаем первый активный адаптер
            for adapter in self.adapters:
                if 'ip' in adapter and adapter['ip'] != 'N/A':
                    return adapter
            return self.adapters[0] if self.adapters else None
        
        for adapter in self.adapters:
            if adapter_name.lower() in adapter.get('name', '').lower():
                return adapter
        return None

def main():
    """Главная функция"""
    print("Программа определения сетевых карт для Windows 7")
    print("=" * 60)
    
    # Проверяем, что система - Windows
    if platform.system() != 'Windows':
        print("Внимание: Эта программа оптимизирована для Windows!")
        print(f"Текущая система: {platform.system()}")
    
    # Создаем экземпляр детектора
    detector = NetworkAdapterDetector()
    
    # Получаем информацию о всех адаптерах
    print("Сканирование сетевых адаптеров...")
    adapters = detector.get_all_adapters()
    
    # Отображаем информацию
    detector.display_adapters()
    
    # Дополнительная информация о конкретном адаптере
    print("\nДополнительная информация:")
    print("-" * 40)
    
    # Показываем активный адаптер
    active_adapter = detector.get_adapter_info()
    if active_adapter:
        print("Активный адаптер:")
        for key, value in active_adapter.items():
            if value and value != 'N/A':
                print(f"  {key}: {value}")
    
    # Сохраняем результаты в файл
    save_to_file = input("\nСохранить информацию в файл? (y/n): ")
    if save_to_file.lower() == 'y':
        filename = 'network_adapters_info.txt'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("ИНФОРМАЦИЯ О СЕТЕВЫХ АДАПТЕРАХ\n")
            f.write("=" * 80 + "\n\n")
            
            for i, adapter in enumerate(adapters, 1):
                f.write(f"Адаптер #{i}:\n")
                f.write("-" * 40 + "\n")
                for key, value in adapter.items():
                    if value and value != 'N/A':
                        f.write(f"  {key}: {value}\n")
                f.write("\n")
            
            f.write(f"\nВсего найдено адаптеров: {len(adapters)}")
        
        print(f"Информация сохранена в файл: {filename}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nПрограмма прервана пользователем")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        print("Пожалуйста, убедитесь, что у вас есть необходимые права доступа")
        input("Нажмите Enter для выхода...")