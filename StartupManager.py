import winreg
import os
import ctypes
import subprocess
import csv
import io
from dataclasses import dataclass
from typing import List, Optional, Tuple

HKEY_CURRENT_USER = winreg.HKEY_CURRENT_USER
HKEY_LOCAL_MACHINE = winreg.HKEY_LOCAL_MACHINE

REG_PATH_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_PATH_RUN_32 = r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"

REG_PATH_APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
REG_PATH_APPROVED_32 = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32"

@dataclass
class StartupEntry:
    name: str
    path: str
    source: str  # 'HKCU\Run', 'HKLM\Run', 'HKLM\Run (32-bit)', 'Startup Folder'
    enabled: bool
    
    def __str__(self):
        status = "✅ Включено" if self.enabled else "❌ Отключено"
        return f"{self.name} ({self.source}) - {status}"

class StartupManager:
    def __init__(self):
        self._startup_folder = self._get_startup_folder_path()

    def _get_startup_folder_path(self) -> str:
        appdata = os.environ.get('APPDATA', '')
        if appdata:
            return os.path.join(appdata, 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        return ""

    def _get_approved_key(self, hive: int, is_32bit: bool, writable: bool = False) -> Optional[int]:
        """Открывает ключ StartupApproved."""
        path = REG_PATH_APPROVED_32 if is_32bit else REG_PATH_APPROVED
        access = winreg.KEY_READ | (winreg.KEY_SET_VALUE if writable else 0)
        try:
            return winreg.OpenKey(hive, path, 0, access)
        except FileNotFoundError:
            if writable:
                try:
                    return winreg.CreateKeyEx(hive, path, 0, access)
                except Exception:
                    return None
            return None

    def _get_disabled_names(self, hive: int, is_32bit: bool) -> set:
        """Возвращает множество имен, отключенных через StartupApproved."""
        disabled = set()
        key = self._get_approved_key(hive, is_32bit)
        if not key:
            return disabled
        
        try:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    # Если первый байт не 0x02 и не 0x06 (и не 0x00), значит отключено (обычно 0x03)
                    if isinstance(value, bytes) and len(value) > 0:
                        if value[0] not in (0x02, 0x06, 0x00):
                            disabled.add(name)
                    i += 1
                except OSError:
                    break
        finally:
            winreg.CloseKey(key)
        return disabled

    def get_startup_entries(self) -> List[StartupEntry]:
        entries = []
        seen = set()

        # 1. HKCU\Run
        self._read_registry_branch(HKEY_CURRENT_USER, REG_PATH_RUN, False, "HKCU\\Run", entries, seen)
        # 2. HKLM\Run
        self._read_registry_branch(HKEY_LOCAL_MACHINE, REG_PATH_RUN, False, "HKLM\\Run", entries, seen)
        # 3. HKLM\Run (32-bit)
        self._read_registry_branch(HKEY_LOCAL_MACHINE, REG_PATH_RUN_32, True, "HKLM\\Run (32-bit)", entries, seen)
        # 4. Папка Startup
        self._read_startup_folder(entries, seen)
        # 5. Планировщик задач
        self._read_scheduled_tasks(entries, seen)

        return sorted(entries, key=lambda x: x.name.lower())

    def _get_approved_states(self, hive: int, is_32bit: bool) -> dict:
        """Возвращает словарь {имя: is_enabled} для всех записей в StartupApproved."""
        states = {}
        key = self._get_approved_key(hive, is_32bit)
        if not key:
            return states
        
        try:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    if isinstance(value, bytes) and len(value) > 0:
                        # 0x02, 0x06, 0x00 = ВКЛЮЧЕНО. 0x03, 0x07 = ОТКЛЮЧЕНО.
                        # (0x01 тоже иногда встречается как отключенное)
                        is_disabled = value[0] in (0x03, 0x07, 0x01)
                        states[name] = not is_disabled  # True = включено, False = отключено
                    i += 1
                except OSError:
                    break
        finally:
            winreg.CloseKey(key)
        return states

    def _read_registry_branch(self, hive: int, run_path: str, is_32bit: bool, source: str, entries: list, seen: set):
        try:
            key = winreg.OpenKey(hive, run_path, 0, winreg.KEY_READ)
        except FileNotFoundError:
            return
        
        approved_states = self._get_approved_states(hive, is_32bit)

        try:
            i = 0
            while True:
                try:
                    name, path, _ = winreg.EnumValue(key, i)
                    if name and name not in seen:
                        seen.add(name)
                        
                        # ПО УМОЛЧАНИЮ СЧИТАЕМ ВКЛЮЧЕННОЙ (если нет записи в StartupApproved)
                        is_enabled = True
                        
                        # Проверяем статус по имени ключа
                        if name in approved_states:
                            is_enabled = approved_states[name]
                        
                        # Если по ключу не нашли, проверяем по имени exe
                        if name not in approved_states:
                            exe_name = self._get_exe_name(path)
                            if exe_name and exe_name in approved_states:
                                is_enabled = approved_states[exe_name]

                        entries.append(StartupEntry(
                            name=name,
                            path=path,
                            source=source,
                            enabled=is_enabled
                        ))
                    i += 1
                except OSError:
                    break
        finally:
            winreg.CloseKey(key)

    def _read_startup_folder(self, entries: list, seen: set):
        if not self._startup_folder or not os.path.exists(self._startup_folder):
            return
        for file in os.listdir(self._startup_folder):
            if file.endswith('.lnk'):
                name = os.path.splitext(file)[0]
                if name not in seen:
                    seen.add(name)
                    entries.append(StartupEntry(
                        name=name,
                        path=os.path.join(self._startup_folder, file),
                        source="Startup Folder",
                        enabled=True
                    ))

    def _get_exe_name(self, path: str) -> str:
        """Извлекает имя exe из пути (для проверки в StartupApproved)."""
        if not path:
            return ""
        clean_path = path.strip('"')
        if '" ' in clean_path:
            clean_path = clean_path.split('"')[1]
        elif ' ' in clean_path and '"' not in clean_path:
            clean_path = clean_path.split(' ')[0]
        return os.path.basename(clean_path)
    
    def _read_scheduled_tasks(self, entries: list, seen: set):
        """Читает задачи из Планировщика заданий."""
        try:           
            # Запускаем schtasks
            result = subprocess.run(
                ['schtasks', '/query', '/fo', 'CSV', '/v'],
                capture_output=True,
                text=True,
                encoding='cp866',
                errors='replace', # Не падаем на неизвестных символах
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode != 0:
                print(f"[SCHED] Ошибка schtasks: {result.stderr}")
                return

            output = result.stdout
            if not output:
                print("[SCHED] Пустой ответ")
                return

            # Парсим CSV
            reader = csv.reader(io.StringIO(output))
            headers = next(reader, None)
            if not headers:
                print("[SCHED] Нет заголовков")
                return

            # Ищем индексы колонок
            def find_idx(names):
                for name in names:
                    if name in headers:
                        return headers.index(name)
                return -1

            task_idx = find_idx(['Имя задачи', 'TaskName'])
            status_idx = find_idx(['Состояние', 'Status'])
            schedule_idx = find_idx(['Расписание', 'Schedule'])
            
            if task_idx == -1:
                print("[SCHED] Не найдена колонка 'Имя задачи'")
                return

            count = 0
            for row in reader:
                if len(row) <= task_idx:
                    continue

                task_name = row[task_idx]
                
                # Пропускаем повторяющиеся заголовки таблицы ---
                if task_name in ['Имя задачи', 'TaskName']:
                    continue
                
                # Пропускаем системные задачи
                if task_name.startswith('\\Microsoft\\'):
                    continue
                
                # Пропускаем пустые строки
                if not task_name.strip():
                    continue

                # Проверяем статус
                is_enabled = True
                if status_idx != -1 and len(row) > status_idx:
                    status = row[status_idx]
                    # Если статус "Отключено" или "Disabled", значит выключено
                    is_enabled = status not in ['Отключено', 'Disabled']

                key = f"Task:{task_name}"
                if key in seen:
                    continue
                seen.add(key)

                entries.append(StartupEntry(
                    name=task_name.split('\\')[-1],
                    path=task_name,
                    source="Планировщик",
                    enabled=is_enabled
                ))
                count += 1

        except Exception as e:
            print(f"[SCHED] Исключение: {e}")
            import traceback
            traceback.print_exc()
    
    # --- Управление ---

    def disable_startup(self, app_name: str, source: str, path: str) -> bool:
        if source == "Startup Folder":
            return self._disable_folder_entry(app_name)
        
        if source == "Планировщик":
            return self._toggle_task(path, enable=False)

        hive = HKEY_CURRENT_USER if source.startswith("HKCU") else HKEY_LOCAL_MACHINE
        is_32bit = "(32-bit)" in source

        try:
            key = self._get_approved_key(hive, is_32bit, writable=True)
            if not key:
                return False

            # Флаг 0x03 = отключено
            disabled_flag = bytes([0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            
            winreg.SetValueEx(key, app_name, 0, winreg.REG_BINARY, disabled_flag)
            
            # Дополнительно пишем под именем exe
            exe_name = self._get_exe_name(path)
            if exe_name and exe_name != app_name:
                winreg.SetValueEx(key, exe_name, 0, winreg.REG_BINARY, disabled_flag)

            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Ошибка отключения {app_name}: {e}")
            return False

    def enable_startup(self, app_name: str, source: str, path: str) -> bool:
        if source == "Startup Folder":
            return self._enable_folder_entry(app_name)
        
        if source == "Планировщик":
            return self._toggle_task(path, enable=True)

        hive = HKEY_CURRENT_USER if source.startswith("HKCU") else HKEY_LOCAL_MACHINE
        is_32bit = "(32-bit)" in source

        try:
            key = self._get_approved_key(hive, is_32bit, writable=True)
            if not key:
                return True # Если ключа нет, значит уже включено

            # Удаляем запись из StartupApproved (по умолчанию Windows считает программу включенной)
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass

            # Удаляем по имени exe
            exe_name = self._get_exe_name(path)
            if exe_name and exe_name != app_name:
                try:
                    winreg.DeleteValue(key, exe_name)
                except FileNotFoundError:
                    pass

            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Ошибка включения {app_name}: {e}")
            return False

    def _disable_folder_entry(self, name: str) -> bool:
        try:
            src = os.path.join(self._startup_folder, name + ".lnk")
            disabled_dir = os.path.join(os.path.dirname(self._startup_folder), "Startup_Disabled")
            os.makedirs(disabled_dir, exist_ok=True)
            if os.path.exists(src):
                os.replace(src, os.path.join(disabled_dir, name + ".lnk"))
                return True
        except Exception as e:
            print(f"Ошибка отключения папки {name}: {e}")
        return False

    def _enable_folder_entry(self, name: str) -> bool:
        try:
            disabled_dir = os.path.join(os.path.dirname(self._startup_folder), "Startup_Disabled")
            src = os.path.join(disabled_dir, name + ".lnk")
            if os.path.exists(src):
                os.replace(src, os.path.join(self._startup_folder, name + ".lnk"))
                return True
        except Exception as e:
            print(f"Ошибка включения папки {name}: {e}")
        return False
    
    def _toggle_task(self, task_path: str, enable: bool) -> bool:
        """Включает или отключает задачу Планировщика."""
        try:
            action = '/enable' if enable else '/disable'
            # Важно: путь задачи должен быть в кавычках
            result = subprocess.run(
                ['schtasks', '/change', '/tn', task_path, action],
                capture_output=True,
                text=True,
                encoding='cp866',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Ошибка изменения задачи {task_path}: {e}")
            return False