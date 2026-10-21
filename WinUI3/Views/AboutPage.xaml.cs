using Microsoft.UI.Xaml.Controls;

namespace BestWinTweaker.Views;

public sealed partial class AboutPage : Page
{
    public AboutPage()
    {
        this.InitializeComponent();

        var version = typeof(AboutPage).Assembly.GetName().Version;
        VersionText.Text = $"Версия: {version?.Major}.{version?.Minor}.{version?.Build}";
    }
}