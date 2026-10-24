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

public partial class ProcessesViewModel : ObservableObject
{
    private readonly ProcessService _processService;
    private bool _isRefreshing;
    //private bool _isFastRefreshing = false;
    private List<ProcessInfo> _allProcesses = new();

    [ObservableProperty]
    private string _searchText = string.Empty;

    [ObservableProperty]
    private bool _showSystem;

    [ObservableProperty]
    private ProcessInfo? _selectedProcess;

    public ObservableCollection<ProcessInfo> Processes { get; } = new();

    public ProcessesViewModel(ProcessService processService)
    {
        _processService = processService;
        _ = RefreshAsync();
    }

    partial void OnSearchTextChanged(string value) => ApplyFilter();

    partial void OnShowSystemChanged(bool value) => _ = RefreshAsync();

    [RelayCommand]
    private async Task RefreshAsync()
    {
        if (_isRefreshing) return;
        _isRefreshing = true;

        try
        {
            var data = await Task.Run(() => _processService.GetProcesses(ShowSystem));
            _allProcesses = data;
            ApplyFilter();
        }
        finally { _isRefreshing = false; }
    }

    //[RelayCommand]
    //private async Task RefreshFastAsync()
    //{
    //    System.Diagnostics.Debug.WriteLine($"[VM] Обновлено процессов: {Processes.Count}");
    //    if (_isFastRefreshing) return;
    //    _isFastRefreshing = true;

    //    try
    //    {
    //        // Получаем быстрые метрики в фоне
    //        var metrics = await Task.Run(() => _processService.GetProcessesFast());

    //        // Обновляем существующие элементы в коллекции
    //        foreach (var process in _allProcesses)
    //        {
    //            if (metrics.TryGetValue(process.Pid, out var data))
    //            {
    //                process.CpuPercent = data.Cpu;
    //                process.MemoryMb = data.MemoryMb;

    //                // Если процесс перестал отвечать
    //                if (process.Status != data.Status)
    //                {
    //                    process.Status = data.Status;
    //                    // Обновите текст и цвет статуса, если они привязаны к Status
    //                }
    //            }
    //        }
    //    }
    //    catch (Exception ex)
    //    {
    //        System.Diagnostics.Debug.WriteLine($"[FastRefresh] Ошибка: {ex.Message}");
    //    }
    //    finally
    //    {
    //        _isFastRefreshing = false; // Обязательно сбрасываем флаг
    //    }
    //}

    [RelayCommand]
    private async Task KillSelectedAsync()
    {
        if (SelectedProcess == null) return;
        var pid = SelectedProcess.Pid;
        var name = SelectedProcess.Name;

        var success = await Task.Run(() => _processService.KillProcess(pid));
        if (success)
        {
            await RefreshAsync();
        }
        // В реальном приложении здесь нужно показать уведомление пользователю
    }

    private void ApplyFilter()
    {
        var filtered = string.IsNullOrWhiteSpace(SearchText)
            ? _allProcesses
            : _allProcesses.Where(p =>
                p.Name.Contains(SearchText, StringComparison.OrdinalIgnoreCase) ||
                p.Pid.ToString().Contains(SearchText)).ToList();

        Processes.Clear();
        foreach (var p in filtered)
            Processes.Add(p);
    }
}