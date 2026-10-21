using BestWinTweaker.Models;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;

namespace BestWinTweaker.Services;

public class ProcessService
{
    private readonly Dictionary<int, TimeSpan> _lastCpuTimes = new();
    private DateTime _lastCheck = DateTime.Now;

    // Скрываем всегда (аналог ALWAYS_HIDDEN)
    private static readonly HashSet<string> AlwaysHidden = new(StringComparer.OrdinalIgnoreCase)
    {
        "Idle", "System", "Memory Compression", "Registry"
    };

    // Системные процессы (скрываются, если не включён чекбокс)
    private static readonly HashSet<string> SystemNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "smss", "csrss", "wininit", "winlogon", "services", "lsass",
        "dwm", "fontdrvhost", "svchost", "sihost", "taskhostw",
        "runtimebroker", "searchindexer", "spoolsv"
    };

    public List<ProcessInfo> GetProcesses(bool showSystem = false)
    {
        var result = new List<ProcessInfo>();
        var now = DateTime.Now;
        var elapsed = (now - _lastCheck).TotalMilliseconds;
        if (elapsed <= 0) elapsed = 100;

        var processes = Process.GetProcesses();

        foreach (var p in processes)
        {
            try
            {
                var name = p.ProcessName;
                if (AlwaysHidden.Contains(name)) continue;
                if (!showSystem && SystemNames.Contains(name)) continue;

                double cpuPercent = 0;
                try
                {
                    var cpuTime = p.TotalProcessorTime;
                    if (_lastCpuTimes.TryGetValue(p.Id, out var lastTime))
                    {
                        var deltaMs = (cpuTime - lastTime).TotalMilliseconds;
                        cpuPercent = Math.Round(deltaMs / elapsed / Environment.ProcessorCount * 100, 1);
                    }
                    _lastCpuTimes[p.Id] = cpuTime;
                }
                catch { /* недоступно */ }

                double memMb = 0;
                try { memMb = Math.Round(p.WorkingSet64 / 1024.0 / 1024.0, 1); }
                catch { }

                // Процент памяти от общего объёма (приблизительно)
                double memPercent = 0;
                try
                {
                    var totalMem = GC.GetGCMemoryInfo().TotalAvailableMemoryBytes;
                    if (totalMem > 0) memPercent = Math.Round(memMb * 1024 * 1024 / (double)totalMem * 100, 1);
                }
                catch { }

                string status = "Running";
                string statusText = "Работает";
                string statusColor = "#4cd964";
                try
                {
                    if (!p.Responding)
                    {
                        status = "NotResponding";
                        statusText = "Не отвечает";
                        statusColor = "#ff9933";
                    }
                }
                catch { }

                result.Add(new ProcessInfo
                {
                    Pid = p.Id,
                    Name = name,
                    CpuPercent = cpuPercent,
                    MemoryPercent = memPercent,
                    MemoryMb = memMb,
                    Status = status,
                    StatusText = statusText,
                    StatusColor = statusColor
                });
            }
            catch (Exception) { /* игнорируем недоступные процессы */ }
            finally { p.Dispose(); }
        }

        _lastCheck = now;
        return result.OrderByDescending(x => x.CpuPercent).ToList();
    }

    public bool KillProcess(int pid)
    {
        try
        {
            using var p = Process.GetProcessById(pid);
            p.Kill(); // Принудительное завершение [citation:3]
            p.WaitForExit(3000);
            return true;
        }
        catch { return false; }
    }
}