using Microsoft.UI.Xaml.Controls;
using BestWinTweaker.ViewModels;
using BestWinTweaker.Services;

namespace BestWinTweaker.Views;

public sealed partial class UwpPage : Page
{
    public UwpViewModel ViewModel { get; }

    public UwpPage()
    {
        this.InitializeComponent();
        var uwpService = App.GetService<UwpService>();
        ViewModel = new UwpViewModel(uwpService);
    }
}