using BestWinTweaker.Models;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;

namespace BestWinTweaker.Services;

public class UwpService
{
    // Список приложений, которые НЕЛЬЗЯ удалять (критично для системы)
    private static readonly string[] ProtectedApps = {
        "Microsoft.WindowsStore", "Microsoft.WindowsCalculator", "Microsoft.WindowsCamera",
        "Microsoft.Windows.Photos", "Microsoft.WindowsSoundRecorder", "Microsoft.MSPaint",
        "Microsoft.Windows.Explorer", "Microsoft.Windows.ShellExperienceHost",
        "Microsoft.Windows.ContentDeliveryManager", "Microsoft.Windows.PeopleExperienceHost",
        "Microsoft.Windows.SecHealthUI", "Microsoft.VCLibs", "Microsoft.NET.Native",
        "Microsoft.UI.Xaml", "Microsoft.Services.Store.Engagement"
    };

    // Безопасные для удаления приложения (помечаются зеленой галочкой)
    private static readonly string[] SafeApps = {
        "Microsoft.BingWeather", "Microsoft.BingNews", "Microsoft.BingSports",
        "Microsoft.BingFinance", "Microsoft.WindowsAlarms", "Microsoft.Windows.Maps",
        "Microsoft.Xbox.TCUI", "Microsoft.XboxApp", "Microsoft.XboxGameOverlay",
        "Microsoft.YourPhone", "Microsoft.ZuneMusic", "Microsoft.ZuneVideo",
        "Microsoft.Microsoft3DViewer", "Microsoft.MicrosoftOfficeHub",
        "Microsoft.MicrosoftSolitaireCollection", "Microsoft.MixedReality.Portal",
        "Microsoft.Office.OneNote", "Microsoft.SkypeApp", "Microsoft.WindowsFeedbackHub",
        "SpotifyAB.SpotifyMusic", "Netflix", "Facebook", "Instagram", "TikTok", "WhatsApp", "Telegram", "Zoom"
    };

    public async Task<List<UwpApp>> GetRemovableAppsAsync()
    {
        var result = new List<UwpApp>();

        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = "powershell.exe",
                Arguments = "-NoProfile -Command \"Get-AppxPackage | Where-Object { $_.IsFramework -eq $false -and $_.SignatureKind -ne 'System' } | Select-Object Name, PackageFullName, Publisher, Version | ConvertTo-Json -Compress\"",
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            using var p = Process.Start(psi);
            if (p == null) return result;

            string output = await p.StandardOutput.ReadToEndAsync();
            await p.WaitForExitAsync();

            if (string.IsNullOrWhiteSpace(output) || output.Trim() == "null")
                return result;

            // Если приложение одно, PowerShell вернет объект {}, а не массив []
            if (output.TrimStart().StartsWith("{"))
                output = $"[{output}]";

            var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
            var appsData = JsonSerializer.Deserialize<List<UwpAppDto>>(output, options);

            if (appsData == null) return result;

            foreach (var dto in appsData)
            {
                if (string.IsNullOrEmpty(dto.PackageFullName)) continue;

                // Проверяем защиту
                bool isProtected = ProtectedApps.Any(p => dto.PackageFullName.Contains(p, StringComparison.OrdinalIgnoreCase));
                if (isProtected) continue;

                // Очищаем имя (убираем технические префиксы)
                string displayName = dto.Name ?? "";
                if (System.Text.RegularExpressions.Regex.IsMatch(displayName, @"^[a-f0-9\-]+$", System.Text.RegularExpressions.RegexOptions.IgnoreCase))
                {
                    displayName = dto.PackageFullName.Split('_')[0].Replace("Microsoft.", "");
                }
                if (displayName.Length < 3) continue;

                bool isSafe = SafeApps.Any(s => dto.PackageFullName.Contains(s, StringComparison.OrdinalIgnoreCase));

                result.Add(new UwpApp
                {
                    Name = displayName,
                    PackageFullName = dto.PackageFullName,
                    Version = dto.Version,
                    Publisher = dto.Publisher,
                    IsSafeToRemove = isSafe
                });
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[UWP] Ошибка получения списка: {ex.Message}");
        }

        return result.OrderByDescending(a => a.IsSafeToRemove).ThenBy(a => a.Name).ToList();
    }

    public async Task<bool> RemoveAppAsync(string packageFullName)
    {
        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = "powershell.exe",
                // Важно: используем двойные кавычки для аргументов и экранируем одинарные
                Arguments = $"-NoProfile -Command \"Remove-AppxPackage -Package '{packageFullName}' -ErrorAction Stop\"",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            using var p = Process.Start(psi);
            if (p == null) return false;

            await p.WaitForExitAsync();
            return p.ExitCode == 0;
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[UWP] Ошибка удаления: {ex.Message}");
            return false;
        }
    }

    // Вспомогательный класс для десериализации JSON
    private class UwpAppDto
    {
        public string Name { get; set; } = string.Empty;
        public string PackageFullName { get; set; } = string.Empty;
        public string Version { get; set; } = string.Empty;
        public string Publisher { get; set; } = string.Empty;
    }
}