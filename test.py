import subprocess
import time
import pyperclip  # pip install pyperclip

# Копируем команду в буфер обмена
pyperclip.copy('irm https://get.activated.win | iex')

# Открываем PowerShell
subprocess.Popen(["powershell.exe", "-NoExit"])
time.sleep(1.5)

# Пользователь должен нажать Ctrl+V сам или вы можете использовать pyautogui
# Для автоматической вставки:
import pyautogui
pyautogui.hotkey('ctrl', 'v')  # вставляет команду, но без Enter

print("Команда скопирована и вставлена. Нажмите Enter в PowerShell для выполнения.")