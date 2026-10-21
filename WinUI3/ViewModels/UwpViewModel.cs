using BestWinTweaker.Models;
using BestWinTweaker.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;

namespace BestWinTweaker.ViewModels;

public partial class UwpViewModel : ObservableObject
{
    private readonly UwpService _uwpService;
    private List<UwpApp> _allApps = new();

    [ObservableProperty]
    private bool _isBusy;

    [ObservableProperty]
    private string _statusMessage = "Готов";

    public ObservableCollection<UwpApp> Apps { get; } = new();

    public UwpViewModel(UwpService uwpService)
    {
        _uwpService = uwpService;
        _ = LoadAppsAsync();
    }

    [RelayCommand]
    private async Task LoadAppsAsync()
    {
        IsBusy = true;
        StatusMessage = "Загрузка списка UWP-приложений...";
        Apps.Clear();

        var apps = await _uwpService.GetRemovableAppsAsync();
        _allApps = apps;

        foreach (var app in apps)
        {
            Apps.Add(app);
        }

        int safeCount = apps.Count(a => a.IsSafeToRemove);
        StatusMessage = $"Найдено: {apps.Count} | Безопасно удалить: {safeCount}";
        IsBusy = false;
    }

    [RelayCommand]
    private async Task RemoveSelectedAsync()
    {
        var selected = Apps.Where(a => a.IsSelected).ToList();
        if (!selected.Any())
        {
            StatusMessage = "Выберите приложения для удаления.";
            return;
        }

        IsBusy = true;
        StatusMessage = $"Удаление {selected.Count} приложений...";

        int successCount = 0;
        foreach (var app in selected)
        {
            bool success = await _uwpService.RemoveAppAsync(app.PackageFullName);
            if (success) successCount++;
        }

        StatusMessage = $"Успешно удалено: {successCount} из {selected.Count}. Обновление списка...";
        await LoadAppsAsync(); // Перезагружаем список после удаления
    }

    [RelayCommand]
    private void SelectAllSafe()
    {
        foreach (var app in Apps.Where(a => a.IsSafeToRemove))
        {
            app.IsSelected = true;
        }
    }
}