# ==============================================================================================
# Простое оконное приложение для оптимизации ПК.
# Почистите мусор в системных папках, отключите службы телеметрии, сбросьте DNS, 
# исправьте ошибки центра обновлений Windows или отключите индексацию на медленном HDD.
# Ускорение ПК в пару кликов!
# GitHub: https://github.com/VladislavBanitsky/BestWinTweaker
# Разработчик: Владислав Баницкий
# Версия: 0.0.3
# Обновлено: 14.01.2026  
# ==============================================================================================

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import shutil
from PIL import Image, ImageTk
from utilities import *

VERSION = "0.0.3"
WIDTH = 300
HEIGHT = 250

class WindowsTweaker:
    def __init__(self, root):
        self.root = root
        self.root.title("BestWinTweaker")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)
        self.root.iconbitmap(resource_path('./resources/images/BestWinTweaker.ico'))
                
        # Основные кнопки-действия
        buttons_frame = ttk.Frame(self.root)
        buttons_frame.pack(pady=10, padx=20, fill="x")       
        
        self.clear_button = ttk.Button(
            buttons_frame,
            text="Очистить временные файлы",
            command=self.clear_temp,
            width=40
        )
        self.clear_button.grid(row=0, column=0, pady=5, padx=5)
        
        # Привязываем события
        self.clear_button.bind("<Enter>", lambda event: self.status_var.set("Очистка папок temp, SoftwareDistribution и Prefetch"))
        self.clear_button.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        
        self.button_disable_services = ttk.Button(
            buttons_frame,
            text="Отключить службы телеметрии",
            command=self.disable_services,
            width=40
        )
        self.button_disable_services.grid(row=2, column=0, pady=5)
        
        # Привязываем события
        self.button_disable_services.bind("<Enter>", lambda event: self.status_var.set("Отключение служб DiagTrack и dmwappushservice"))
        self.button_disable_services.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        
        self.button_flush_dns = ttk.Button(
            buttons_frame,
            text="Очистить DNS",
            command=self.flush_dns,
            width=40
        )
        self.button_flush_dns.grid(row=3, column=0, pady=5)
        
        # Привязываем события
        self.button_flush_dns.bind("<Enter>", lambda event: self.status_var.set("Исправление проблем с доступом к сайтам"))
        self.button_flush_dns.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        
        self.fix_updates_button = ttk.Button(
            buttons_frame,
            text="Исправить ошибки обновлений",
            command=self.fix_updates,
            width=40
        )
        self.fix_updates_button.grid(row=4, column=0, pady=5)
        
        # Привязываем события
        self.fix_updates_button.bind("<Enter>", lambda event: self.status_var.set("Исправление ошибок Центра обновлений"))
        self.fix_updates_button.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        
        if self.is_indexing_enabled():
            self.disable_indexing_button = ttk.Button(
                buttons_frame,
                text="Отключить индексацию",
                command=self.disable_indexing,
                width=40
            )
            self.disable_indexing_button.grid(row=5, column=0, pady=5)
            
            # Привязываем события
            self.disable_indexing_button.bind("<Enter>", lambda event: self.status_var.set("Снижение нагрузки на HDD/SSD"))
            self.disable_indexing_button.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        else:
            self.enable_indexing_button = ttk.Button(
                buttons_frame,
                text="Включить индексацию",
                command=self.enable_indexing,
                width=40
            )
            self.enable_indexing_button.grid(row=5, column=0, pady=5)
            
            # Привязываем события
            self.enable_indexing_button.bind("<Enter>", lambda event: self.status_var.set("Включает поиск по содержимому файлов, именам и метаданным"))
            self.enable_indexing_button.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        
        self.about = ttk.Button(
            buttons_frame,
            text="О программе",
            command=self.about,
            width=40
        )
        self.about.grid(row=6, column=0, pady=5)
        
        # Привязываем события
        self.about.bind("<Enter>", lambda event: self.status_var.set("Сведения о программе :)"))
        self.about.bind("<Leave>", lambda event: self.status_var.set("Готов"))
        
        # Статус-бар
        self.status_var = tk.StringVar()
        self.status_var.set("Готов")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief="flat",
            anchor="center",
            font=("TkDefaultFont", 9),
            background = "#00f000"
        )
        status_bar.pack(side="bottom", fill="x")
        
    
    def run_cmd(self, cmd):
        """Выполнить командную строку и вернуть результат"""
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                check=True,
                encoding='cp866'
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"!Ошибка: {e}"

    def clear_temp(self, msg=True):
        """Очистить временные файлы Windows"""
        try:
            temp_dirs = [
                os.environ.get('TEMP'),
                os.environ.get('TMP'),
                r"C:\Windows\Temp",
                r"C:\Windows\SoftwareDistribution\Download",
                r"C:\Windows\Prefetch"
            ]

            deleted = 0
            for temp_dir in temp_dirs:
                if temp_dir and os.path.exists(temp_dir):
                    for item in os.listdir(temp_dir):
                        item_path = os.path.join(temp_dir, item)
                        try:
                            if os.path.isfile(item_path):
                                os.remove(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            deleted += 1
                        except:
                            pass  # Пропускаем недоступные файлы
            
            if msg == True:
                self.status_var.set(f"Очищено {deleted} временных файлов")
                messagebox.showinfo("Успех", f"Очищено {deleted} файлов")
        except Exception as e:
            self.status_var.set(f"Ошибка очистки: {e}")
            messagebox.showerror("Ошибка", str(e))
    
    def disable_services(self):
        """Отключить некоторые ненужные службы (пример: телеметрия)"""
        services = [
            "DiagTrack",      # Служба диагностики
            "dmwappushservice" # Телеметрия
        ]
        
        disabled = 0
        for service in services:
            cmd = f'sc config "{service}" start= disabled'
            result = self.run_cmd(cmd)
            if "успешно" in result.lower() or "success" in result.lower():
                disabled += 1
        
        self.status_var.set(f"Отключено {disabled} служб")
        messagebox.showinfo("Готово", f"Отключено {disabled} служб")

    def flush_dns(self):
        """Обновить/очистить DNS-кэш"""
        cmd = "ipconfig /flushdns"
        result = self.run_cmd(cmd)
        if "успешно" in result.lower() or "successful" in result.lower():
            self.status_var.set("DNS-кэш очищен")
            messagebox.showinfo("Готово", "DNS-кэш очищен")
        else:
            self.status_var.set("Ошибка очистки DNS")
            messagebox.showerror("Ошибка", result)
    
    def fix_updates(self):
        """Исправление ошибок обновлений Windows"""
        # Останавливаем службы обновлений
        cmds = ["net stop wuauserv", "net stop cryptSvc", "net stop bits", "net stop msiserver"]
        for cmd in cmds:
            result = self.run_cmd(cmd)
        # Очищаем файлы обновлений
        self.clear_temp(False)
        # Включаем службы обновлений
        cmds = ["net start wuauserv", "net start cryptSvc", "net start bits", "net start msiserver"]
        for cmd in cmds:
            result = self.run_cmd(cmd)
        self.status_var.set("Исправление ошибок обновлений выполнено")
        cmd = "wuauclt /detectnow"  # для Windows 7/8
        result = self.run_cmd(cmd)
        cmd = "UsoClient ScanInstallWait" # для Windows 10/11
        result = self.run_cmd(cmd)
        self.status_var.set("Проверка обновлений запущена")
        messagebox.showinfo("Информация", "Проверка обновлений запущена (может занять время). Проверьте Центр обноовлений Windows :)")
    
    def is_indexing_enabled(self):
        try:
            # Выполняем команду sc query для службы Windows Search
            cmd = 'sc query "wsearch"'
            result = self.run_cmd(cmd)
            # Проверяем, есть ли в выводе STATE : 4 RUNNING
            if '4  RUNNING' in result:
                return True
            else:
                return False
        except Exception as e:
            print(f"Ошибка при проверке состояния индексации: {e}")
            return False
    
    def disable_indexing(self):
        """Отключить индексацию"""
        cmd = 'sc config "wsearch" start= disabled'  # отключение индексации дисков
        result = self.run_cmd(cmd)        
        self.status_var.set("Индексация дисков отключена")
        messagebox.showinfo("Готово", "Индексация дисков отключена")
    
    def enable_indexing(self):
        """Включить индексацию"""
        cmd = 'sc config "wsearch" start=delayed-auto && sc start "wsearch"'  # включение индексации дисков
        result = self.run_cmd(cmd)        
        self.status_var.set("Индексация дисков включена")
        messagebox.showinfo("Готово", "Индексация дисков включена")
    
    def about(self):
        """ Окно с данными об устройстве """
        pc_window = tk.Toplevel(self.root)
        pc_window.title(f"BestWinTweaker О программе")
        pc_window.resizable(width=False, height=False)
        pc_window.iconbitmap(resource_path('./resources/images/BestWinTweaker.ico'))
        pc_window.geometry(f"{WIDTH}x{HEIGHT}")
        logo_img = Image.open(resource_path('./resources/images/BestWinTweaker.png'))
        logo_img = logo_img.resize((180, 180), Image.LANCZOS)
        logo_photo = ImageTk.PhotoImage(logo_img)
        logo_label = tk.Label(pc_window, image=logo_photo)
        logo_label.image = logo_photo  # сохраняем ссылку
        logo_label.pack()
        tk.Label(pc_window, text="Ускорение ПК в пару кликов!").pack()
        tk.Label(pc_window, text=f"BestWinTweaker, v. {VERSION}").pack()
        GitHubLink = tk.Label(pc_window, text="VladislavBanitsky", fg="blue", cursor="hand2", font=["Segoe UI", 9, "underline"])
        GitHubLink.pack()
        GitHubLink.bind("<Button-1>", lambda e: callback("https://github.com/VladislavBanitsky/BestWinTweaker"))
    
        
if __name__ == "__main__":
    root = tk.Tk()
    app = WindowsTweaker(root)
    root.mainloop()
