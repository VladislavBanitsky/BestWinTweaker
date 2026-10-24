using Windows.ApplicationModel.DataTransfer;

namespace BestWinTweaker.Helpers;

public static class ClipboardHelper
{
    public static void CopyToClipboard(string text)
    {
        if (string.IsNullOrEmpty(text)) return;
        var dataPackage = new DataPackage();
        dataPackage.SetText(text);
        Clipboard.SetContent(dataPackage);
    }
}