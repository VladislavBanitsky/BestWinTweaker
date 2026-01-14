import webbrowser
import sys
import os

# Функция для корректного поиска файлов
def resource_path(relative_path):
	""" Получает абсолютный путь к ресурсу, работает для dev и для PyInstaller """
	if hasattr(sys, '_MEIPASS'):  # Если запущено из EXE
		base_path = sys._MEIPASS
	else:  # Если запущено из скрипта
		base_path = os.path.abspath(".")
	return os.path.join(base_path, relative_path)

# Функция для открытия ссылки в браузере
def callback(url):
    webbrowser.open_new(url)
    