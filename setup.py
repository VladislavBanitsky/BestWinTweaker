# setup.py
import PyInstaller.__main__
import os

from version import VERSION

# Название приложения
APP_NAME = "BestWinTweaker"

# Пути
SCRIPT_PATH = "start_app.py"
ICON_PATH = "./resources/images/BestWinTweaker.ico"

# Разбираем версию
version_parts = VERSION.split('.')
major = version_parts[0] if len(version_parts) > 0 else "0"
minor = version_parts[1] if len(version_parts) > 1 else "0"
patch = version_parts[2] if len(version_parts) > 2 else "0"
build = version_parts[3] if len(version_parts) > 3 else "0"


def create_version_file():
    """Создаёт файл версии для PyInstaller"""
    version_content = f'''# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'BestWinTweaker'),
        StringStruct(u'FileDescription', u'BestWinTweaker - Системный монитор и оптимизатор'),
        StringStruct(u'FileVersion', u'{VERSION}'),
        StringStruct(u'InternalName', u'BestWinTweaker'),
        StringStruct(u'LegalCopyright', u'Copyright © 2026'),
        StringStruct(u'OriginalFilename', u'BestWinTweaker.exe'),
        StringStruct(u'ProductName', u'BestWinTweaker'),
        StringStruct(u'ProductVersion', u'{VERSION}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    with open('version.txt', 'w', encoding='utf-8') as f:
        f.write(version_content)
    return 'version.txt'


version_file = create_version_file()

# Аргументы для PyInstaller
args = [
    SCRIPT_PATH,
    f"--name={APP_NAME}",
    "--onefile",
    "--windowed",
    "--noconsole",
    f"--icon={ICON_PATH}",
    f"--version-file={version_file}",
    "--add-data=./resources;./resources",

    # --- Скрытые импорты проекта ---
    "--hidden-import=start_app",
    "--hidden-import=splash_screen",
    "--hidden-import=data_loader",
    "--hidden-import=ConfigManager",
    "--hidden-import=StatusManager",
    "--hidden-import=TweakerTools",
    "--hidden-import=StartupManager",
    "--hidden-import=ProcessesManager",
    "--hidden-import=proc_colors",
    "--hidden-import=utilities",
    "--hidden-import=uwpremover",
    "--hidden-import=bing_wallpaper",
    "--hidden-import=BestWinTweaker",
    "--hidden-import=version",
    "--hidden-import=patch_subprocess",

    # --- Внешние зависимости ---
    "--hidden-import=GPUtil",
    "--hidden-import=cpuinfo",
    "--hidden-import=customtkinter",
    "--hidden-import=PIL",
    "--hidden-import=PIL.Image",
    "--hidden-import=PIL.ImageTk",
    "--hidden-import=winreg",
    "--hidden-import=psutil",
    "--hidden-import=platform",
    "--hidden-import=datetime",
    "--hidden-import=requests",
    "--hidden-import=wmi",
    "--hidden-import=pythoncom",
    "--hidden-import=pywin32",
    "--hidden-import=json",
    "--hidden-import=re",
    "--hidden-import=traceback",
    "--hidden-import=shutil",
    "--hidden-import=tempfile",
    "--hidden-import=webbrowser",
    "--hidden-import=threading",
    "--hidden-import=multiprocessing",
    "--hidden-import=ctypes",
    "--hidden-import=subprocess",
    "--hidden-import=concurrent.futures",
    "--hidden-import=BlurWindow",
    "--hidden-import=BlurWindow.blurWindow",

    # --- Сбор данных ---
    "--collect-data=customtkinter",
    "--collect-all=customtkinter",
    "--collect-all=tkinter",
    "--collect-all=PIL",
    "--collect-all=psutil",
    "--collect-all=wmi",
    "--collect-all=pywin32",
    "--collect-all=BlurWindow",

    "--uac-admin",
    "--clean",
    "--noconfirm",
]

try:
    PyInstaller.__main__.run(args)
    print("Сборка завершена!")
finally:
    if os.path.exists(version_file):
        os.remove(version_file)

input("Нажмите Enter, чтобы выйти...")