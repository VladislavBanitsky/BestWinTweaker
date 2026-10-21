using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Net.Http;
using System.Net.NetworkInformation;
using System.ServiceProcess;
using System.Text.Json;
using System.Threading.Tasks;

namespace BestWinTweaker.Services;

public class TweakerService
{
    // ---- Исправление обновлений ----
    public async Task<bool> FixUpdatesAsync()
    {
        try
        {
            // Останавливаем службы
            string[] stopCmds = {
                "net stop wuauserv", "net stop cryptSvc", "net stop bits", "net stop msiserver"
            };
            foreach (var cmd in stopCmds) RunSilent("cmd.exe", $"/c {cmd}");

            // Очищаем кэш обновлений
            ClearTemp();
            if (Directory.Exists(@"C:\Windows\SoftwareDistribution\Download"))
            {
                try { Directory.Delete(@"C:\Windows\SoftwareDistribution\Download", true); } catch { }
            }

            // Запускаем службы
            string[] startCmds = {
                "net start cryptSvc", "net start bits", "net start msiserver", "net start wuauserv"
            };
            foreach (var cmd in startCmds) RunSilent("cmd.exe", $"/c {cmd}");

            // Запускаем поиск обновлений
            RunSilent("cmd.exe", "/c wuauclt /detectnow");
            RunSilent("cmd.exe", "/c UsoClient ScanInstallWait");

            return true;
        }
        catch { return false; }
    }

    // ---- Индексация ----
    public bool IsIndexingEnabled()
    {
        var result = RunSilent("sc.exe", "query wsearch");
        return result.Output.Contains("RUNNING", StringComparison.OrdinalIgnoreCase);
    }

    public void DisableIndexing()
    {
        RunSilent("sc.exe", "config wsearch start= disabled");
        RunSilent("sc.exe", "stop wsearch");
    }

    public void EnableIndexing()
    {
        RunSilent("sc.exe", "config wsearch start= delayed-auto");
        RunSilent("sc.exe", "start wsearch");
    }

    // ---- Скачивание Windows (Fido) ----
    public async Task<bool> StartWindowsDownloadAsync()
    {
        try
        {
            // 1. Скачиваем Fido.ps1
            string url = "https://raw.githubusercontent.com/pbatard/Fido/master/Fido.ps1";
            string tempPath = Path.Combine(Path.GetTempPath(), "Fido.ps1");

            using var client = new HttpClient();
            var scriptContent = await client.GetStringAsync(url);
            await File.WriteAllTextAsync(tempPath, scriptContent, System.Text.Encoding.UTF8);

            // 2. Формируем команду PowerShell, которая:
            //    - Устанавливает кодировку консоли в UTF-8
            //    - Запускает Fido
            //    - Ждет нажатия Enter, чтобы окно не закрылось
            string command = $@"
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8;
            [Console]::InputEncoding = [System.Text.Encoding]::UTF8;
            $OutputEncoding = [System.Text.Encoding]::UTF8;
            & '{tempPath}';
            Write-Host '';
            Write-Host 'Нажмите Enter, чтобы закрыть...' -ForegroundColor Green;
            Read-Host
        ";

            // 3. Запускаем PowerShell с этой командой
            var psi = new ProcessStartInfo
            {
                FileName = "powershell.exe",
                Arguments = $"-NoProfile -ExecutionPolicy Bypass -Command \"{command}\"",
                UseShellExecute = true,
                CreateNoWindow = false
            };

            Process.Start(psi);
            return true;
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[Fido] Ошибка: {ex.Message}");
            return false;
        }
    }

    // ---- Обои Bing ----
    public async Task<bool> SetBingWallpaperAsync()
    {
        try
        {
            using var client = new HttpClient();
            // API Bing Wallpaper (возвращает JSON с URL картинки)
            string apiUrl = "https://bing.biturl.top/?resolution=UHD&mkt=ru-RU&index=0&format=json";
            var response = await client.GetStringAsync(apiUrl);
            using var doc = JsonDocument.Parse(response);
            string imageUrl = doc.RootElement.GetProperty("url").GetString();
            string copyright = doc.RootElement.GetProperty("copyright").GetString();

            if (string.IsNullOrEmpty(imageUrl)) return false;

            // Скачиваем картинку
            string tempPath = Path.Combine(Path.GetTempPath(), "bing_wallpaper.jpg");
            var imageBytes = await client.GetByteArrayAsync(imageUrl);
            await File.WriteAllBytesAsync(tempPath, imageBytes);

            // Устанавливаем как обои через Win32 API
            SystemParametersInfo(20, 0, tempPath, 3);
            return true;
        }
        catch { return false; }
    }

    [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Auto)]
    private static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);

    // ---- Удаление водяного знака ----
    public async Task<bool> RemoveWatermarkAsync()
    {
        try
        {
            // Скачиваем UWD (Universal Watermark Disabler)
            string zipUrl = "https://github.com/pr701/universal-watermark-disabler/releases/download/v1.0.0.6-2015/uwd.zip";
            string tempDir = Path.Combine(Path.GetTempPath(), "UWD_Temp");
            string zipPath = Path.Combine(Path.GetTempPath(), "uwd.zip");

            Directory.CreateDirectory(tempDir);

            using var client = new HttpClient();
            var zipBytes = await client.GetByteArrayAsync(zipUrl);
            await File.WriteAllBytesAsync(zipPath, zipBytes);

            // Распаковываем
            ZipFile.ExtractToDirectory(zipPath, tempDir, true);

            // Ищем exe
            var exeFiles = Directory.GetFiles(tempDir, "*.exe", SearchOption.AllDirectories);
            if (exeFiles.Length == 0) return false;

            // Запускаем
            var psi = new ProcessStartInfo
            {
                FileName = exeFiles[0],
                UseShellExecute = true,
                Verb = "runas" // Требуются права администратора
            };
            var p = Process.Start(psi);
            p?.WaitForExit();

            // Перезапускаем Explorer
            RunSilent("cmd.exe", "/c taskkill /f /im explorer.exe & start explorer.exe");

            // Очистка
            try { Directory.Delete(tempDir, true); File.Delete(zipPath); } catch { }

            return true;
        }
        catch { return false; }
    }

    // ---- Очистка временных файлов ----
    public (int Deleted, string? Error) ClearTemp()
    {
        var tempDirs = new[]
        {
            Path.GetTempPath(),
            @"C:\Windows\Temp",
            @"C:\Windows\SoftwareDistribution\Download",
            @"C:\Windows\Prefetch"
        };

        int deleted = 0;
        var errors = new List<string>();

        foreach (var dir in tempDirs)
        {
            if (!Directory.Exists(dir)) continue;
            try
            {
                foreach (var file in Directory.GetFiles(dir))
                {
                    try { File.Delete(file); deleted++; } catch { }
                }
                foreach (var subDir in Directory.GetDirectories(dir))
                {
                    try { Directory.Delete(subDir, true); deleted++; } catch { }
                }
            }
            catch (Exception ex) { errors.Add($"{dir}: {ex.Message}"); }
        }

        return (deleted, errors.Count > 0 ? string.Join("; ", errors) : null);
    }

    // ---- Отключение телеметрии ----
    public (int Disabled, string? Errors) DisableTelemetry()
    {
        var services = new[] { "DiagTrack", "dmwappushservice" };
        int disabled = 0;
        var errors = new List<string>();

        foreach (var name in services)
        {
            try
            {
                using var sc = new ServiceController(name);
                if (sc.Status != ServiceControllerStatus.Stopped)
                {
                    sc.Stop();
                    sc.WaitForStatus(ServiceControllerStatus.Stopped, TimeSpan.FromSeconds(10));
                }
                // Отключение автозапуска через sc.exe (аналог sc config)
                RunSilent("sc.exe", $"config \"{name}\" start= disabled");
                disabled++;
            }
            catch (Exception ex) { errors.Add($"{name}: {ex.Message}"); }
        }
        return (disabled, errors.Count > 0 ? string.Join("; ", errors) : null);
    }

    // ---- Очистка DNS ----
    public bool FlushDns(out string? error)
    {
        error = null;
        try
        {
            var result = RunSilent("ipconfig.exe", "/flushdns");
            return result.ExitCode == 0;
        }
        catch (Exception ex) { error = ex.Message; return false; }
    }

    // ---- Ping (нативный API вместо парсинга консоли) ----
    public async Task<(bool Success, string Result)> PingAsync(string host)
    {
        try
        {
            // 1. Пытаемся определить имя хоста по IP (если введен IP)
            string hostName = host;
            try
            {
                // Если введен IP-адрес, получаем его DNS-имя
                if (IPAddress.TryParse(host, out var ip))
                {
                    var hostEntry = Dns.GetHostEntry(ip);
                    if (!string.IsNullOrEmpty(hostEntry.HostName))
                        hostName = hostEntry.HostName;
                }
                else
                {
                    // Если введено имя, получаем его IP
                    var hostEntry = Dns.GetHostEntry(host);
                    if (hostEntry.AddressList.Length > 0)
                        hostName = $"{host} ({hostEntry.AddressList[0]})";
                }
            }
            catch { /* Если DNS не отвечает, оставляем как есть */ }

            // 2. Выполняем пинг
            using var ping = new Ping();
            var reply = await ping.SendPingAsync(host, 5000);

            if (reply.Status == IPStatus.Success)
            {
                return (true, $"Узел {hostName} доступен. Время: {reply.RoundtripTime} мс");
            }
            else
            {
                return (false, $"Узел {hostName} не доступен. Статус: {reply.Status}");
            }
        }
        catch (Exception ex)
        {
            return (false, $"Ошибка: {ex.Message}");
        }
    }

    // ---- Запуск внешнего процесса без окна ----
    public static (int ExitCode, string Output, string Error) RunSilent(string fileName, string arguments)
    {
        var psi = new ProcessStartInfo
        {
            FileName = fileName,
            Arguments = arguments,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };
        using var p = Process.Start(psi);
        if (p == null) return (-1, "", "Не удалось запустить процесс");

        var output = p.StandardOutput.ReadToEnd();
        var error = p.StandardError.ReadToEnd();
        p.WaitForExit(10000);
        return (p.ExitCode, output, error);
    }
}