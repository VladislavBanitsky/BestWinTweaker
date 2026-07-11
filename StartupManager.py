import os
import sys
import ctypes
import winreg
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

# Константы для работы с реестром
HKEY_CURRENT_USER = winreg.HKEY_CURRENT_USER
HKEY_LOCAL_MACHINE = winreg.HKEY_LOCAL_MACHINE

# Пути автозагрузки в реестре
REG_PATH_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_PATH_RUN_ONCE = r"Software\Microsoft\Windows\CurrentVersion\RunOnce"
REG_PATH_RUN_32 = r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"

# Константы для уведомления системы об изменениях
SHCNE_ASSOCCHANGED = 0x08000000
SHCNF_IDLIST = 0x0000
HWND_BROADCAST = 0xFFFF
WM_SETTINGCHANGE = 0x001A


@dataclass
class StartupEntry:
    """Класс для хранения информации о записи автозагрузки"""
    name: str
    path: str
    source: str  # 'HKCU\Run', 'HKLM\Run', 'HKLM\Run (32-bit)', 'Startup Folder'
    enabled: bool
    
    def __str__(self):
        status = "✅ Включено" if self.enabled else "❌ Отключено"
        return f"{self.name} ({self.source}) - {status}"


class StartupManager:
    """
    Класс для управления автозагрузкой приложений в Windows.
    Поддерживает работу с реестром и папкой автозагрузки.
    """
    
    def __init__(self):
        """Инициализация менеджера автозагрузки"""
        self._startup_folder = self._get_startup_folder_path()
        self._cache = {}
    
    def _get_startup_folder_path(self) -> Path:
        """Получает путь к папке автозагрузки текущего пользователя"""
        try:
            appdata = os.environ.get('APPDATA', '')
            if appdata:
                startup_path = Path(appdata) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
                if startup_path.exists():
                    return startup_path
        except Exception:
            pass
        
        userprofile = os.environ.get('USERPROFILE', '')
        if userprofile:
            return Path(userprofile) / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
        
        return Path()
    
    def _get_registry_key(self, hkey: int, subkey: str, access: int = winreg.KEY_READ) -> Optional[winreg.HKEYType]:
        """Безопасное открытие ключа реестра"""
        try:
            return winreg.OpenKey(hkey, subkey, 0, access)
        except WindowsError:
            return None
    
    def _get_registry_value(self, hkey: int, subkey: str, name: str) -> Tuple[Optional[str], Optional[int]]:
        """Получает значение из реестра"""
        try:
            key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ)
            try:
                value, reg_type = winreg.QueryValueEx(key, name)
                return value, reg_type
            except FileNotFoundError:
                return None, None
            finally:
                winreg.CloseKey(key)
        except WindowsError:
            return None, None
    
    def _set_registry_value(self, hkey: int, subkey: str, name: str, value: str) -> bool:
        """Устанавливает значение в реестре"""
        try:
            key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
                return True
            except Exception:
                return False
            finally:
                winreg.CloseKey(key)
        except WindowsError:
            try:
                key = winreg.CreateKey(hkey, subkey)
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
                winreg.CloseKey(key)
                return True
            except Exception:
                return False
    
    def _delete_registry_value(self, hkey: int, subkey: str, name: str) -> bool:
        """Удаляет значение из реестра"""
        try:
            key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, name)
                return True
            except FileNotFoundError:
                return True
            except Exception:
                return False
            finally:
                winreg.CloseKey(key)
        except WindowsError:
            return False
    
    def _normalize_path(self, path: str) -> str:
        """Нормализует путь, удаляя кавычки и лишние пробелы"""
        if not path:
            return ""
        path = path.strip().strip('"')
        return path
    
    def _notify_system_changes(self):
        """Уведомляет систему об изменениях в автозагрузке"""
        try:
            ctypes.windll.user32.SendMessageTimeoutW(
                ctypes.c_void_p(0xFFFF),
                0x001A,
                0,
                "Environment",
                0x0002,
                5000,
                ctypes.byref(ctypes.c_ulong())
            )
            
            ctypes.windll.shell32.SHChangeNotify(
                0x08000000,
                0x0000,
                None,
                None
            )
        except Exception:
            pass
    
    def get_startup_entries(self) -> List[StartupEntry]:
        """
        Получает список всех записей автозагрузки с РЕАЛЬНЫМ состоянием
        
        Returns:
            List[StartupEntry]: Список записей автозагрузки
        """
        entries = []
        seen = set()
        
        # 1. Записи из реестра HKCU\Run
        key = self._get_registry_key(HKEY_CURRENT_USER, REG_PATH_RUN)
        if key:
            try:
                i = 0
                while True:
                    try:
                        name = winreg.EnumValue(key, i)[0]
                        path = winreg.EnumValue(key, i)[1]
                        
                        # КРИТИЧНО: проверяем, что путь существует и файл доступен
                        is_enabled = False
                        if path and path.strip():
                            # Проверяем, что путь ведет к существующему файлу
                            normalized_path = self._normalize_path(path)
                            if normalized_path and os.path.exists(normalized_path):
                                is_enabled = True
                            # Если это не файл, но путь не пустой - считаем включенным
                            elif path.strip():
                                is_enabled = True
                        
                        if name and name not in seen:
                            entries.append(StartupEntry(
                                name=name,
                                path=path if path else "",
                                source="HKCU\\Run",
                                enabled=is_enabled
                            ))
                            seen.add(name)
                        i += 1
                    except WindowsError:
                        break
            finally:
                winreg.CloseKey(key)
        
        # 2. Записи из реестра HKLM\Run
        key = self._get_registry_key(HKEY_LOCAL_MACHINE, REG_PATH_RUN)
        if key:
            try:
                i = 0
                while True:
                    try:
                        name = winreg.EnumValue(key, i)[0]
                        path = winreg.EnumValue(key, i)[1]
                        
                        is_enabled = False
                        if path and path.strip():
                            normalized_path = self._normalize_path(path)
                            if normalized_path and os.path.exists(normalized_path):
                                is_enabled = True
                            elif path.strip():
                                is_enabled = True
                        
                        if name and name not in seen:
                            entries.append(StartupEntry(
                                name=name,
                                path=path if path else "",
                                source="HKLM\\Run",
                                enabled=is_enabled
                            ))
                            seen.add(name)
                        i += 1
                    except WindowsError:
                        break
            finally:
                winreg.CloseKey(key)
        
        # 3. Записи из реестра HKLM\Run (32-bit)
        key = self._get_registry_key(HKEY_LOCAL_MACHINE, REG_PATH_RUN_32)
        if key:
            try:
                i = 0
                while True:
                    try:
                        name = winreg.EnumValue(key, i)[0]
                        path = winreg.EnumValue(key, i)[1]
                        
                        is_enabled = False
                        if path and path.strip():
                            normalized_path = self._normalize_path(path)
                            if normalized_path and os.path.exists(normalized_path):
                                is_enabled = True
                            elif path.strip():
                                is_enabled = True
                        
                        if name and name not in seen:
                            entries.append(StartupEntry(
                                name=name,
                                path=path if path else "",
                                source="HKLM\\Run (32-bit)",
                                enabled=is_enabled
                            ))
                            seen.add(name)
                        i += 1
                    except WindowsError:
                        break
            finally:
                winreg.CloseKey(key)
        
        # 4. Ярлыки из папки автозагрузки (всегда включены)
        if self._startup_folder and self._startup_folder.exists():
            for lnk in self._startup_folder.glob("*.lnk"):
                name = lnk.stem
                if name not in seen:
                    entries.append(StartupEntry(
                        name=name,
                        path=str(lnk),
                        source="Startup Folder",
                        enabled=True  # Ярлыки в папке всегда включены
                    ))
                    seen.add(name)
        
        return entries
    
    def enable_startup(self, app_name: str) -> bool:
        """
        Включает автозагрузку для приложения.
        
        Args:
            app_name: Имя приложения (без расширения .exe)
            
        Returns:
            bool: True если успешно, False в противном случае
        """
        # Проверяем, есть ли уже запись
        entries = self.get_startup_entries()
        for entry in entries:
            if entry.name.lower() == app_name.lower():
                if entry.enabled:
                    return True
                # Если запись отключена, удаляем её и создадим заново
                self.disable_startup(app_name)
                break
        
        # Ищем исполняемый файл
        exe_path = self._find_executable(app_name)
        if not exe_path:
            return False
        
        # Добавляем запись в HKCU\Run
        success = self._set_registry_value(
            HKEY_CURRENT_USER,
            REG_PATH_RUN,
            app_name,
            f'"{exe_path}"'
        )
        
        if success:
            self._notify_system_changes()
        
        return success
    
    def disable_startup(self, app_name: str) -> bool:
        """
        Отключает автозагрузку для приложения.
        Удаляет запись из реестра.
        
        Args:
            app_name: Имя приложения
            
        Returns:
            bool: True если успешно, False в противном случае
        """
        found = False
        
        # Проверяем и удаляем из HKCU\Run
        value, _ = self._get_registry_value(HKEY_CURRENT_USER, REG_PATH_RUN, app_name)
        if value is not None:
            if self._delete_registry_value(HKEY_CURRENT_USER, REG_PATH_RUN, app_name):
                found = True
        
        # Проверяем и удаляем из HKLM\Run
        value, _ = self._get_registry_value(HKEY_LOCAL_MACHINE, REG_PATH_RUN, app_name)
        if value is not None:
            if self._delete_registry_value(HKEY_LOCAL_MACHINE, REG_PATH_RUN, app_name):
                found = True
        
        # Проверяем и удаляем из HKLM\Run (32-bit)
        value, _ = self._get_registry_value(HKEY_LOCAL_MACHINE, REG_PATH_RUN_32, app_name)
        if value is not None:
            if self._delete_registry_value(HKEY_LOCAL_MACHINE, REG_PATH_RUN_32, app_name):
                found = True
        
        if found:
            self._notify_system_changes()
        
        return found
    
    def _find_executable(self, app_name: str) -> Optional[str]:
        """
        Ищет исполняемый файл приложения в системе
        
        Args:
            app_name: Имя приложения
            
        Returns:
            str: Путь к исполняемому файлу или None
        """
        if not app_name.endswith('.exe'):
            search_names = [app_name + '.exe']
        else:
            search_names = [app_name]
        
        standard_paths = [
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            os.environ.get('ProgramFiles', r'C:\Program Files'),
            os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
            os.environ.get('LOCALAPPDATA', ''),
            os.environ.get('APPDATA', ''),
        ]
        
        path_env = os.environ.get('PATH', '').split(os.pathsep)
        standard_paths.extend(path_env)
        
        for base_path in standard_paths:
            if not base_path:
                continue
            base = Path(base_path)
            for name in search_names:
                direct = base / name
                if direct.exists():
                    return str(direct)
                
                for subdir in [base / name.replace('.exe', ''), base / name.replace('.exe', '').lower()]:
                    if subdir.exists() and subdir.is_dir():
                        exe = subdir / name
                        if exe.exists():
                            return str(exe)
        
        try:
            for name in search_names:
                result = subprocess.run(
                    ['where', name],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    paths = result.stdout.strip().split('\n')
                    for p in paths:
                        if p and os.path.exists(p):
                            return p
        except:
            pass
        
        return None
    
    def toggle_startup(self, app_name: str) -> bool:
        """
        Переключает состояние автозагрузки приложения
        
        Args:
            app_name: Имя приложения
            
        Returns:
            bool: True если включено после переключения, False если выключено
        """
        entries = self.get_startup_entries()
        is_enabled = any(e.name.lower() == app_name.lower() and e.enabled for e in entries)
        
        if is_enabled:
            self.disable_startup(app_name)
            return False
        else:
            return self.enable_startup(app_name)
    
    def is_startup_enabled(self, app_name: str) -> bool:
        """
        Проверяет, включена ли автозагрузка для приложения
        
        Args:
            app_name: Имя приложения
            
        Returns:
            bool: True если включена, False в противном случае
        """
        entries = self.get_startup_entries()
        return any(e.name.lower() == app_name.lower() and e.enabled for e in entries)
    
    def get_startup_path(self, app_name: str) -> Optional[str]:
        """
        Получает путь к исполняемому файлу, используемому в автозагрузке
        
        Args:
            app_name: Имя приложения
            
        Returns:
            str: Путь к исполняемому файлу или None
        """
        entries = self.get_startup_entries()
        for entry in entries:
            if entry.name.lower() == app_name.lower():
                return self._normalize_path(entry.path)
        return None
    
    def get_common_app_names(self) -> Dict[str, str]:
        """Возвращает словарь распространённых приложений"""
        return {
            'rtkaudservice64': 'RtkAudService64',
            'securityhealthsystray': 'SecurityHealthSystray',
            'xbox': 'Xbox',
            'torrent': 'Torrent Client',
            'terminal': 'Терминал',
            'yandexmusic': 'Яндекс.Музыка',
            'canonquickmenu': 'Canon Quick Menu',
            'onedrive': 'OneDrive',
            'msedge': 'msedge',
            'browser': 'browser',
            'utweb': 'Utweb'
        }
    
    def auto_manage(self, app_names: List[str], enable: bool = True) -> Dict[str, bool]:
        """Массовое управление автозагрузкой"""
        results = {}
        common_names = self.get_common_app_names()
        
        for name in app_names:
            search_name = name
            if name.lower() in common_names:
                search_name = common_names[name.lower()]
            
            if enable:
                results[name] = self.enable_startup(search_name)
            else:
                results[name] = self.disable_startup(search_name)
        
        return results


if __name__ == "__main__":
    manager = StartupManager()
    
    print("\n=== ВСЕ ЗАПИСИ АВТОЗАГРУЗКИ ===")
    entries = manager.get_startup_entries()
    for entry in entries:
        print(f"{entry.name}: {'✅ ВКЛЮЧЕНА' if entry.enabled else '❌ ОТКЛЮЧЕНА'} - {entry.source}")
        print(f"  Путь: {entry.path}")
        print()
    
    print(f"\nПапка автозагрузки: {manager._startup_folder}")