using Microsoft.UI.Xaml.Controls;
using BestWinTweaker.ViewModels;
using BestWinTweaker.Services;

namespace BestWinTweaker.Views;

public sealed partial class ProcessesPage : Page
{
    public ProcessesViewModel ViewModel { get; }

    public ProcessesPage()
    {
        this.InitializeComponent();
        var processService = App.GetService<ProcessService>();
        ViewModel = new ProcessesViewModel(processService);
    }
}