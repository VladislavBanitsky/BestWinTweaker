using System;
using System.IO;
using System.Text.Json;
using System.Collections.Generic;

namespace BestWinTweaker.Services;

public class ConfigManager
{
    private readonly string _configDir;
    private readonly string _configFile;
    private Dictionary<string, string> _config;

    public ConfigManager()
    {
        // Создаем папку %USERPROFILE%\.bwt
        var userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        _configDir = Path.Combine(userProfile, ".bwt");
        _configFile = Path.Combine(_configDir, "config.json");

        // Создаем папку, если её нет
        if (!Directory.Exists(_configDir))
        {
            Directory.CreateDirectory(_configDir);
        }

        // Загружаем конфиг
        _config = LoadConfig();
    }

    private Dictionary<string, string> LoadConfig()
    {
        if (!File.Exists(_configFile))
            return new Dictionary<string, string>();

        try
        {
            var json = File.ReadAllText(_configFile);
            var data = JsonSerializer.Deserialize<Dictionary<string, string>>(json);
            return data ?? new Dictionary<string, string>();
        }
        catch
        {
            return new Dictionary<string, string>();
        }
    }

    private void SaveConfig()
    {
        try
        {
            var options = new JsonSerializerOptions { WriteIndented = true };
            var json = JsonSerializer.Serialize(_config, options);
            File.WriteAllText(_configFile, json);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[Config] Ошибка сохранения: {ex.Message}");
        }
    }

    // --- Методы для работы с темой ---

    public string GetTheme()
    {
        // По умолчанию "Light"
        return _config.TryGetValue("theme", out var theme) ? theme : "Dark";
    }

    public void SetTheme(string theme)
    {
        _config["theme"] = theme;
        SaveConfig();
    }

    // --- Методы для работы с размером и расположением окна ---
    public void SaveWindowBounds(int x, int y, int width, int height, bool isMaximized)
    {
        _config["WinX"] = x.ToString();
        _config["WinY"] = y.ToString();
        _config["WinWidth"] = width.ToString();
        _config["WinHeight"] = height.ToString();
        _config["WinMaximized"] = isMaximized.ToString();
        SaveConfig();
    }

    public (int X, int Y, int Width, int Height, bool IsMaximized)? LoadWindowBounds()
    {
        if (_config.TryGetValue("WinWidth", out var wStr) &&
            _config.TryGetValue("WinHeight", out var hStr) &&
            _config.TryGetValue("WinX", out var xStr) &&
            _config.TryGetValue("WinY", out var yStr))
        {
            if (int.TryParse(wStr, out int w) && int.TryParse(hStr, out int h) &&
                int.TryParse(xStr, out int x) && int.TryParse(yStr, out int y))
            {
                bool isMax = _config.TryGetValue("WinMaximized", out var maxStr) && bool.TryParse(maxStr, out bool m) && m;
                return (x, y, w, h, isMax);
            }
        }
        return null; // Нет сохраненных данных
    }
}