using BestWinTweaker.Models;
using BestWinTweaker.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using System.Collections.ObjectModel;
using System.Threading.Tasks;
using Microsoft.UI.Dispatching; // Для DispatcherTimer

namespace BestWinTweaker.ViewModels;

public partial class MonitorViewModel : ObservableObject
{
    private readonly MonitorService _monitorService = new();
    private bool _isRefreshing;

    private readonly HardwareSensorService _sensorService;

    [ObservableProperty]
    private string _cpuTemperature = "—";

    [ObservableProperty]
    private double _gpuLoad;

    [ObservableProperty]
    private double _gpuTemperature;

    [ObservableProperty]
    private string _gpuName = string.Empty;

    [ObservableProperty]
    private string _gpuMemoryText = string.Empty;

    [ObservableProperty]
    private string _boardModel = "Загрузка...";

    [ObservableProperty]
    private string _networkAdapter = "Загрузка...";

    [ObservableProperty]
    private string _downloadSpeed = "0.00";

    [ObservableProperty]
    private string _uploadSpeed = "0.00";

    [ObservableProperty]
    private string _totalDownloadGb = "0.00";

    [ObservableProperty]
    private string _totalUploadGb = "0.00";

    public ObservableCollection<GpuInfo> Gpus { get; } = new();

    [ObservableProperty]
    private string _cpuName = "Загрузка...";

    [ObservableProperty]
    private double _cpuUsage;

    [ObservableProperty]
    private double _cpuFrequency;

    [ObservableProperty]
    private string _coresText = string.Empty;

    [ObservableProperty]
    private double _ramPercent;

    [ObservableProperty]
    private string _ramUsageText = "0 GB / 0 GB";

    public ObservableCollection<DiskInfo> Disks { get; } = new();

    public MonitorViewModel(HardwareSensorService sensorService)
    {
        _sensorService = sensorService;
        _ = RefreshAsync();
    }

    [RelayCommand]
    private async Task RefreshAsync()
    {
        if (_isRefreshing) return;
        _isRefreshing = true;

        try
        {
            var cpu = await Task.Run(() => _monitorService.GetCpuInfo());
            CpuName = cpu.Name;
            CpuUsage = cpu.UsagePercent;
            CpuFrequency = cpu.FrequencyMhz;
            CoresText = $"Ядер: {cpu.LogicalCores} логических, {cpu.PhysicalCores} физических";

            var ram = await Task.Run(() => _monitorService.GetRamInfo());
            RamPercent = ram.Percent;
            RamUsageText = $"{ram.UsedGb:F1} GB / {ram.TotalGb:F1} GB";

            System.Diagnostics.Debug.WriteLine($"[RAM] Percent: {ram.Percent}%, Used: {ram.UsedGb} GB");
            RamPercent = ram.Percent;
            RamUsageText = $"{ram.UsedGb:F1} GB / {ram.TotalGb:F1} GB";

            var disks = await Task.Run(() => _monitorService.GetDisks());
            Disks.Clear();
            foreach (var d in disks)
                Disks.Add(d);

            var cpuTemps = await Task.Run(() => _sensorService.GetCpuTemperatures());
            if (cpuTemps.PackageTempC > 0)
                CpuTemperature = $"{cpuTemps.PackageTempC}°C";
            else if (cpuTemps.MaxCoreTempC > 0)
                CpuTemperature = $"{cpuTemps.MaxCoreTempC}°C";
            else
                CpuTemperature = "—";

            // Загрузка данных материнской платы
            BoardModel = await Task.Run(() => _monitorService.GetBoardModel());

            // Загрузка данных сети
            var net = await Task.Run(() => _monitorService.GetNetworkInfo());
            NetworkAdapter = net.adapter;
            DownloadSpeed = net.download;
            UploadSpeed = net.upload;
            TotalDownloadGb = net.totalDownload;
            TotalUploadGb = net.totalUpload;

            var gpus = await Task.Run(() => _sensorService.GetGpus());
            Gpus.Clear();
            foreach (var g in gpus)
                Gpus.Add(g);

            if (gpus.Count > 0)
            {
                var primary = gpus[0];
                GpuName = primary.Name;
                GpuLoad = primary.LoadPercent;
                GpuTemperature = primary.TemperatureC;
                GpuMemoryText = primary.MemoryTotalMb > 0
                    ? $"{primary.MemoryUsedMb:F0} / {primary.MemoryTotalMb:F0} MB ({primary.MemoryPercent:F1}%)"
                    : "—";
            }
        }
        finally
        {
            _isRefreshing = false;
        }
    }
}