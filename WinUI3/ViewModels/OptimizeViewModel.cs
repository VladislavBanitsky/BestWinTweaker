using BestWinTweaker.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.UI;
using System;
using System.Diagnostics;
using System.Threading.Tasks;
using Windows.ApplicationModel.DataTransfer; // Для копирования

namespace BestWinTweaker.ViewModels;

public partial class OptimizeViewModel : ObservableObject
{
    private readonly TweakerService _tweaker = new();

    public StatusManager Status { get; } = new();

    [ObservableProperty]
    private bool _isBusy;

    [ObservableProperty]
    private string _pingResult = string.Empty;

    [ObservableProperty]
    private string _pingHostName = string.Empty; // Имя хоста для копирования

    [ObservableProperty]
    private bool _hasPingResult = false; // Показывать ли кнопку копирования

    public OptimizeViewModel()
    {
        UpdateIndexingText();
        Status.StatusChanged += OnStatusChanged;
    }

    [ObservableProperty]
    private string _indexingButtonText = "Управление индексацией";

    private void UpdateIndexingText()
    {
        IndexingButtonText = _tweaker.IsIndexingEnabled()
            ? "Отключить индексацию"
            : "Включить индексацию";
    }

    private void OnStatusChanged(object? sender, EventArgs e)
    {
        // Если статус не начинается с "Проверка" и не содержит "Скопировано",
        // значит, это результат другой команды — прячем кнопку копирования.
        if (!Status.Text.StartsWith("Проверка") && !Status.Text.StartsWith("Скопировано") && !Status.Text.StartsWith("Узел"))
        {
            HasPingResult = false;
            _pingHostName = string.Empty;
        }
    }

    [RelayCommand]
    private async Task FixUpdatesAsync()
    {
        IsBusy = true;
        Status.SetStatus("Исправление ошибок обновлений...", Colors.Orange, 0);
        var success = await _tweaker.FixUpdatesAsync();
        if (success)
        {
            Status.SetStatus("Службы обновлений перезапущены", Colors.White);
        }
        else
        {
            Status.SetStatus("Ошибка", Colors.Red);
        }
        IsBusy = false;
    }

    [RelayCommand]
    private void ToggleIndexing()
    {
        IsBusy = true;
        if (_tweaker.IsIndexingEnabled())
        {
            _tweaker.DisableIndexing();
            Status.SetStatus("Индексация отключена", Colors.White);
        }
        else
        {
            _tweaker.EnableIndexing();
            Status.SetStatus("Индексация включена", Colors.White);
        }
        UpdateIndexingText();
        IsBusy = false;
    }

    [RelayCommand]
    private async Task DownloadWindowsAsync()
    {
        IsBusy = true;
        Status.SetStatus("Запуск Fido для скачивания Windows...", Colors.Orange, 0);
        var success = await _tweaker.StartWindowsDownloadAsync();
        if (success)
        {
            Status.SetStatus("Открыто окно Fido", Colors.White);
        }
        else
        {
            Status.SetStatus("Ошибка", Colors.Red);
        }
        IsBusy = false;
    }

    [RelayCommand]
    private async Task SetBingWallpaperAsync()
    {
        IsBusy = true;
        Status.SetStatus("Загрузка обоев Bing...", Colors.Orange, 0);
        var (success, message) = await _tweaker.SetBingWallpaperAsync();
        if (success)
        {
            Status.SetStatus($"Обои Bing установлены! {message}", Colors.White);
        }
        else
        {
            Status.SetStatus("Ошибка загрузки", Colors.Red);
        }
        IsBusy = false;
    }

    [RelayCommand]
    private async Task RemoveWatermarkAsync()
    {
        IsBusy = true;
        Status.SetStatus("Запуск UWD...", Colors.Orange, 0);
        var success = await _tweaker.RemoveWatermarkAsync();
        if (success)
        {
            Status.SetStatus("Водяной знак удалён", Colors.White);
        }
        else
        {
            Status.SetStatus("Ошибка", Colors.Red);
        }
        IsBusy = false;
    }

    [RelayCommand]
    private void OpenTaskManager()
    {
        Process.Start(new ProcessStartInfo { FileName = "taskmgr.exe", UseShellExecute = true });
        Status.SetStatus("Открыто Диспетчер задач", Colors.White);
    }

    [RelayCommand]
    private void OpenDeviceManager()
    {
        Process.Start(new ProcessStartInfo { FileName = "devmgmt.msc", UseShellExecute = true });
        Status.SetStatus("Открыт Диспетчер устройств", Colors.White);
    }

    [RelayCommand]
    private void OpenDiskManagement()
    {
        Process.Start(new ProcessStartInfo { FileName = "diskmgmt.msc", UseShellExecute = true });
        Status.SetStatus("Открыто Управление дисками", Colors.White);
    }

    [RelayCommand]
    private async Task ClearTempAsync()
    {
        IsBusy = true;
        Status.SetStatus("Очистка временных файлов...", Colors.Orange, 0);
        var (deleted, error) = await Task.Run(() => _tweaker.ClearTemp());
        if (error == null)
        {
            Status.SetStatus($"Очищено {deleted} файлов и папок", Colors.White);
        }
        else
        {
            Status.SetStatus($"Очищено {deleted}, ошибки: {error}", Colors.Red);
        }
        IsBusy = false;
    }

    [RelayCommand]
    private async Task DisableTelemetryAsync()
    {
        IsBusy = true;
        Status.SetStatus("Отключение служб телеметрии...", Colors.Orange, 0);
        var (disabled, errors) = await Task.Run(() => _tweaker.DisableTelemetry());
        if (errors == null)
        {
            Status.SetStatus($"Отключено {disabled} служб", Colors.White);
        }
        else
        {
            Status.SetStatus($"Отключено {disabled}, ошибки: {errors}", Colors.Red);
        }
        IsBusy = false;
    }

    [RelayCommand]
    private async Task FlushDnsAsync()
    {
        IsBusy = true;
        Status.SetStatus("Очистка DNS кэша...", Colors.Orange, 0);
        var success = await Task.Run(() => _tweaker.FlushDns(out _));
        if (success)
        {
            Status.SetStatus("DNS кэш очищен", Colors.White);
        }
        else
        {
            Status.SetStatus("Ошибка очистки DNS", Colors.Red);
        }
        IsBusy = false;
    }

    [RelayCommand]
    private async Task PingAsync(string host)
    {
        if (string.IsNullOrWhiteSpace(host)) return;

        IsBusy = true;
        HasPingResult = false;
        Status.SetStatus($"Проверка {host}...", Colors.Orange, 0);
        var (success, hostName, fullResult) = await _tweaker.PingAsync(host);
        // СНАЧАЛА сохраняем данные для копирования
        PingHostName = hostName;
        HasPingResult = true;
        // ПОТОМ меняем статус (событие OnStatusChanged увидит, что статус начинается с "Узел" и не сбросит кнопку)
        if (success)
            Status.SetStatus(fullResult, Colors.White);
        else
            Status.SetStatus(fullResult, Colors.Red);

        IsBusy = false;
    }

    [RelayCommand]
    private void CopyPingResult()
    {
        if (string.IsNullOrEmpty(PingHostName)) return;

        var dataPackage = new DataPackage();
        dataPackage.SetText(PingHostName);
        Clipboard.SetContent(dataPackage);
        Status.SetStatus($"Скопировано: {PingHostName}", Colors.White);
        HasPingResult = false; // Прячем кнопку копирования
    }
}