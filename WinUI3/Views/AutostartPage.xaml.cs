using Microsoft.UI.Xaml.Controls;
using BestWinTweaker.ViewModels;
using BestWinTweaker.Services;

namespace BestWinTweaker.Views;

public sealed partial class AutostartPage : Page
{
    public AutostartViewModel ViewModel { get; }

    public AutostartPage()
    {
        this.InitializeComponent();
        var service = App.GetService<StartupService>();
        ViewModel = new AutostartViewModel(service);
    }
}