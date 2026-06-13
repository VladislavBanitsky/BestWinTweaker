import PyInstaller.__main__
import os

# Название приложения
APP_NAME = "BestWinTweaker"

# Пути
SCRIPT_PATH = "start_app.py"
ICON_PATH = "./resources/images/BestWinTweaker.ico"

# Создаем файл версии
def create_version_file():
    version_content = f'''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be a tuple of integers (major, minor, build, private)
    filevers=(1, 9, 0, 0),
    prodvers=(1, 9, 0, 0),
    # Contains a bitmask that specifies the valid bits 'flags'
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    OS=0x40004,
    # The general type of file.
    fileType=0x1,
    # The function of the file.
    subtype=0x0,
    # The date and time stamp of the file.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'BestWinTweaker'),
        StringStruct(u'FileDescription', u'BestWinTweaker - Системный монитор и оптимизатор'),
        StringStruct(u'FileVersion', u'1.9.0.0'),
        StringStruct(u'InternalName', u'BestWinTweaker'),
        StringStruct(u'LegalCopyright', u'Copyright © 2026'),
        StringStruct(u'OriginalFilename', u'BestWinTweaker.exe'),
        StringStruct(u'ProductName', u'BestWinTweaker'),
        StringStruct(u'ProductVersion', u'1.9.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    with open('version.txt', 'w', encoding='utf-8') as f:
        f.write(version_content)
    return 'version.txt'

# Создаем файл версии
version_file = create_version_file()

# Аргументы для PyInstaller
args = [
    SCRIPT_PATH,
    f"--name={APP_NAME}",
    "--onefile",                    # Один exe файл
    "--windowed",                   # Без консольного окна
    "--noconsole",                  # Без консоли (дубль)
    f"--icon={ICON_PATH}",
    f"--version-file={version_file}",  # Файл с версией
    "--add-data=./resources;./resources",  # Добавляем папку с ресурсами
    "--hidden-import=GPUtil",
    "--hidden-import=cpuinfo",
    "--hidden-import=customtkinter",
    "--hidden-import=PIL",
    "--hidden-import=winreg",
    "--hidden-import=psutil",
    "--hidden-import=platform",
    "--hidden-import=datetime",
    "--hidden-import=requests",      # Добавлено для Fido
    "--hidden-import=fido_integration",  # Добавлено для Fido
    "--hidden-import=fido_gui",      # Добавлено для Fido
    "--collect-data=customtkinter",  # Собираем темы customtkinter
    "--uac-admin",                   # Запуск от администратора
    "--clean",                       # Очистка временных файлов
    "--noconfirm",                   # Не спрашивать подтверждение
]

# Запускаем PyInstaller
PyInstaller.__main__.run(args)

print("Сборка завершена!")
input("Нажмите Enter, чтобы выйти...")

# Удаляем временный файл версии
if os.path.exists(version_file):
    os.remove(version_file)