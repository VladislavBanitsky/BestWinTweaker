using BestWinTweaker.Models;
using LibreHardwareMonitor.Hardware;
using System;
using System.Collections.Generic;

namespace BestWinTweaker.Services;

public class HardwareSensorService : IDisposable
{
    private readonly Computer _computer;
    private readonly UpdateVisitor _visitor;

    public HardwareSensorService()
    {
        _computer = new Computer
        {
            IsCpuEnabled = true,
            IsGpuEnabled = true,
            IsMemoryEnabled = false, // RAM берём через GlobalMemoryStatusEx
            IsStorageEnabled = false // Диски берём через DriveInfo
        };
        _computer.Open();
        _visitor = new UpdateVisitor();
    }

    public CpuTemperatureInfo GetCpuTemperatures()
    {
        var result = new CpuTemperatureInfo();
        _computer.Accept(_visitor);

        foreach (var hardware in _computer.Hardware)
        {
            if (hardware.HardwareType != HardwareType.Cpu) continue;

            foreach (var sensor in hardware.Sensors)
            {
                if (sensor.SensorType != SensorType.Temperature || sensor.Value == null) continue;

                var name = sensor.Name;
                var value = sensor.Value.Value;

                if (name.Contains("Package", StringComparison.OrdinalIgnoreCase))
                    result.PackageTempC = Math.Round(value, 1);
                else if (name.Contains("Core Max", StringComparison.OrdinalIgnoreCase) ||
                         name.Contains("CPU Core Max", StringComparison.OrdinalIgnoreCase))
                    result.MaxCoreTempC = Math.Round(value, 1);
            }
        }
        return result;
    }

    public List<GpuInfo> GetGpus()
    {
        var result = new List<GpuInfo>();
        _computer.Accept(_visitor);

        foreach (var hardware in _computer.Hardware)
        {
            // Поддерживаем NVIDIA, AMD и Intel GPU
            if (hardware.HardwareType != HardwareType.GpuNvidia &&
                hardware.HardwareType != HardwareType.GpuAmd &&
                hardware.HardwareType != HardwareType.GpuIntel)
                continue;

            var gpu = new GpuInfo { Name = hardware.Name };

            foreach (var sensor in hardware.Sensors)
            {
                if (sensor.Value == null) continue;
                var value = sensor.Value.Value;

                switch (sensor.SensorType)
                {
                    case SensorType.Load when sensor.Name.Contains("GPU Core", StringComparison.OrdinalIgnoreCase):
                        gpu.LoadPercent = Math.Round(value, 1);
                        break;
                    case SensorType.Temperature when sensor.Name.Contains("GPU Core", StringComparison.OrdinalIgnoreCase):
                        gpu.TemperatureC = Math.Round(value, 1);
                        break;
                    case SensorType.SmallData when sensor.Name.Contains("GPU Memory Used", StringComparison.OrdinalIgnoreCase):
                        gpu.MemoryUsedMb = Math.Round(value, 0);
                        break;
                    case SensorType.SmallData when sensor.Name.Contains("GPU Memory Total", StringComparison.OrdinalIgnoreCase):
                        gpu.MemoryTotalMb = Math.Round(value, 0);
                        break;
                }
            }

            if (gpu.MemoryTotalMb > 0)
                gpu.MemoryPercent = Math.Round(gpu.MemoryUsedMb / gpu.MemoryTotalMb * 100, 1);

            result.Add(gpu);
        }
        return result;
    }

    public void Dispose()
    {
        _computer.Close();
    }

    // Обязательный визитор для обновления сенсоров
    private class UpdateVisitor : IVisitor
    {
        public void VisitComputer(IComputer computer) => computer.Traverse(this);
        public void VisitHardware(IHardware hardware)
        {
            hardware.Update();
            foreach (var sub in hardware.SubHardware) sub.Accept(this);
        }
        public void VisitSensor(ISensor sensor) { }
        public void VisitParameter(IParameter parameter) { }
    }
}