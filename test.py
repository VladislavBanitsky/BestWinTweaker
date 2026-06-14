"""
Идентификация DDR оперативной памяти на Windows и Linux.
Определяет тип памяти (DDR3, DDR4, DDR5), объем, частоту и производителя.
"""

import platform
import struct

# -----------------------------------------------------------------------------
# Windows реализация (через WMI)
# -----------------------------------------------------------------------------
if platform.system() == "Windows":
    try:
        import winreg
        import wmi

        def get_ddr_info_windows():
            """
            Получает информацию о модулях памяти через WMI на Windows.
            Возвращает список словарей с данными о каждом модуле.
            """
            c = wmi.WMI()
            memory_modules = []

            # Значения идентификации типа памяти из Win32_PhysicalMemory
            memory_type_map = {
                0: "Unknown",
                1: "Other",
                2: "DRAM",
                3: "Synchronous DRAM",
                4: "Cache DRAM",
                5: "EDO",
                6: "EDRAM",
                7: "VRAM",
                8: "SRAM",
                9: "RAM",
                10: "ROM",
                11: "Flash",
                12: "EEPROM",
                13: "FEPROM",
                14: "EPROM",
                15: "CDRAM",
                16: "3DRAM",
                17: "SDRAM",
                18: "SGRAM",
                19: "RDRAM",
                20: "DDR",        # DDR (DDR1)
                21: "DDR2",
                22: "DDR2 FB-DIMM",
                24: "DDR3",       # DDR3
                25: "FBD2",
                26: "DDR4",       # DDR4
                27: "LPDDR",
                28: "LPDDR2",
                29: "LPDDR3",
                30: "LPDDR4",
                31: "DDR5",       # DDR5 (современные системы)
            }

            for mem in c.Win32_PhysicalMemory():
                mem_type = memory_type_map.get(mem.MemoryType, "Unknown")
                capacity_bytes = getattr(mem, 'Capacity', 0)
                if capacity_bytes:
                    capacity_gb = int(capacity_bytes) / (1024 ** 3)
                else:
                    capacity_gb = 0

                speed = getattr(mem, 'Speed', None)
                manufacturer = getattr(mem, 'Manufacturer', 'Unknown')
                part_number = getattr(mem, 'PartNumber', 'Unknown')
                bank_label = getattr(mem, 'BankLabel', 'Unknown')
                device_locator = getattr(mem, 'DeviceLocator', 'Unknown')

                memory_modules.append({
                    "type": mem_type,
                    "capacity_gb": capacity_gb,
                    "speed_mhz": speed if speed and speed > 0 else None,
                    "manufacturer": manufacturer.strip() if manufacturer else "Unknown",
                    "part_number": part_number.strip() if part_number else "Unknown",
                    "bank": bank_label,
                    "slot": device_locator,
                })
            return memory_modules

        def identify_ddr():
            """Основная функция для Windows."""
            modules = get_ddr_info_windows()
            return modules

    except ImportError:
        print("Ошибка: Установите библиотеку wmi: pip install wmi")
        print("Для работы также требуется pywin32")
        exit(1)

# -----------------------------------------------------------------------------
# Linux реализация (через SPD EEPROM)
# -----------------------------------------------------------------------------
elif platform.system() == "Linux":
    import os
    import glob

    # Типы устройств DRAM из спецификации SPD (байт 2)
    # на основе JEDEC Standard [citation:1]
    DRAM_DEVICE_TYPE = {
        0x0c: "DDR4 SDRAM",      # JEDEC 21-C Annex L [citation:1]
        0x10: "LPDDR4 SDRAM",
        0x11: "LPDDR4X SDRAM",
        0x12: "DDR5 SDRAM",      # Добавлено для DDR5
        0x13: "LPDDR5 SDRAM",
    }

    # Производители из JEDEC JEP106 (неполный список, только популярные) [citation:1]
    JEP106_MANUFACTURERS = {
        1: {  # Bank 1
            0x2c: "Micron",
            0xad: "SK Hynix",
            0xce: "Samsung",
        },
        2: {  # Bank 2
            0x98: "Kingston",
        },
        3: {  # Bank 3
            0x9e: "Corsair",
        },
        5: {  # Bank 5
            0xcd: "G.SKILL",
            0xef: "Team Group",
        },
        6: {  # Bank 6
            0x02: "Patriot",
            0x9b: "Crucial",
        },
    }

    def read_spd_eeprom(device_path):
        """Читает 512 байт SPD EEPROM по указанному пути /dev/i2c-X."""
        try:
            with open(device_path, 'rb') as f:
                # SPD EEPROM обычно имеет адрес 0x50, емкость 256/512 байт
                # Пытаемся прочитать 512 байт (DDR4 SPD размер)
                data = f.read(512)
                if len(data) < 128:  # Минимальный размер SPD
                    return None
                return data
        except (IOError, OSError, PermissionError):
            return None

    def parse_ddr4_spd(spd_data):
        """
        Парсит SPD данные для DDR4 [citation:1].
        Возвращает словарь с информацией о модуле.
        """
        info = {}

        # Байт 0: количество использованных байт SPD и общее количество
        spd_bytes_used_nibble = spd_data[0] & 0x0f
        spd_bytes_total_nibble = (spd_data[0] >> 4) & 0b0111
        info['spd_size'] = spd_bytes_used_nibble * 128
        info['total_size'] = spd_bytes_total_nibble * 256 if spd_bytes_total_nibble <= 2 else None

        # Байт 2: Тип DRAM устройства [citation:1]
        dram_type_byte = spd_data[2]
        info['type'] = DRAM_DEVICE_TYPE.get(dram_type_byte, f"Unknown (0x{dram_type_byte:02x})")

        # Байт 3: Тип модуля (младшие 4 бита) [citation:1]
        base_module_type = spd_data[3] & 0x0f
        module_types = {
            0b0001: "RDIMM",
            0b0010: "UDIMM",
            0b0011: "SO-DIMM",
            0b0100: "LRDIMM",
            0b0101: "Mini-RDIMM",
            0b0110: "Mini-UDIMM",
        }
        info['form_factor'] = module_types.get(base_module_type, f"Type {base_module_type}")

        # Байт 12-13: Емкость модуля (DDR4 специфично)
        # Код для конфигурации емкости (байты 4 и 12 содержат информацию о плотности)
        density_bits = spd_data[4] & 0x0f
        if density_bits == 0x04:
            info['capacity_gb'] = 4
        elif density_bits == 0x05:
            info['capacity_gb'] = 8
        elif density_bits == 0x06:
            info['capacity_gb'] = 16
        elif density_bits == 0x07:
            info['capacity_gb'] = 32
        else:
            info['capacity_gb'] = None

        # Байт 16: Номинальная скорость (tCK min) в ps -> МГц
        tck_min_ps = spd_data[16]
        if tck_min_ps > 0:
            # Скорость MT/s = 2000 / (tCK_min_ps / 1000) = 2,000,000 / tCK_min_ps
            mt_s = int(2000000 / tck_min_ps)
            info['speed_mhz'] = mt_s
        else:
            info['speed_mhz'] = None

        # Байты 320-321: Производитель модуля (JEDEC ID) [citation:1]
        # Только для SPD ревизии >= 1.0
        if len(spd_data) > 321:
            bank = 1 + (spd_data[320] & 0x7f)
            manuf_id = spd_data[321]
            if bank in JEP106_MANUFACTURERS and manuf_id in JEP106_MANUFACTURERS[bank]:
                info['manufacturer'] = JEP106_MANUFACTURERS[bank][manuf_id]
            else:
                info['manufacturer'] = f"Unknown (Bank {bank}, ID 0x{manuf_id:02x})"
        else:
            info['manufacturer'] = "Unknown"

        # Байты 329-348: Номер партии (ASCII, 20 байт) [citation:1]
        if len(spd_data) > 348:
            part_number_raw = spd_data[329:349]
            part_number = part_number_raw.split(b'\x00')[0].decode('ascii', errors='ignore')
            info['part_number'] = part_number.strip()
        else:
            info['part_number'] = "Unknown"

        return info

    def identify_ddr():
        """
        Основная функция для Linux: поиск SPD EEPROM и чтение информации.
        """
        # Ищем устройства I2C, которые могут содержать SPD EEPROM (обычно адрес 0x50)
        # SPD EEPROM подключаются к шине SMBus/i2c материнской платы
        i2c_devices = glob.glob('/dev/i2c-*')

        if not i2c_devices:
            print("Предупреждение: I2C устройства не найдены.")
            print("Убедитесь, что загружены модули ядра: i2c_dev, i2c_piix4 или i801_smbus")
            return []

        modules_info = []

        for dev_path in sorted(i2c_devices):
            # Адрес SPD EEPROM обычно 0x50, 0x51, 0x52, 0x53 (для каждого канала)
            for addr in [0x50, 0x51, 0x52, 0x53]:
                # Для Linux адрес указывается через функцию i2cset, но в sysfs мы не можем
                # напрямую задать адрес при открытии файла. Используем ioctl через smbus.
                # Альтернатива: использовать библиотеку smbus2
                try:
                    import smbus2
                    bus = smbus2.SMBus(int(dev_path.split('-')[-1]))
                    # Пытаемся прочитать SPD данные (256 байт)
                    spd_bytes = bus.read_i2c_block_data(addr, 0, 256)
                    if spd_bytes and len(spd_bytes) >= 128:
                        # Проверяем, что это валидный SPD
                        if spd_bytes[2] in DRAM_DEVICE_TYPE:
                            info = parse_ddr4_spd(spd_bytes)
                            info['slot'] = f"DIMM {addr - 0x50 + 1}"
                            info['bus'] = dev_path
                            modules_info.append(info)
                except (ImportError, FileNotFoundError, OSError, IOError):
                    continue
                except Exception:
                    continue

        if not modules_info:
            print("Не удалось прочитать SPD данные.")
            print("Возможные причины:")
            print("  - Установите smbus2: pip install smbus2")
            print("  - Запустите скрипт с sudo (требуются права root для доступа к I2C)")
            print("  - Убедитесь, что модули ядра загружены: modprobe i2c-dev i2c-piix4")

        return modules_info

# -----------------------------------------------------------------------------
# Другая ОС
# -----------------------------------------------------------------------------
else:
    def identify_ddr():
        print(f"OS {platform.system()} не поддерживается напрямую.")
        print("Попробуйте использовать системные утилиты: dmidecode (Linux) или WMIC (Windows)")
        return []

# -----------------------------------------------------------------------------
# Основная функция для вывода информации
# -----------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("Идентификация DDR оперативной памяти")
    print("=" * 60)

    modules = identify_ddr()

    if not modules:
        print("\nМодули памяти не обнаружены.")
        return

    for i, module in enumerate(modules, 1):
        print(f"\n--- Модуль {i} ---")
        for key, value in module.items():
            if value is not None and value != 0:
                if key == 'capacity_gb' and isinstance(value, (int, float)):
                    print(f"{key}: {value:.1f} GB")
                elif key == 'speed_mhz' and value:
                    print(f"{key}: {value} MT/s")
                else:
                    print(f"{key}: {value}")

if __name__ == "__main__":
    main()