# silent_subprocess.py
import subprocess
import os

def patch_subprocess():
    """Патчит subprocess для скрытия всех окон"""
    
    # Сохраняем оригиналы
    _original_run = subprocess.run
    _original_popen = subprocess.Popen
    _original_call = subprocess.call
    _original_check_call = subprocess.check_call
    _original_check_output = subprocess.check_output
    
    def _silent_run(*args, **kwargs):
        kwargs.setdefault('startupinfo', subprocess.STARTUPINFO())
        kwargs['startupinfo'].dwFlags = subprocess.STARTF_USESHOWWINDOW
        kwargs['startupinfo'].wShowWindow = subprocess.SW_HIDE
        kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
        return _original_run(*args, **kwargs)
    
    def _silent_popen(*args, **kwargs):
        kwargs.setdefault('startupinfo', subprocess.STARTUPINFO())
        kwargs['startupinfo'].dwFlags = subprocess.STARTF_USESHOWWINDOW
        kwargs['startupinfo'].wShowWindow = subprocess.SW_HIDE
        kwargs['creationflags'] = kwargs.get('creationflags', 0) | subprocess.CREATE_NO_WINDOW
        kwargs.setdefault('stdin', subprocess.DEVNULL)
        return _original_popen(*args, **kwargs)
    
    def _silent_call(*args, **kwargs):
        kwargs.setdefault('startupinfo', subprocess.STARTUPINFO())
        kwargs['startupinfo'].dwFlags = subprocess.STARTF_USESHOWWINDOW
        kwargs['startupinfo'].wShowWindow = subprocess.SW_HIDE
        kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
        return _original_call(*args, **kwargs)
    
    def _silent_check_output(*args, **kwargs):
        kwargs.setdefault('startupinfo', subprocess.STARTUPINFO())
        kwargs['startupinfo'].dwFlags = subprocess.STARTF_USESHOWWINDOW
        kwargs['startupinfo'].wShowWindow = subprocess.SW_HIDE
        kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
        return _original_check_output(*args, **kwargs)
    
    # Применяем патчи
    subprocess.run = _silent_run
    subprocess.Popen = _silent_popen
    subprocess.call = _silent_call
    subprocess.check_output = _silent_check_output