using BestWinTweaker.Services;
using BestWinTweaker.ViewModels;
using Microsoft.UI.Xaml; // Для DispatcherTimer
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Navigation;
using Windows.ApplicationModel.DataTransfer;
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

    // Копирование полей 
    private void CopyText_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string text && !string.IsNullOrEmpty(text))
        {
            var dataPackage = new DataPackage();
            dataPackage.SetText(text);
            Clipboard.SetContent(dataPackage);

            // Можно добавить визуальное подтверждение (например, изменить иконку на галочку на секунду)
            var icon = btn.Content as FontIcon;
            if (icon != null)
            {
                icon.Glyph = "\uE73E"; // Иконка галочки (CheckMark)
                                       // Вернуть обратно через 1.5 секунды (можно использовать DispatcherTimer)
                var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(1.5) };
                timer.Tick += (s, args) =>
                {
                    icon.Glyph = "\uE8C8"; // Возвращаем иконку копирования
                    timer.Stop();
                };
                timer.Start();
            }
        }
    }
}