import shutil
import winreg
import subprocess
import os
import time

class TweakerTools:
    """Класс с инструментами оптимизации Windows"""

    @staticmethod
    def run_cmd(cmd):
        """Выполнить командную строку и вернуть результат"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                check=True,
                encoding='cp866'
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"!Ошибка: {e}"

    @staticmethod
    def clear_temp():
        """Очистить временные файлы Windows"""
        try:
            temp_dirs = [
                os.environ.get('TEMP'),
                os.environ.get('TMP'),
                r"C:\Windows\Temp",
                r"C:\Windows\SoftwareDistribution\Download",
                r"C:\Windows\Prefetch"
            ]

            deleted = 0
            for temp_dir in temp_dirs:
                if temp_dir and os.path.exists(temp_dir):
                    for item in os.listdir(temp_dir):
                        item_path = os.path.join(temp_dir, item)
                        try:
                            if os.path.isfile(item_path):
                                os.remove(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            deleted += 1
                        except:
                            pass

            return deleted, None
        except Exception as e:
            return 0, str(e)

    @staticmethod
    def disable_telemetry_services():
        """Отключить службы телеметрии"""
        services = [
            "DiagTrack",
            "dmwappushservice"
        ]

        disabled = 0
        errors = []
        for service in services:
            cmd = f'sc config "{service}" start= disabled'
            result = TweakerTools.run_cmd(cmd)
            if "успешно" in result.lower() or "success" in result.lower():
                disabled += 1
            else:
                errors.append(service)

        return disabled, errors

    @staticmethod
    def flush_dns():
        """Очистить DNS-кэш"""
        cmd = "ipconfig /flushdns"
        result = TweakerTools.run_cmd(cmd)
        if "успешно" in result.lower() or "successful" in result.lower():
            return True, None
        else:
            return False, result

    @staticmethod
    def fix_updates():
        """Исправить ошибки обновлений Windows"""
        try:
            # Останавливаем службы
            stop_cmds = ["net stop wuauserv", "net stop cryptSvc", "net stop bits", "net stop msiserver"]
            for cmd in stop_cmds:
                TweakerTools.run_cmd(cmd)

            # Очищаем временные файлы обновлений
            TweakerTools.clear_temp()

            # Запускаем службы
            start_cmds = ["net start wuauserv", "net start cryptSvc", "net start bits", "net start msiserver"]
            for cmd in start_cmds:
                TweakerTools.run_cmd(cmd)

            # Запускаем поиск обновлений
            TweakerTools.run_cmd("wuauclt /detectnow")
            TweakerTools.run_cmd("UsoClient ScanInstallWait")

            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def is_indexing_enabled():
        """Проверить включена ли индексация"""
        try:
            cmd = 'sc query "wsearch"'
            result = TweakerTools.run_cmd(cmd)
            return '4  RUNNING' in result
        except:
            return False

    @staticmethod
    def disable_indexing():
        """Отключить индексацию"""
        cmd = 'sc config "wsearch" start= disabled'
        TweakerTools.run_cmd(cmd)

    @staticmethod
    def enable_indexing():
        """Включить индексацию"""
        cmd = 'sc config "wsearch" start= delayed-auto && sc start "wsearch"'
        TweakerTools.run_cmd(cmd)

    @staticmethod
    def get_disabled_folder_path(startup_path):
        """Получить путь к папке с отключенными программами"""
        return os.path.join(os.path.dirname(startup_path), "Disabled_Startup")

    @staticmethod
    def get_startup_folder_programs():
        """Получить программы из папки Startup"""
        startup_programs = []

        startup_paths = [
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'),
            os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'Microsoft', 'Windows', 'Start Menu',
                         'Programs', 'Startup'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Roaming', 'Microsoft', 'Windows', 'Start Menu',
                         'Programs', 'Startup')
        ]

        startup_paths = list(dict.fromkeys(startup_paths))

        for startup_path in startup_paths:
            if os.path.exists(startup_path):
                try:
                    for item in os.listdir(startup_path):
                        item_path = os.path.join(startup_path, item)
                        if os.path.isfile(item_path) and item.lower().endswith(
                                ('.lnk', '.exe', '.bat', '.cmd', '.vbs', '.ps1')):
                            disabled_folder = TweakerTools.get_disabled_folder_path(startup_path)
                            disabled_path = os.path.join(disabled_folder, item)

                            startup_programs.append({
                                "type": "folder",
                                "display_name": os.path.splitext(item)[0],
                                "filename": item,
                                "full_path": item_path,
                                "startup_path": startup_path,
                                "disabled_path": disabled_path,
                                "is_disabled": False
                            })
                except Exception:
                    pass

        for startup_path in startup_paths:
            disabled_folder = TweakerTools.get_disabled_folder_path(startup_path)
            if os.path.exists(disabled_folder):
                try:
                    for item in os.listdir(disabled_folder):
                        item_path = os.path.join(disabled_folder, item)
                        if os.path.isfile(item_path) and item.lower().endswith(
                                ('.lnk', '.exe', '.bat', '.cmd', '.vbs', '.ps1')):
                            existing = any(
                                p["filename"] == item and p["startup_path"] == startup_path for p in startup_programs)
                            if not existing:
                                startup_programs.append({
                                    "type": "folder",
                                    "display_name": os.path.splitext(item)[0],
                                    "filename": item,
                                    "full_path": os.path.join(startup_path, item),
                                    "startup_path": startup_path,
                                    "disabled_path": item_path,
                                    "is_disabled": True
                                })
                except Exception:
                    pass

        return startup_programs

    @staticmethod
    def get_startup_registry_programs():
        """Получить программы из реестра"""
        startup_programs = []

        registry_paths = [
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run")
        ]

        for hive, reg_path in registry_paths:
            try:
                key = winreg.OpenKey(hive, reg_path, 0, winreg.KEY_READ)
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        is_disabled = name.startswith("Disabled_")
                        original_name = name[9:] if is_disabled else name

                        startup_programs.append({
                            "type": "registry",
                            "display_name": original_name,
                            "original_name": name,
                            "path": value,
                            "reg_hive": hive,
                            "reg_path": reg_path,
                            "is_disabled": is_disabled
                        })
                        i += 1
                    except WindowsError:
                        break
                winreg.CloseKey(key)
            except WindowsError:
                pass

        return startup_programs

    @staticmethod
    def get_all_startup_programs():
        """Получить все программы из автозагрузки"""
        all_programs = TweakerTools.get_startup_registry_programs()
        all_programs.extend(TweakerTools.get_startup_folder_programs())
        return all_programs

    @staticmethod
    def disable_registry_program(program):
        """Отключить программу из реестра"""
        try:
            key = winreg.OpenKey(program["reg_hive"], program["reg_path"], 0, winreg.KEY_SET_VALUE)
            if not program["original_name"].startswith("Disabled_"):
                winreg.SetValueEx(key, f"Disabled_{program['original_name']}", 0, winreg.REG_SZ, program["path"])
                winreg.DeleteValue(key, program["original_name"])
            winreg.CloseKey(key)
            return True
        except:
            return False

    @staticmethod
    def enable_registry_program(program):
        """Включить программу в реестре"""
        try:
            key = winreg.OpenKey(program["reg_hive"], program["reg_path"], 0, winreg.KEY_SET_VALUE)
            if program["original_name"].startswith("Disabled_"):
                original_name = program["original_name"][9:]
                winreg.SetValueEx(key, original_name, 0, winreg.REG_SZ, program["path"])
                winreg.DeleteValue(key, program["original_name"])
            winreg.CloseKey(key)
            return True
        except:
            return False

    @staticmethod
    def disable_folder_program(program):
        """Отключить программу из папки Startup"""
        try:
            disabled_folder = TweakerTools.get_disabled_folder_path(program["startup_path"])
            if not os.path.exists(disabled_folder):
                os.makedirs(disabled_folder)
            if os.path.exists(program["full_path"]):
                shutil.move(program["full_path"], program["disabled_path"])
                return True
            return False
        except:
            return False

    @staticmethod
    def enable_folder_program(program):
        """Включить программу в папку Startup"""
        try:
            if os.path.exists(program["disabled_path"]):
                if not os.path.exists(program["startup_path"]):
                    os.makedirs(program["startup_path"])
                shutil.move(program["disabled_path"], program["full_path"])
                return True
            return False
        except:
            return False
    
    @staticmethod
    def remove_watermark():
        """Удалить водяной знак сборки Windows (оценка/тестовая версия)"""
        try:
            # Проверяем, есть ли водяной знак
            commands = [
                # Удаляем параметры водяного знака из реестра
                'reg delete "HKEY_CURRENT_USER\\Control Panel\\Desktop" /v "PaintDesktopVersion" /f 2>nul',
                # Сбрасываем обои через PowerShell (принудительное обновление)
                'powershell -Command "& { $code = @\' [DllImport(\"user32.dll\")] public static extern int SendMessage(int hWnd, int Msg, int wParam, int lParam); \'@; Add-Type -Name Window -MemberDefinition $code; [Window]::SendMessage(0xFFFF, 0x001A, 0, 0) }" 2>nul'
            ]
            
            errors = []
            success_count = 0
            
            for cmd in commands:
                try:
                    result = TweakerTools.run_cmd(cmd)
                    # Не выводим ошибки, так как некоторые ключи могут отсутствовать
                    success_count += 1
                except Exception:
                    # Некоторые команды могут завершаться с ошибкой, но это нормально
                    pass
            
            # Перезапускаем проводник для применения изменений
            try:
                TweakerTools.restart_explorer()
            except:
                pass
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def restart_explorer():
        """Перезапустить проводник Windows"""
        try:
            # Останавливаем explorer.exe
            subprocess.run('taskkill /f /im explorer.exe', shell=True, capture_output=True, text=True)
            time.sleep(1)  # Небольшая пауза
            # Запускаем explorer.exe заново
            subprocess.run('start explorer.exe', shell=True, capture_output=True, text=True)
            return True
        except Exception as e:
            return False
