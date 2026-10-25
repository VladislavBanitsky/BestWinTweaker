using BestWinTweaker.Services;
using BestWinTweaker.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Navigation;
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
        // Подписываемся на обновление коллекции, чтобы восстановить скролл
        ViewModel.Processes.CollectionChanged += Processes_CollectionChanged;
    }

    private void Processes_CollectionChanged(object? sender, System.Collections.Specialized.NotifyCollectionChangedEventArgs e)
    {
        // Если список был очищен (Clear) и заново заполнен, это вызывает сброс скролла.
        // Но мы не можем вернуть скролл прямо здесь, так как UI еще не успел отрисоваться.
        // Вместо этого используем DispatcherQueue, чтобы восстановить позицию после отрисовки.
        if (e.Action == System.Collections.Specialized.NotifyCollectionChangedAction.Reset)
        {
            // Запоминаем позицию скролла
            var scrollViewer = FindScrollViewer(ProcessListView);
            if (scrollViewer != null)
            {
                double offset = scrollViewer.VerticalOffset;

                // Восстанавливаем позицию после того, как UI обновится
                DispatcherQueue.TryEnqueue(() =>
                {
                    scrollViewer.ChangeView(null, offset, null, true);
                });
            }
        }
    }

    // Вспомогательный метод для поиска ScrollViewer внутри ListView
    private ScrollViewer? FindScrollViewer(DependencyObject parent)
    {
        for (int i = 0; i < VisualTreeHelper.GetChildrenCount(parent); i++)
        {
            var child = VisualTreeHelper.GetChild(parent, i);
            if (child is ScrollViewer sv) return sv;
            var result = FindScrollViewer(child);
            if (result != null) return result;
        }
        return null;
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