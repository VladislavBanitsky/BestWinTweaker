# patch_subprocess.py
import subprocess
import os

# Сохраняем оригинальный Popen
_original_popen = subprocess.Popen

def _silent_popen(*args, **kwargs):
    """Глобально скрываем все консольные окна"""
    # Настройки для скрытия окон
    if 'startupinfo' not in kwargs:
        kwargs['startupinfo'] = subprocess.STARTUPINFO()
        kwargs['startupinfo'].dwFlags = subprocess.STARTF_USESHOWWINDOW
        kwargs['startupinfo'].wShowWindow = subprocess.SW_HIDE

    kwargs['creationflags'] = kwargs.get('creationflags', 0) | subprocess.CREATE_NO_WINDOW
    kwargs['stdin'] = subprocess.DEVNULL

    return _original_popen(*args, **kwargs)

# Применяем патч глобально
subprocess.Popen = _silent_popen