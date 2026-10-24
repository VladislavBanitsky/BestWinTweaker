using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Navigation;
using BestWinTweaker.ViewModels;
using BestWinTweaker.Services;
using System;

namespace BestWinTweaker.Views;

public sealed partial class ProcessesPage : Page
{
    public ProcessesViewModel ViewModel { get; }
    private DispatcherTimer? _timer;

    public ProcessesPage()
    {
        this.InitializeComponent();
        var processService = App.GetService<ProcessService>();
        ViewModel = new ProcessesViewModel(processService);
    }

    protected override void OnNavigatedTo(NavigationEventArgs e)
    {
        base.OnNavigatedTo(e);

        // Запускаем таймер при входе на вкладку
        if (_timer == null)
        {
            _timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(2) };
            _timer.Tick += async (s, args) => await ViewModel.RefreshCommand.ExecuteAsync(null);  // или RefreshFastCommand
        }
        _timer.Start();
    }

    protected override void OnNavigatedFrom(NavigationEventArgs e)
    {
        base.OnNavigatedFrom(e);

        // Останавливаем таймер при уходе с вкладки (экономия ресурсов)
        _timer?.Stop();
    }
}