using BestWinTweaker.Services;
using BestWinTweaker.Views;
using Microsoft.UI;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Windows.Storage;
using System;
using Windows.Graphics;
using WinRT.Interop;

namespace BestWinTweaker;

public sealed partial class MainWindow : Window
{
    private readonly ConfigManager _configManager = new();

    public MainWindow()
    {
        this.InitializeComponent();
        ContentFrame.Navigate(typeof(MonitorPage));
        IntPtr hWnd = WindowNative.GetWindowHandle(this);
        WindowId windowId = Win32Interop.GetWindowIdFromWindow(hWnd);
        AppWindow appWindow = AppWindow.GetFromWindowId(windowId);

        // Задаем ширину и высоту (в логических пикселях)
        appWindow.ResizeClient(new SizeInt32(1400, 690));
        // Устанавливаем заголовок окна
        appWindow.Title = "BestWinTweaker - Системный монитор и оптимизатор";
        // Установка иконки заголовка
        appWindow.SetIcon("BestWinTweaker.ico");

        // Получаем ConfigManager из DI
        _configManager = App.GetService<ConfigManager>();

        // Загружаем сохраненную тему
        var savedTheme = _configManager.GetTheme();
        ApplyTheme(savedTheme);

        // Применяем размеры окна и его расположение
        RestoreWindowBounds();

        // Подписываемся на закрытие
        this.Closed += MainWindow_Closed;

    }

    private void MainWindow_Closed(object sender, WindowEventArgs args)
    {
        var appWindow = this.AppWindow;
        if (appWindow == null) return;

        // Определяем, развернуто ли окно
        bool isMaximized = false;
        if (appWindow.Presenter is OverlappedPresenter presenter)
        {
            isMaximized = presenter.State == OverlappedPresenterState.Maximized;
        }

        // Сохраняем в наш JSON-файл
        _configManager.SaveWindowBounds(
            appWindow.Position.X,
            appWindow.Position.Y,
            appWindow.Size.Width,
            appWindow.Size.Height,
            isMaximized
        );
    }

    private void RestoreWindowBounds()
    {
        var appWindow = this.AppWindow;
        var bounds = _configManager.LoadWindowBounds();

        if (bounds.HasValue)
        {
            var (x, y, width, height, isMaximized) = bounds.Value;

            // Восстанавливаем размер и позицию
            appWindow.MoveAndResize(new RectInt32(x, y, width, height));

            // Если было развернуто — разворачиваем
            if (isMaximized && appWindow.Presenter is OverlappedPresenter presenter)
            {
                presenter.Maximize();
            }
        }
        else
        {
            // Если настроек нет — ставим размер по умолчанию и центрируем
            appWindow.Resize(new SizeInt32(1400, 690));

            // Центрирование
            CenterWindow(appWindow);
        }
    }

    private void CenterWindow(AppWindow appWindow)
    {
        // Получаем DisplayArea для текущего окна
        var displayArea = DisplayArea.GetFromWindowId(appWindow.Id, DisplayAreaFallback.Nearest);
        if (displayArea == null) return;

        // Берем РАБОЧУЮ область (исключает панель задач)
        var workArea = displayArea.WorkArea;

        // Вычисляем позицию для центрирования внутри рабочей области
        var centeredPosition = new PointInt32(
            workArea.X + (workArea.Width - 1400) / 2,
            workArea.Y + (workArea.Height - 690) / 2
        );

        appWindow.Move(centeredPosition);
    }

    private void NavView_SelectionChanged(NavigationView sender, NavigationViewSelectionChangedEventArgs args)
    {
        if (args.SelectedItem is NavigationViewItem item)
        {
            var tag = item.Tag?.ToString();
            switch (tag)
            {
                case "monitor": ContentFrame.Navigate(typeof(MonitorPage)); break;      
                case "processes": ContentFrame.Navigate(typeof(ProcessesPage)); break;
                case "optimize":  ContentFrame.Navigate(typeof(OptimizePage));  break;
                case "autostart": ContentFrame.Navigate(typeof(AutostartPage)); break;
                case "uwp":       ContentFrame.Navigate(typeof(UwpPage));       break;
                case "about":     ContentFrame.Navigate(typeof(AboutPage));     break;
            }
        }
    }

    private void ThemeToggle_Toggled(object sender, RoutedEventArgs e)
    {
        // Определяем, какая тема выбрана
        string newTheme = ThemeToggle.IsOn ? "Dark" : "Light";

        // Применяем тему
        ApplyTheme(newTheme);

        // Сохраняем в конфиг
        _configManager.SetTheme(newTheme);
    }

    private void ApplyTheme(string theme)
    {
        // 1. Меняем тему содержимого
        if (this.Content is FrameworkElement rootElement)
        {
            rootElement.RequestedTheme = theme == "Dark" ? ElementTheme.Dark : ElementTheme.Light;
        }

        // 2. Меняем тему шапки окна
        var titleBar = this.AppWindow.TitleBar;
        if (titleBar != null)
        {
            titleBar.PreferredTheme = theme == "Dark"
                ? TitleBarTheme.Dark
                : TitleBarTheme.Light;
        }

        // Синхронизируем переключатель (чтобы не было рекурсии при старте)
        if (ThemeToggle.IsOn != (theme == "Dark"))
        {
            ThemeToggle.IsOn = theme == "Dark";
        }
    }
}