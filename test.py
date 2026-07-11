# check_registry.py
import winreg

HKEY_CURRENT_USER = winreg.HKEY_CURRENT_USER
HKEY_LOCAL_MACHINE = winreg.HKEY_LOCAL_MACHINE
REG_PATH_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"

def check_registry(hkey, path):
    print(f"\n=== Проверка {path} ===")
    try:
        key = winreg.OpenKey(hkey, path, 0, winreg.KEY_READ)
        i = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, i)
                print(f"  {name}: '{value}'")
                if value and value.strip():
                    print(f"    -> ВКЛЮЧЕНА (путь не пустой)")
                else:
                    print(f"    -> ОТКЛЮЧЕНА (путь пустой)")
                i += 1
            except WindowsError:
                break
        winreg.CloseKey(key)
    except WindowsError as e:
        print(f"  Ошибка: {e}")

# Проверяем все ветки
print("=" * 50)
print("ПРОВЕРКА РЕЕСТРА АВТОЗАГРУЗКИ")
print("=" * 50)

check_registry(HKEY_CURRENT_USER, REG_PATH_RUN)
check_registry(HKEY_LOCAL_MACHINE, REG_PATH_RUN)

# Проверяем 32-bit ветку
try:
    check_registry(HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run")
except:
    pass

print("\n" + "=" * 50)