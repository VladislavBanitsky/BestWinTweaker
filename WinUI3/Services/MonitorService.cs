using BestWinTweaker.Models;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Management;
using System.Net.NetworkInformation;
using System.Threading;

namespace BestWinTweaker.Services;

public class MonitorService
{
    private PerformanceCounter? _cpuCounter;
    private PerformanceCounter? _ramCounter;

    // Поля для расчета скорости сети
    private long _prevBytesReceived = 0;
    private long _prevBytesSent = 0;
    private DateTime _prevNetTime = DateTime.MinValue;

    public MonitorService()
    {
        try
        {
            _cpuCounter = new PerformanceCounter("Processor", "% Processor Time", "_Total");
            _ramCounter = new PerformanceCounter("Memory", "Available MBytes");
            // Первый вызов NextValue() всегда возвращает 0 — «прогреваем» счётчики.
            _cpuCounter.NextValue();
            _ramCounter.NextValue();

            // Ждем 100 мс, чтобы счетчик успел собрать данные
            Thread.Sleep(100);
        }
        catch
        {
            // Счётчики могут быть недоступны в некоторых окружениях.
            _cpuCounter = null;
            _ramCounter = null;
        }
    }

    public CpuInfo GetCpuInfo()
    {
        var info = new CpuInfo
        {
            Name = GetCpuName(),
            LogicalCores = GetLogicalCoreCount(),
            PhysicalCores = GetPhysicalCoreCount()
        };

        try
        {
            if (_cpuCounter != null)
                info.UsagePercent = Math.Round(_cpuCounter.NextValue(), 1);

            // Частота через WMI (простой способ без сторонних библиотек).
            info.FrequencyMhz = GetCpuFrequency();
        }
        catch { /* игнорируем */ }

        return info;
    }

    public RamInfo GetRamInfo()
    {
        var info = new RamInfo();
        try
        {
            // Используем GlobalMemoryStatusEx для получения общего объёма.
            var memStatus = new MEMORYSTATUSEX();
            memStatus.dwLength = (uint)System.Runtime.InteropServices.Marshal.SizeOf(memStatus);
            if (GlobalMemoryStatusEx(ref memStatus))
            {
                info.TotalGb = Math.Round(memStatus.ullTotalPhys / 1024.0 / 1024.0 / 1024.0, 1);
                var usedBytes = memStatus.ullTotalPhys - memStatus.ullAvailPhys;
                info.UsedGb = Math.Round(usedBytes / 1024.0 / 1024.0 / 1024.0, 1);
                info.Percent = info.TotalGb > 0
                    ? Math.Round(info.UsedGb / info.TotalGb * 100, 1)
                    : 0;
            }
        }
        catch { /* игнорируем */ }
        return info;
    }

    public List<DiskInfo> GetDisks()
    {
        var list = new List<DiskInfo>();
        try
        {
            foreach (var drive in DriveInfo.GetDrives())
            {
                if (drive.DriveType != DriveType.Fixed || !drive.IsReady)
                    continue;

                var totalGb = Math.Round(drive.TotalSize / 1024.0 / 1024.0 / 1024.0, 1);
                var freeGb = Math.Round(drive.AvailableFreeSpace / 1024.0 / 1024.0 / 1024.0, 1);
                var usedGb = Math.Round(totalGb - freeGb, 1);
                var percent = totalGb > 0 ? Math.Round(usedGb / totalGb * 100, 1) : 0;

                list.Add(new DiskInfo
                {
                    Device = drive.Name.TrimEnd('\\'),
                    MountPoint = drive.RootDirectory.FullName,
                    TotalGb = totalGb,
                    UsedGb = usedGb,
                    Percent = percent,
                    DiskType = GetDiskType(drive.Name)
                });
            }
        }
        catch { /* игнорируем */ }
        return list;
    }

    // ---- Вспомогательные методы ----

    private static string GetCpuName()
    {
        try
        {
            using var key = Microsoft.Win32.Registry.LocalMachine.OpenSubKey(
                @"HARDWARE\DESCRIPTION\System\CentralProcessor\0");
            return key?.GetValue("ProcessorNameString")?.ToString()?.Trim() ?? "Unknown CPU";
        }
        catch { return "Unknown CPU"; }
    }

    private static int GetPhysicalCoreCount()
    {
        try
        {
            using var searcher = new System.Management.ManagementObjectSearcher(
                "SELECT NumberOfCores FROM Win32_Processor");

            int total = 0;
            foreach (var obj in searcher.Get())
            {
                total += Convert.ToInt32(obj["NumberOfCores"]);
            }

            // Если WMI вернул 0 (например, на виртуалке), возвращаем приближение
            return total > 0 ? total : (Environment.ProcessorCount / 2 > 0 ? Environment.ProcessorCount / 2 : 1);
        }
        catch
        {
            // Fallback, если WMI недоступен
            return Environment.ProcessorCount / 2 > 0 ? Environment.ProcessorCount / 2 : 1;
        }
    }

    private static int GetLogicalCoreCount()
    {
        try
        {
            using var searcher = new System.Management.ManagementObjectSearcher(
                "SELECT NumberOfLogicalProcessors FROM Win32_Processor");

            int total = 0;
            foreach (var obj in searcher.Get())
            {
                total += Convert.ToInt32(obj["NumberOfLogicalProcessors"]);
            }

            return total > 0 ? total : Environment.ProcessorCount;
        }
        catch
        {
            return Environment.ProcessorCount;
        }
    }

    private static double GetCpuFrequency()
    {
        try
        {
            using var key = Microsoft.Win32.Registry.LocalMachine.OpenSubKey(
                @"HARDWARE\DESCRIPTION\System\CentralProcessor\0");
            var mhz = key?.GetValue("~MHz");
            if (mhz != null) return Convert.ToDouble(mhz);
        }
        catch { }
        return 0;
    }

    private static string GetDiskType(string driveLetter)
    {
        // Упрощённо: определяем SSD/HDD через PowerShell (можно заменить на WMI).
        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = "powershell",
                Arguments = $"-Command \"(Get-PhysicalDisk | Where-Object {{$_.DeviceId -eq (Get-Partition -DriveLetter {driveLetter[0]} | Get-Disk).Number}}).MediaType\"",
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            using var p = Process.Start(psi);
            if (p != null)
            {
                var output = p.StandardOutput.ReadToEnd().Trim();
                p.WaitForExit(2000);
                if (!string.IsNullOrEmpty(output))
                    return output;
            }
        }
        catch { }
        return "Unknown";
    }

    public string GetBoardModel()
    {
        try
        {
            using var searcher = new System.Management.ManagementObjectSearcher("SELECT * FROM Win32_BaseBoard");
            foreach (System.Management.ManagementObject obj in searcher.Get())
            {
                return $"{obj["Manufacturer"]} {obj["Product"]}";
            }
        }
        catch { }
        return "Неизвестно";
    }

    public (string adapter, string download, string upload, string totalDownload, string totalUpload) GetNetworkInfo()
    {
        try
        {
            // 1. Получаем имя адаптера через WMI
            string adapterName = "Не найдено";
            try
            {
                using var searcher = new ManagementObjectSearcher(
                    "SELECT * FROM Win32_NetworkAdapter WHERE NetEnabled=True AND PhysicalAdapter=True");
                foreach (var obj in searcher.Get())
                {
                    adapterName = obj["Name"]?.ToString() ?? "Не найдено";
                    break;
                }
            }
            catch { }

            // 2. Ищем активный интерфейс для статистики.
            // ВАЖНО: отсекаем виртуальные адаптеры (Loopback, Tunnel, и т.д.)
            var activeInterface = NetworkInterface.GetAllNetworkInterfaces()
                .Where(n => n.OperationalStatus == OperationalStatus.Up
                         && n.NetworkInterfaceType != NetworkInterfaceType.Loopback
                         && n.NetworkInterfaceType != NetworkInterfaceType.Tunnel
                         && !n.Description.Contains("Virtual", StringComparison.OrdinalIgnoreCase)
                         && !n.Description.Contains("Hyper-V", StringComparison.OrdinalIgnoreCase)
                         && !n.Description.Contains("VPN", StringComparison.OrdinalIgnoreCase))
                .OrderByDescending(n => n.GetIPStatistics().BytesReceived)
                .FirstOrDefault();

            if (activeInterface == null)
                return (adapterName, "0.00", "0.00", "0.00", "0.00");

            var stats = activeInterface.GetIPStatistics();
            var now = DateTime.Now;
            var timeDiff = (now - _prevNetTime).TotalSeconds;

            double downloadSpeed = 0;
            double uploadSpeed = 0;

            // Считаем скорость только если прошел хотя бы 1 тик и есть предыдущие данные
            if (_prevNetTime != DateTime.MinValue && timeDiff > 0.1)
            {
                downloadSpeed = (stats.BytesReceived - _prevBytesReceived) / timeDiff / (1024.0 * 1024.0);
                uploadSpeed = (stats.BytesSent - _prevBytesSent) / timeDiff / (1024.0 * 1024.0);
            }

            // Сохраняем текущие значения для следующего вызова
            _prevBytesReceived = stats.BytesReceived;
            _prevBytesSent = stats.BytesSent;
            _prevNetTime = now;

            // Общий трафик в гигабайтах
            double totalDownload = stats.BytesReceived / (1024.0 * 1024.0 * 1024.0);
            double totalUpload = stats.BytesSent / (1024.0 * 1024.0 * 1024.0);

            return (adapterName,
                    downloadSpeed.ToString("F2"),
                    uploadSpeed.ToString("F2"),
                    totalDownload.ToString("F2"),
                    totalUpload.ToString("F2"));
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[Сеть] Ошибка: {ex.Message}");
            return ("Ошибка", "0.00", "0.00", "0.00", "0.00");
        }
    }

    // ---- P/Invoke для памяти ----

    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
    private struct MEMORYSTATUSEX
    {
        public uint dwLength;
        public uint dwMemoryLoad;
        public ulong ullTotalPhys;
        public ulong ullAvailPhys;
        public ulong ullTotalPageFile;
        public ulong ullAvailPageFile;
        public ulong ullTotalVirtual;
        public ulong ullAvailVirtual;
        public ulong ullAvailExtendedVirtual;
    }

    [System.Runtime.InteropServices.DllImport("kernel32.dll", SetLastError = true)]
    [return: System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.Bool)]
    private static extern bool GlobalMemoryStatusEx(ref MEMORYSTATUSEX lpBuffer);
}