import patch_subprocess  #  импортируем патч
import subprocess
import json
import re
import traceback

class UWPRemover:
    """Класс для безопасного удаления UWP-приложений"""
    
    def __init__(self, parent_window):
        self.parent = parent_window
        self.apps = []
        self.selected_apps = {}
        
    def get_removable_apps(self):
        """Получить список удаляемых приложений (выполняется в потоке)"""
        try:
            cmd = ['powershell', '-Command', 
                   'Get-AppxPackage | Where-Object { $_.IsFramework -eq $false -and $_.SignatureKind -ne "System" } | Select-Object Name, PackageFullName, Publisher, Version, InstallLocation | ConvertTo-Json -Compress']
            
            # Определяем кодировку в зависимости от версии Windows
            # Для Windows 7 и более старых версий используем cp866
            # Для новых версий - utf-8
            try:
                import sys
                win_ver = sys.getwindowsversion()
                if win_ver.major < 10:  # Windows 7, 8, 8.1
                    encoding = 'cp866'
                else:
                    encoding = 'utf-8'
            except:
                encoding = 'utf-8'
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding=encoding, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0 and result.stdout and result.stdout != 'null':
                json_str = result.stdout.strip()
                if json_str.startswith('['):
                    apps_data = json.loads(json_str)
                elif json_str.startswith('{'):
                    apps_data = [json.loads(json_str)]
                else:
                    apps_data = []
                
                # Список приложений, которые НЕЛЬЗЯ удалять
                protected = [
                    'Microsoft.WindowsStore',
                    'Microsoft.WindowsCalculator', 
                    'Microsoft.WindowsCamera',
                    'Microsoft.Windows.Photos',
                    'Microsoft.WindowsSoundRecorder',
                    'Microsoft.MSPaint',
                    'Microsoft.Windows.Explorer',
                    'Microsoft.Windows.ShellExperienceHost',
                    'Microsoft.Windows.ContentDeliveryManager',
                    'Microsoft.Windows.PeopleExperienceHost',
                    'Microsoft.Windows.SecHealthUI',
                    'Microsoft.VCLibs',
                    'Microsoft.NET.Native',
                    'Microsoft.UI.Xaml',
                    'Microsoft.Services.Store.Engagement',
                ]
                
                # Список безопасных для удаления
                safe = [
                    'Microsoft.BingWeather',
                    'Microsoft.BingNews', 
                    'Microsoft.BingSports',
                    'Microsoft.BingFinance',
                    'Microsoft.WindowsAlarms',
                    'Microsoft.Windows.Maps',
                    'Microsoft.Xbox.TCUI',
                    'Microsoft.XboxApp',
                    'Microsoft.XboxGameOverlay',
                    'Microsoft.YourPhone',
                    'Microsoft.ZuneMusic',
                    'Microsoft.ZuneVideo',
                    'Microsoft.Microsoft3DViewer',
                    'Microsoft.MicrosoftOfficeHub',
                    'Microsoft.MicrosoftSolitaireCollection',
                    'Microsoft.MixedReality.Portal',
                    'Microsoft.Office.OneNote',
                    'Microsoft.SkypeApp',
                    'Microsoft.WindowsFeedbackHub',
                    'SpotifyAB.SpotifyMusic',
                    'Netflix',
                    'Facebook',
                    'Instagram',
                    'TikTok',
                    'WhatsApp',
                    'Telegram',
                    'Zoom',
                ]
                
                apps = []
                for app in apps_data:
                    if not isinstance(app, dict):
                        continue
                    
                    package_name = app.get('PackageFullName', '')
                    name = app.get('Name', '')
                    
                    if not package_name:
                        continue
                    
                    # Проверяем защиту
                    is_protected = any(p in package_name for p in protected)
                    if is_protected:
                        continue
                    
                    # Проверяем безопасность
                    is_safe = any(s in package_name for s in safe)
                    
                    # Очищаем имя
                    clean_name = name
                    if name and re.match(r'^[a-f0-9\-]+$', name, re.I):
                        parts = package_name.split('_')
                        if parts:
                            clean_name = parts[0].replace('Microsoft.', '')
                    
                    if clean_name and len(clean_name) > 2:
                        apps.append({
                            'name': clean_name,
                            'package_name': package_name,
                            'publisher': app.get('Publisher', ''),
                            'version': app.get('Version', ''),
                            'is_safe': is_safe,
                            'install_location': app.get('InstallLocation', '')
                        })
                
                return sorted(apps, key=lambda x: (not x['is_safe'], x['name']))
            
            return []
        except Exception as e:
            print(f"Ошибка получения приложений: {e}")
            return []
    
    def remove_app(self, package_name, callback=None):
        """Удалить приложение"""
        try:
            # Запускаем PowerShell с правильными правами
            cmd = f'powershell -Command "Get-AppxPackage | Where-Object {{ $_.PackageFullName -eq \'{package_name}\' }} | Remove-AppxPackage"'
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            success = result.returncode == 0
            
            if callback:
                self.parent.after(0, lambda: callback(success, package_name))
            
            return success
        except Exception as e:
            if callback:
                self.parent.after(0, lambda: callback(False, package_name))
            return False