using BestWinTweaker.Services;
using BestWinTweaker.ViewModels;
using Microsoft.UI.Xaml; // Для DispatcherTimer
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Navigation;
using System;

namespace BestWinTweaker.Views;

public sealed partial class MonitorPage : Page
{
    public MonitorViewModel ViewModel { get; }
    private DispatcherTimer? _timer;

    public MonitorPage()
    {
        this.InitializeComponent();

        // Получаем Singleton-экземпляр HardwareSensorService из DI-контейнера
        var sensorService = App.GetService<HardwareSensorService>();

        // Передаём его в ViewModel
        ViewModel = new MonitorViewModel(sensorService);
    }

    // Запускаем таймер, когда страница становится видимой
    protected override void OnNavigatedTo(NavigationEventArgs e)
    {
        base.OnNavigatedTo(e);

        if (_timer == null)
        {
            _timer = new DispatcherTimer
            {
                Interval = TimeSpan.FromSeconds(2)
            };
            _timer.Tick += Timer_Tick;
        }

        _timer.Start();
    }

    // Останавливаем таймер, когда уходим со страницы
    protected override void OnNavigatedFrom(NavigationEventArgs e)
    {
        base.OnNavigatedFrom(e);
        _timer?.Stop();
    }

    private async void Timer_Tick(object? sender, object e)
    {
        // Вызываем команду обновления во ViewModel
        await ViewModel.RefreshCommand.ExecuteAsync(null);
    }


}