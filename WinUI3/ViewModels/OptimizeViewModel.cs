using BestWinTweaker.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using System.Threading.Tasks;
using System.Diagnostics;

namespace BestWinTweaker.ViewModels;

public partial class OptimizeViewModel : ObservableObject
{
    private readonly TweakerService _tweaker = new();

    [ObservableProperty]
    private bool _isBusy;

    [ObservableProperty]
    private string _statusMessage = "Готов";

    public OptimizeViewModel()
    {
        UpdateIndexingText();
    }

    [ObservableProperty]
    private string _indexingButtonText = "Управление индексацией";

    private void UpdateIndexingText()
    {
        IndexingButtonText = _tweaker.IsIndexingEnabled()
            ? "Отключить индексацию"
            : "Включить индексацию";
    }

    [RelayCommand]
    private async Task FixUpdatesAsync()
    {
        IsBusy = true;
        StatusMessage = "Исправление ошибок обновлений...";
        var success = await _tweaker.FixUpdatesAsync();
        StatusMessage = success ? "Службы обновлений перезапущены" : "Ошибка";
        IsBusy = false;
    }

    [RelayCommand]
    private void ToggleIndexing()
    {
        IsBusy = true;
        if (_tweaker.IsIndexingEnabled())
        {
            _tweaker.DisableIndexing();
            StatusMessage = "Индексация отключена";
        }
        else
        {
            _tweaker.EnableIndexing();
            StatusMessage = "Индексация включена";
        }
        UpdateIndexingText();
        IsBusy = false;
    }

    [RelayCommand]
    private async Task DownloadWindowsAsync()
    {
        IsBusy = true;
        StatusMessage = "Запуск Fido для скачивания Windows...";
        var success = await _tweaker.StartWindowsDownloadAsync();
        StatusMessage = success ? "Окно PowerShell открыто" : "Ошибка";
        IsBusy = false;
    }

    [RelayCommand]
    private async Task SetBingWallpaperAsync()
    {
        IsBusy = true;
        StatusMessage = "Загрузка обоев Bing...";
        var success = await _tweaker.SetBingWallpaperAsync();
        StatusMessage = success ? "Обои Bing установлены!" : "Ошибка загрузки";
        IsBusy = false;
    }

    [RelayCommand]
    private async Task RemoveWatermarkAsync()
    {
        IsBusy = true;
        StatusMessage = "Удаление водяного знака (требуются права администратора)...";
        var success = await _tweaker.RemoveWatermarkAsync();
        StatusMessage = success ? "Водяной знак удален" : "Ошибка";
        IsBusy = false;
    }

    [RelayCommand]
    private void OpenDiskManagement()
    {
        Process.Start(new ProcessStartInfo { FileName = "diskmgmt.msc", UseShellExecute = true });
    }

    [RelayCommand]
    private async Task ClearTempAsync()
    {
        IsBusy = true;
        StatusMessage = "Очистка временных файлов...";
        var (deleted, error) = await Task.Run(() => _tweaker.ClearTemp());
        StatusMessage = error == null
            ? $"Очищено {deleted} файлов и папок"
            : $"Очищено {deleted}, ошибки: {error}";
        IsBusy = false;
    }

    [RelayCommand]
    private async Task DisableTelemetryAsync()
    {
        IsBusy = true;
        StatusMessage = "Отключение служб телеметрии...";
        var (disabled, errors) = await Task.Run(() => _tweaker.DisableTelemetry());
        StatusMessage = errors == null
            ? $"Отключено {disabled} служб"
            : $"Отключено {disabled}, ошибки: {errors}";
        IsBusy = false;
    }

    [RelayCommand]
    private async Task FlushDnsAsync()
    {
        IsBusy = true;
        StatusMessage = "Очистка DNS кэша...";
        var success = await Task.Run(() => _tweaker.FlushDns(out _));
        StatusMessage = success ? "DNS кэш очищен" : "Ошибка очистки DNS";
        IsBusy = false;
    }

    [RelayCommand]
    private async Task PingAsync(string host)
    {
        if (string.IsNullOrWhiteSpace(host)) return;
        IsBusy = true;
        StatusMessage = $"Проверка {host}...";
        var (success, result) = await _tweaker.PingAsync(host);
        StatusMessage = result;
        IsBusy = false;
    }
}