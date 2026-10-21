using BestWinTweaker.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using System;
using System.Threading.Tasks;

namespace BestWinTweaker.Views;

public sealed partial class OptimizePage : Page
{
    public OptimizeViewModel ViewModel { get; } = new();

    public OptimizePage()
    {
        this.InitializeComponent();
    }

    // Подтверждение перед опасной операцией
    private async Task<bool> ConfirmAsync(string title, string message)
    {
        var dialog = new ContentDialog
        {
            Title = title,
            Content = message,
            PrimaryButtonText = "Продолжить",
            CloseButtonText = "Отмена",
            XamlRoot = this.XamlRoot  // ← обязательно для WinUI 3
        };
        return await dialog.ShowAsync() == ContentDialogResult.Primary;
    }

    private async void PingButton_Click(object sender, RoutedEventArgs e)
    {
        // Простой диалог ввода
        var input = new TextBox { PlaceholderText = "8.8.8.8 или google.com" };
        var dialog = new ContentDialog
        {
            Title = "Проверка пинга",
            Content = input,
            PrimaryButtonText = "Проверить",
            CloseButtonText = "Отмена",
            XamlRoot = this.XamlRoot
        };

        if (await dialog.ShowAsync() == ContentDialogResult.Primary)
        {
            await ViewModel.PingCommand.ExecuteAsync(input.Text);
        }
    }

    private void OpenTaskManager_Click(object sender, RoutedEventArgs e)
    {
        System.Diagnostics.Process.Start("taskmgr.exe");
    }

    private void OpenDeviceManager_Click(object sender, RoutedEventArgs e)
    {
        var psi = new System.Diagnostics.ProcessStartInfo
        {
            FileName = "devmgmt.msc",
            UseShellExecute = true   // ← обязательно для .msc и других документов
        };
        System.Diagnostics.Process.Start(psi);
    }
}