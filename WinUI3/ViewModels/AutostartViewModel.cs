using BestWinTweaker.Models;
using BestWinTweaker.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;

namespace BestWinTweaker.ViewModels;

public partial class AutostartViewModel : ObservableObject
{
    private readonly StartupService _service;
    private List<StartupEntry> _allEntries = new();
    private Dictionary<string, bool> _originalStates = new();

    [ObservableProperty]
    private string _statusMessage = "Готов";

    [ObservableProperty]
    private bool _isBusy;

    public ObservableCollection<StartupEntry> Entries { get; } = new();

    public AutostartViewModel(StartupService service)
    {
        _service = service;
        _ = RefreshAsync();
    }

    [RelayCommand]
    private async Task RefreshAsync()
    {
        IsBusy = true;
        StatusMessage = "Загрузка списка автозагрузки...";

        // Сервис УЖЕ возвращает объединенный список (реестр + Планировщик + бэкап)
        var entries = await Task.Run(() => _service.GetStartupEntries());

        _allEntries = entries.OrderBy(e => e.Name).ToList();

        // СНАПШОТ: сохраняем исходное состояние по ключу
        _originalStates = _allEntries.ToDictionary(
            e => $"{e.Name}|{e.Source}",
            e => e.Enabled,
            StringComparer.OrdinalIgnoreCase);

        Entries.Clear();
        foreach (var e in _allEntries)
            Entries.Add(e);

        StatusMessage = $"Всего: {Entries.Count} | Включено: {Entries.Count(e => e.Enabled)}";
        IsBusy = false;
    }

    [RelayCommand]
    private async Task ApplyChangesAsync()
    {
        IsBusy = true;
        StatusMessage = "Применение изменений...";

        int changed = 0;
        int failed = 0;
        foreach (var entry in Entries)
        {
            // Сравниваем с неизменяемым снапшотом _originalStates (ключ "Name|Source"),
            var key = $"{entry.Name}|{entry.Source}";
            if (!_originalStates.TryGetValue(key, out var originalEnabled))
            {
                // Запись новая (не было при RefreshAsync) — считаем, что было отключено
                originalEnabled = false;
            }
            if (originalEnabled == entry.Enabled) continue;   // состояние не менялось

            bool success;
            if (entry.Enabled)
            {
                // Передаем entry.Path (при включении сервис сам удалит запись из бэкапа)
                success = await Task.Run(() => _service.Enable(entry.Name, entry.Source, entry.Path));
            }
            else
            {
                // Передаем entry.Path (при отключении сервис сам сохранит путь в бэкап)
                success = await Task.Run(() => _service.Disable(entry.Name, entry.Source, entry.Path));
            }
            if (success) changed++;
            else failed++;
        }

        if (failed > 0)
            StatusMessage = $"Изменено: {changed} | Не удалось: {failed} (нужны права администратора?)";
        else if (changed > 0)
            StatusMessage = $"Применено изменений: {changed}";
        else
            StatusMessage = "Изменений не было";
        await RefreshAsync();
    }

    [RelayCommand]
    private void SelectAll()
    {
        foreach (var e in Entries) e.Enabled = true;
    }

    [RelayCommand]
    private void DeselectAll()
    {
        foreach (var e in Entries) e.Enabled = false;
    }
}