using System;
using CommunityToolkit.Mvvm.ComponentModel;
using Microsoft.UI;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Media;
using Windows.UI;

namespace BestWinTweaker.Services;

public partial class StatusManager : ObservableObject
{
    [ObservableProperty]
    private string _text = "Готов";

    [ObservableProperty]
    private Brush _textColor = new SolidColorBrush(Colors.Gray);

    private DispatcherTimer? _resetTimer;

    // Событие, которое сообщает ViewModel, что статус изменился
    public event EventHandler? StatusChanged;

    public void SetStatus(string text, Color? color = null, int timeoutMs = 3000)
    {
        _resetTimer?.Stop();

        Text = text;
        TextColor = new SolidColorBrush(color ?? Colors.Gray);

        // Уведомляем подписчиков
        StatusChanged?.Invoke(this, EventArgs.Empty);

        if (timeoutMs > 0)
        {
            _resetTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(timeoutMs) };
            _resetTimer.Tick += (s, e) =>
            {
                Text = "Готов";
                TextColor = new SolidColorBrush(Colors.Gray);
                _resetTimer?.Stop();
                StatusChanged?.Invoke(this, EventArgs.Empty); // Уведомляем и при сбросе
            };
            _resetTimer.Start();
        }
    }

    public void Reset()
    {
        _resetTimer?.Stop();
        Text = "Готов";
        TextColor = new SolidColorBrush(Colors.Gray);
        StatusChanged?.Invoke(this, EventArgs.Empty);
    }
}