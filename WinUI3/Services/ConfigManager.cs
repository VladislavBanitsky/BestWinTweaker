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
}