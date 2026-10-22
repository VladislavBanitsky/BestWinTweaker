namespace BestWinTweaker.Models;

public class DiskInfo
{
    public string Device { get; set; } = string.Empty;
    public string MountPoint { get; set; } = string.Empty;
    public double UsedGb { get; set; }
    public double TotalGb { get; set; }
    public double Percent { get; set; }
    public string DiskType { get; set; } = string.Empty;
    public string Model { get; set; } = string.Empty;
}

public class CpuInfo
{
    public string Name { get; set; } = string.Empty;
    public double UsagePercent { get; set; }
    public double FrequencyMhz { get; set; }
    public int LogicalCores { get; set; }
    public int PhysicalCores { get; set; }
}

public class RamInfo
{
    public double UsedGb { get; set; }
    public double TotalGb { get; set; }
    public double Percent { get; set; }
}

public class GpuInfo
{
    public string Name { get; set; } = string.Empty;
    public double LoadPercent { get; set; }
    public double TemperatureC { get; set; }
    public double MemoryUsedMb { get; set; }
    public double MemoryTotalMb { get; set; }
    public double MemoryPercent { get; set; }
}

public class CpuTemperatureInfo
{
    public double PackageTempC { get; set; }
    public double MaxCoreTempC { get; set; }
}