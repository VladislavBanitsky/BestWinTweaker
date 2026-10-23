using System;

namespace BestWinTweaker.Models;

public class StartupBackupEntry
{
    public string Name { get; set; } = string.Empty;
    public string Path { get; set; } = string.Empty;
    public string Source { get; set; } = string.Empty;
    public DateTime DisabledAt { get; set; } = DateTime.Now;
}