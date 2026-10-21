using BestWinTweaker.Services;
using BestWinTweaker.Views;
using Microsoft.UI;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
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

        // Центрируем окно на экране
        var displayArea = DisplayArea.GetFromWindowId(appWindow.Id, DisplayAreaFallback.Nearest);
        if (displayArea != null)
        {
            var centeredPosition = new PointInt32(
                (displayArea.WorkArea.Width - 1400) / 2,
                (displayArea.WorkArea.Height - 690) / 2
            );
            appWindow.Move(centeredPosition);
        }

        // Получаем ConfigManager из DI
        _configManager = App.GetService<ConfigManager>();

        // Загружаем сохраненную тему при старте
        var savedTheme = _configManager.GetTheme();
        ApplyTheme(savedTheme);
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