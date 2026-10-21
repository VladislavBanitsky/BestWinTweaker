using CommunityToolkit.Mvvm.ComponentModel;

namespace BestWinTweaker.Models;

public partial class ProcessInfo : ObservableObject
{
    [ObservableProperty]
    private int _pid;

    [ObservableProperty]
    private string _name = string.Empty;

    [ObservableProperty]
    private double _cpuPercent;

    [ObservableProperty]
    private double _memoryPercent;

    [ObservableProperty]
    private double _memoryMb;

    [ObservableProperty]
    private string _status = string.Empty;

    [ObservableProperty]
    private string _statusText = string.Empty;

    [ObservableProperty]
    private string _statusColor = "#777777";
}