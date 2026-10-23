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

            foreach (var name in key.GetValueNames())
            {
                if (string.IsNullOrEmpty(name) || !seen.Add(name)) continue;
                var path = key.GetValue(name)?.ToString() ?? string.Empty;

                result.Add(new StartupEntry
                {
                    Name = name,
                    Path = path,
                    Source = source,
                    Enabled = true, // Если ключ есть в Run - значит он включен
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
            // 1. Включаем в системе
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
            }

            // 2. Удаляем из бэкапа (запись теперь активна)
            RemoveFromBackup(name, source);
            return true;
        }
        catch { return false; }
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