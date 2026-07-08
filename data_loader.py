import patch_subprocess
import psutil
import cpuinfo
import GPUtil
import threading
import time
import os

from utilities import get_disk_type, get_ddr_type, get_board_model, get_windows_version, get_network_adapter_model



class DataLoader:
    """Класс для фоновой загрузки всех данных системы"""
    
    def __init__(self, splash_screen):
        self.splash = splash_screen
        self.loaded_data = {}
        self.loading_threads = []
        
    def load_all_data(self):
        """Загрузить все данные в фоновом режиме"""
        
        # Этапы загрузки с весами для прогресс-бара
        loading_tasks = [
            ("CPU", self.load_cpu_data, 5),
            ("Оперативная память", self.load_ram_data, 10),
            ("Видеокарта", self.load_gpu_data, 15),
            ("Диски", self.load_disk_data, 20),
            ("Сеть", self.load_network_data, 10),
            ("Материнская плата", self.load_board_data, 5),
            ("Автозагрузка", self.load_autostart_data, 15),
            ("UWP приложения", self.load_uwp_data, 20),
        ]
        
        total_weight = sum(task[2] for task in loading_tasks)
        completed_weight = 0
        
        for task_name, task_func, weight in loading_tasks:
            # Обновляем статус
            self.splash.set_status(f"Загрузка: {task_name}...", 
                                  int((completed_weight / total_weight) * 100))
            
            # Загружаем данные
            data = task_func()
            self.loaded_data[task_name] = data
            
            completed_weight += weight
            
            # Небольшая задержка для плавности UI
            time.sleep(0.05)
        
        # Завершаем загрузку
        self.splash.set_status("Готово!", 100)
        self.splash.complete_loading()
        
        return self.loaded_data
    
    def load_cpu_data(self):
        """Загрузка данных CPU"""
        try:
            return {
                'name': cpuinfo.get_cpu_info()['brand_raw'],
                'cores_logical': psutil.cpu_count(),
                'cores_physical': psutil.cpu_count(logical=False),
                'freq_min': psutil.cpu_freq().min if psutil.cpu_freq() else None,
                'freq_max': psutil.cpu_freq().max if psutil.cpu_freq() else None,
            }
        except Exception as e:
            return {'error': str(e)}
    
    def load_ram_data(self):
        """Загрузка данных RAM"""
        try:
            ram = psutil.virtual_memory()
            return {
                'total_gb': ram.total / (1024 ** 3),
                'used_gb': ram.used / (1024 ** 3),
                'percent': ram.percent,
                'ddr_type': get_ddr_type(),
            }
        except Exception as e:
            return {'error': str(e)}
    
    def load_gpu_data(self):
        """Загрузка данных GPU"""
        try:
            gpus = GPUtil.getGPUs()
            gpu_list = []
            for gpu in gpus:
                gpu_list.append({
                    'name': gpu.name,
                    'load': gpu.load * 100,
                    'temperature': gpu.temperature,
                    'memory_used': gpu.memoryUsed,
                    'memory_total': gpu.memoryTotal,
                    'memory_util': gpu.memoryUtil * 100,
                })
            return gpu_list
        except Exception as e:
            return {'error': str(e)}
    
    def load_network_data(self):
        """Загрузка данных сети"""
        try:
            from utilities import get_network_adapter_model
            net = psutil.net_io_counters()
            return {
                'bytes_sent': net.bytes_sent,
                'bytes_recv': net.bytes_recv,
                'bytes_sent_gb': net.bytes_sent / (1024 ** 3),
                'bytes_recv_gb': net.bytes_recv / (1024 ** 3),
                'adapter_model': get_network_adapter_model(),  # Добавлено
            }
        except Exception as e:
            return {'error': str(e)}
    
    def load_disk_data(self):
        """Загрузка данных дисков"""
        try:
            disks = {}
            for partition in psutil.disk_partitions():
                try:
                    
                    # Пропускаем CD/DVD приводы
                    if partition.opts and 'cdrom' in partition.opts.lower():
                        continue
                    
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks[partition.device] = {
                        'mount': partition.mountpoint,
                        'total_gb': usage.total / (1024 ** 3),
                        'used_gb': usage.used / (1024 ** 3),
                        'percent': usage.percent,
                        'type': get_disk_type(partition.device)
                    }
                except:
                    pass
            return disks
        except Exception as e:
            return {'error': str(e)}
    
    def load_board_data(self):
        """Загрузка данных материнской платы"""
        try:
            return {
                'model': get_board_model(),
            }
        except Exception as e:
            return {'error': str(e)}
    
    def load_autostart_data(self):
        """Загрузка данных автозагрузки"""
        try:
            from TweakerTools import TweakerTools
            programs = TweakerTools.get_all_startup_programs()
            return programs
        except Exception as e:
            return {'error': str(e)}
    
    def load_uwp_data(self):
        """Загрузка UWP приложений"""
        try:
            from uwpremover import UWPRemover
            remover = UWPRemover(None)
            apps = remover.get_removable_apps()
            return apps
        except Exception as e:
            return {'error': str(e)}