using CommunityToolkit.Mvvm.ComponentModel;
using System;

namespace BestWinTweaker.Models;

public partial class StartupEntry : ObservableObject
{
    [ObservableProperty]
    private string _name = string.Empty;

    [ObservableProperty]
    private string _path = string.Empty;

    [ObservableProperty]
    private string _source = string.Empty;   // HKCU\Run, HKLM\Run, HKLM\Run (32-bit), Startup Folder

    [ObservableProperty]
    private bool _enabled;

    public string Type => Source switch
    {
        "Startup Folder" => "папка",
        "Планировщик" => "задача",
        _ => "реестр"
    };
}