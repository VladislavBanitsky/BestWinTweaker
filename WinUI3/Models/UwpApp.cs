using CommunityToolkit.Mvvm.ComponentModel;

namespace BestWinTweaker.Models;

public partial class UwpApp : ObservableObject
{
    [ObservableProperty]
    private string _name = string.Empty;

    [ObservableProperty]
    private string _packageFullName = string.Empty;

    [ObservableProperty]
    private string _version = string.Empty;

    [ObservableProperty]
    private string _publisher = string.Empty;

    [ObservableProperty]
    private bool _isSafeToRemove;

    [ObservableProperty]
    private bool _isSelected;

    // Для отображения иконки (галочка или предупреждение)
    public string Icon => IsSafeToRemove ? "✅" : "⚠️";
    public string IconColor => IsSafeToRemove ? "Green" : "Orange";
}