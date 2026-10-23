using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Microsoft.Win32;
using Microsoft.Win32.TaskScheduler;
using BestWinTweaker.Models;

namespace BestWinTweaker.Services;

public class StartupService
{
    private const string RunKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string RunKey32 = @"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run";
    private const string TaskPrefix = "Task: ";
    private readonly string _backupFile;

    public StartupService()
    {
        var backupDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            ".bwt", "backups");
        Directory.CreateDirectory(backupDir);
        _backupFile = Path.Combine(backupDir, "startup_backup.json");
    }

    public List<StartupEntry> GetStartupEntries()
    {
        var result = new List<StartupEntry>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        // 1. Читаем реестр (только те, что реально есть)
        ReadRegistryBranch(Registry.CurrentUser, RunKey, "HKCU\\Run", result, seen);
        ReadRegistryBranch(Registry.LocalMachine, RunKey, "HKLM\\Run", result, seen);
        ReadRegistryBranch(Registry.LocalMachine, RunKey32, "HKLM\\Run (32-bit)", result, seen);

        // 2. Читаем папку Startup
        ReadStartupFolder(result, seen);

        // 3. Читаем Планировщик
        ReadScheduledTasks(result, seen);

        // 4. Добавляем записи из бэкапа, которых нет в текущем списке
        var backup = LoadBackup();
        foreach (var b in backup)
        {
            var key = $"{b.Name}|{b.Source}";
            if (!seen.Contains(key) && !result.Any(r => r.Name == b.Name && r.Source == b.Source))
            {
                result.Add(new StartupEntry
                {
                    Name = b.Name,
                    Path = b.Path,
                    Source = b.Source,
                    Enabled = false, // Отключено (нет в реестре, но есть в бэкапе)
                    IsFromBackup = true
                });
            }
        }

        return result.OrderBy(e => e.Name, StringComparer.OrdinalIgnoreCase).ToList();
    }

    private void ReadRegistryBranch(RegistryKey hive, string subKey, string source, List<StartupEntry> result, HashSet<string> seen)
    {
        try
        {
            using var key = hive.OpenSubKey(subKey);
            if (key == null) return;

            // Получаем список отключенных программ для этой ветки
            var disabledInApproved = GetDisabledFromStartupApproved(hive, source);

            foreach (var name in key.GetValueNames())
            {
                if (string.IsNullOrEmpty(name) || !seen.Add(name)) continue;

                var path = key.GetValue(name)?.ToString() ?? string.Empty;

                // Программа считается выключенной, если её имя есть в списке отключенных StartupApproved
                // (или её exe-имя, что часто бывает с Discord/Яндексом)
                bool isEnabled = true;

                if (disabledInApproved.Contains(name))
                {
                    isEnabled = false;
                }
                else
                {
                    // Проверяем по имени exe (если путь указывает на Update.exe или browser.exe)
                    var exeName = GetExeName(path);
                    if (!string.IsNullOrEmpty(exeName) && disabledInApproved.Contains(exeName))
                    {
                        isEnabled = false;
                    }
                }

                result.Add(new StartupEntry
                {
                    Name = name,
                    Path = path,
                    Source = source,
                    Enabled = isEnabled, // Выставляем реальный статус
                    IsFromBackup = false
                });
            }
        }
        catch { }
    }

    private void ReadStartupFolder(List<StartupEntry> result, HashSet<string> seen)
    {
        var folder = Environment.GetFolderPath(Environment.SpecialFolder.Startup);
        if (Directory.Exists(folder))
        {
            foreach (var file in Directory.GetFiles(folder, "*.lnk"))
            {
                var name = Path.GetFileNameWithoutExtension(file);
                if (!seen.Add(name)) continue;
                result.Add(new StartupEntry { Name = name, Path = file, Source = "Startup Folder", Enabled = true });
            }
        }

        // Читаем отключенные ярлыки
        var disabledFolder = Path.Combine(Path.GetDirectoryName(folder)!, "Startup_Disabled");
        if (Directory.Exists(disabledFolder))
        {
            foreach (var file in Directory.GetFiles(disabledFolder, "*.lnk"))
            {
                var name = Path.GetFileNameWithoutExtension(file);
                if (!seen.Add(name)) continue;
                result.Add(new StartupEntry { Name = name, Path = file, Source = "Startup Folder", Enabled = false });
            }
        }
    }

    private void ReadScheduledTasks(List<StartupEntry> result, HashSet<string> seen)
    {
        try
        {
            using var ts = new TaskService();
            var allTasks = ts.RootFolder.GetTasks(new System.Text.RegularExpressions.Regex(".*"));

            foreach (var task in allTasks)
            {
                if (task.Path.StartsWith(@"\Microsoft\", StringComparison.OrdinalIgnoreCase)) continue;

                bool isStartup = task.Definition.Triggers.Any(t => t is LogonTrigger || t is BootTrigger);
                if (!isStartup) continue;

                var key = TaskPrefix + task.Path;
                if (!seen.Add(key)) continue;

                result.Add(new StartupEntry
                {
                    Name = task.Name,
                    Path = task.Path,
                    Source = "Планировщик",
                    Enabled = task.Enabled,
                    IsFromBackup = false
                });
            }
        }
        catch { }
    }

    public bool Disable(string name, string source, string path)
    {
        try
        {
            // 1. Отключаем в системе
            if (source == "Планировщик")
            {
                using var ts = new TaskService();
                var task = ts.GetTask(path);
                if (task != null) task.Enabled = false;
            }
            else if (source == "Startup Folder")
            {
                // Перемещаем в Disabled
                var folder = Environment.GetFolderPath(Environment.SpecialFolder.Startup);
                var src = Path.Combine(folder, name + ".lnk");
                var disabledDir = Path.Combine(Path.GetDirectoryName(folder)!, "Startup_Disabled");
                Directory.CreateDirectory(disabledDir);
                if (File.Exists(src)) File.Move(src, Path.Combine(disabledDir, name + ".lnk"), true);
            }
            else
            {
                // Реестр: удаляем ключ
                var hive = source.StartsWith("HKCU") ? Registry.CurrentUser : Registry.LocalMachine;
                var runKeyPath = source.Contains("32-bit") ? RunKey32 : RunKey;
                using var runKey = hive.OpenSubKey(runKeyPath, writable: true);
                if (runKey?.GetValue(name) != null) runKey.DeleteValue(name);
            }

            // 2. Сохраняем в бэкап
            AddToBackup(name, path, source);
            return true;
        }
        catch { return false; }
    }

    public bool Enable(string name, string source, string path)
    {
        try
        {
            // 1. Включаем в системе (реестр, планировщик или папка)
            if (source == "Планировщик")
            {
                using var ts = new TaskService();
                var task = ts.GetTask(path);
                if (task != null) task.Enabled = true;
            }
            else if (source == "Startup Folder")
            {
                var folder = Environment.GetFolderPath(Environment.SpecialFolder.Startup);
                var disabledDir = Path.Combine(Path.GetDirectoryName(folder)!, "Startup_Disabled");
                var src = Path.Combine(disabledDir, name + ".lnk");
                if (File.Exists(src)) File.Move(src, Path.Combine(folder, name + ".lnk"), true);
            }
            else
            {
                // Реестр: создаем ключ
                var hive = source.StartsWith("HKCU") ? Registry.CurrentUser : Registry.LocalMachine;
                var runKeyPath = source.Contains("32-bit") ? RunKey32 : RunKey;

                using var runKey = hive.CreateSubKey(runKeyPath, writable: true);
                if (!string.IsNullOrEmpty(path)) runKey.SetValue(name, path, RegistryValueKind.String);

                // Обновляем StartupApproved для реестра
                try
                {
                    // Путь к StartupApproved (Run или Run32 в зависимости от источника)
                    string approvedSubKey = source.Contains("32-bit")
                        ? @"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32"
                        : @"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run";

                    using var approvedKey = hive.CreateSubKey(approvedSubKey, writable: true);
                    if (approvedKey != null)
                    {
                        // Флаг 02 00 00 00 ... означает "Включено"
                        // Windows использует первые байты для статуса. 02 или 06 = включено. 03 или 07 = отключено
                        byte[] enabledFlag = new byte[] { 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };

                        // Записываем флаг под именем программы
                        approvedKey.SetValue(name, enabledFlag, RegistryValueKind.Binary);

                        // Дополнительно можно записать под именем exe, если оно отличается
                        var exeName = GetExeName(path);
                        if (!string.IsNullOrEmpty(exeName) && exeName != name)
                        {
                            approvedKey.SetValue(exeName, enabledFlag, RegistryValueKind.Binary);
                        }
                    }
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[Enable] Ошибка записи в StartupApproved: {ex.Message}");
                }
            }

            // 2. Удаляем из нашего JSON-бэкапа (запись теперь активна)
            RemoveFromBackup(name, source);
            return true;
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[Enable] Общая ошибка: {ex.Message}");
            return false;
        }
    }

    private string GetExeName(string path)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(path)) return string.Empty;
            var cleanPath = path.Trim('"');
            if (cleanPath.Contains("\" "))
                cleanPath = cleanPath.Split('"')[1];
            else if (!cleanPath.Contains("\"") && cleanPath.Contains(" "))
                cleanPath = cleanPath.Split(' ')[0];

            return Path.GetFileName(cleanPath);
        }
        catch { return string.Empty; }
    }

    private HashSet<string> GetDisabledFromStartupApproved(RegistryKey hive, string source)
    {
        var disabledNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        // Определяем путь к StartupApproved в зависимости от ветки (32-bit или обычная)
        string approvedSubKey = source.Contains("32-bit")
            ? @"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32"
            : @"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run";

        try
        {
            using var approvedKey = hive.OpenSubKey(approvedSubKey);
            if (approvedKey == null) return disabledNames;

            foreach (var name in approvedKey.GetValueNames())
            {
                if (approvedKey.GetValue(name) is byte[] bytes && bytes.Length >= 1)
                {
                    // Байт 0x02 или 0x06 = включено. Байт 0x03 или 0x07 = отключено.
                    // Если первый байт НЕ 02 и НЕ 06, значит программа отключена (обычно 03).
                    if (bytes[0] != 0x02 && bytes[0] != 0x06 && bytes[0] != 0x00)
                    {
                        disabledNames.Add(name);
                    }
                }
            }
        }
        catch { }

        return disabledNames;
    }

    private void SaveBackup(List<StartupBackupEntry> backup)
    {
        try
        {
            var json = JsonSerializer.Serialize(backup, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(_backupFile, json);
        }
        catch { }
    }
    private List<StartupBackupEntry> LoadBackup()
    {
        try
        {
            if (!File.Exists(_backupFile)) return new();
            var json = File.ReadAllText(_backupFile);
            return JsonSerializer.Deserialize<List<StartupBackupEntry>>(json) ?? new();
        }
        catch { return new(); }
    }

    private void AddToBackup(string name, string path, string source)
    {
        var backup = LoadBackup();
        // Удаляем старую запись, если она была
        backup.RemoveAll(b => b.Name == name && b.Source == source);
        backup.Add(new StartupBackupEntry { Name = name, Path = path, Source = source });
        SaveBackup(backup);
    }

    private void RemoveFromBackup(string name, string source)
    {
        var backup = LoadBackup();
        backup.RemoveAll(b => b.Name == name && b.Source == source);
        SaveBackup(backup);
    }
}