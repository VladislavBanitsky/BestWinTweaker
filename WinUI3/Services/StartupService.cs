using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Microsoft.Win32;
using Microsoft.Win32.TaskScheduler;
using BestWinTweaker.Models;

namespace BestWinTweaker.Services;

public class StartupService
{
    private const string RunKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string RunKey32 = @"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run";
    private const string ApprovedKey = @"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run";
    private const string ApprovedKey32 = @"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32";

    // --- Чтение ---

    public List<StartupEntry> GetStartupEntries()
    {
        var result = new List<StartupEntry>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        ReadRegistryBranch(Registry.CurrentUser, RunKey, ApprovedKey, "HKCU\\Run", result, seen);
        ReadRegistryBranch(Registry.LocalMachine, RunKey, ApprovedKey, "HKLM\\Run", result, seen);
        ReadRegistryBranch(Registry.LocalMachine, RunKey32, ApprovedKey32, "HKLM\\Run (32-bit)", result, seen);

        ReadStartupFolder(result, seen);
        ReadScheduledTasks(result, seen);

        return result.OrderBy(e => e.Name, StringComparer.OrdinalIgnoreCase).ToList();
    }

    private void ReadRegistryBranch(RegistryKey hive, string runKeyPath, string approvedKeyPath, string source, List<StartupEntry> result, HashSet<string> seen)
    {
        try
        {
            using var runKey = hive.OpenSubKey(runKeyPath);
            if (runKey == null) return;

            // Получаем флаги отключения из StartupApproved
            var disabledInApproved = GetDisabledNames(hive, approvedKeyPath);

            foreach (var name in runKey.GetValueNames())
            {
                if (string.IsNullOrEmpty(name) || !seen.Add(name)) continue;

                var path = runKey.GetValue(name)?.ToString() ?? string.Empty;

                // Программа включена, если её нет в списке отключенных
                bool isEnabled = !disabledInApproved.Contains(name);

                // Дополнительная проверка по имени exe (для Discord/Яндекс)
                if (isEnabled)
                {
                    var exeName = GetExeName(path);
                    if (!string.IsNullOrEmpty(exeName) && disabledInApproved.Contains(exeName))
                        isEnabled = false;
                }

                result.Add(new StartupEntry
                {
                    Name = name,
                    Path = path,
                    Source = source,
                    Enabled = isEnabled
                });
            }
        }
        catch { }
    }

    private HashSet<string> GetDisabledNames(RegistryKey hive, string approvedKeyPath)
    {
        var disabled = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        try
        {
            using var key = hive.OpenSubKey(approvedKeyPath);
            if (key == null) return disabled;

            foreach (var name in key.GetValueNames())
            {
                if (key.GetValue(name) is byte[] bytes && bytes.Length > 0)
                {
                    // 0x03, 0x07 (и другие нечетные) = отключено. 0x02, 0x06 = включено.
                    // Если первый байт не 02 и не 06, считаем отключенным.
                    if (bytes[0] != 0x02 && bytes[0] != 0x06 && bytes[0] != 0x00)
                        disabled.Add(name);
                }
            }
        }
        catch { }
        return disabled;
    }

    private void ReadStartupFolder(List<StartupEntry> result, HashSet<string> seen)
    {
        var folder = Environment.GetFolderPath(Environment.SpecialFolder.Startup);
        if (!Directory.Exists(folder)) return;

        foreach (var file in Directory.GetFiles(folder, "*.lnk"))
        {
            var name = Path.GetFileNameWithoutExtension(file);
            if (!seen.Add(name)) continue;

            result.Add(new StartupEntry { Name = name, Path = file, Source = "Startup Folder", Enabled = true });
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

                var key = "Task:" + task.Path;
                if (!seen.Add(key)) continue;

                result.Add(new StartupEntry
                {
                    Name = task.Name,
                    Path = task.Path,
                    Source = "Планировщик",
                    Enabled = task.Enabled
                });
            }
        }
        catch { }
    }

    // --- Управление ---

    public bool Disable(string name, string source, string path)
    {
        try
        {
            if (source == "Планировщик")
            {
                using var ts = new TaskService();
                var task = ts.GetTask(path);
                if (task != null) { task.Enabled = false; return true; }
                return false;
            }

            if (source == "Startup Folder")
            {
                var folder = Environment.GetFolderPath(Environment.SpecialFolder.Startup);
                var src = Path.Combine(folder, name + ".lnk");
                var disabledDir = Path.Combine(Path.GetDirectoryName(folder)!, "Startup_Disabled");
                Directory.CreateDirectory(disabledDir);
                if (File.Exists(src)) File.Move(src, Path.Combine(disabledDir, name + ".lnk"), true);
                return true;
            }

            // Реестр: пишем флаг отключения в StartupApproved
            var hive = source.StartsWith("HKCU") ? Registry.CurrentUser : Registry.LocalMachine;
            var approvedPath = source.Contains("32-bit") ? ApprovedKey32 : ApprovedKey;

            using var approvedKey = hive.CreateSubKey(approvedPath, writable: true);

            // Флаг 03 00 00 00 = отключено
            byte[] disabledFlag = new byte[] { 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };

            approvedKey.SetValue(name, disabledFlag, RegistryValueKind.Binary);

            // Дополнительно пишем под именем exe (для Discord/Яндекс)
            var exeName = GetExeName(path);
            if (!string.IsNullOrEmpty(exeName) && exeName != name)
            {
                approvedKey.SetValue(exeName, disabledFlag, RegistryValueKind.Binary);
            }

            return true;
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[Disable] Ошибка: {ex.Message}");
            return false;
        }
    }

    public bool Enable(string name, string source, string path)
    {
        try
        {
            if (source == "Планировщик")
            {
                using var ts = new TaskService();
                var task = ts.GetTask(path);
                if (task != null) { task.Enabled = true; return true; }
                return false;
            }

            if (source == "Startup Folder")
            {
                var folder = Environment.GetFolderPath(Environment.SpecialFolder.Startup);
                var disabledDir = Path.Combine(Path.GetDirectoryName(folder)!, "Startup_Disabled");
                var src = Path.Combine(disabledDir, name + ".lnk");
                if (File.Exists(src)) File.Move(src, Path.Combine(folder, name + ".lnk"), true);
                return true;
            }

            // Реестр: удаляем флаг из StartupApproved (или пишем 02)
            var hive = source.StartsWith("HKCU") ? Registry.CurrentUser : Registry.LocalMachine;
            var approvedPath = source.Contains("32-bit") ? ApprovedKey32 : ApprovedKey;

            using var approvedKey = hive.OpenSubKey(approvedPath, writable: true);
            if (approvedKey == null) return true; // Если ключа нет — уже включено

            // Удаляем запись (Windows по умолчанию считает программу включенной)
            approvedKey.DeleteValue(name, throwOnMissingValue: false);

            var exeName = GetExeName(path);
            if (!string.IsNullOrEmpty(exeName) && exeName != name)
            {
                approvedKey.DeleteValue(exeName, throwOnMissingValue: false);
            }

            return true;
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[Enable] Ошибка: {ex.Message}");
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
}