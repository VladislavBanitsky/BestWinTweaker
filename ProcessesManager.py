import psutil
import time
import concurrent.futures


class ProcessesManager:
    """Менеджер процессов с быстрым параллельным сбором данных"""

    MAX_WORKERS = 8

    # Скрываем ВСЕГДА
    ALWAYS_HIDDEN = {
        'system idle process',
        'idle',
        'memory compression',
        'registry',
    }

    # Скрываем, если снят чекбокс «Показывать системные»
    SYSTEM_NAMES = {
        'system',
        'secure system',
        'smss.exe',
        'csrss.exe',
        'wininit.exe',
        'winlogon.exe',
        'services.exe',
        'lsass.exe',
        'dwm.exe',
        'fontdrvhost.exe',
        'svchost.exe',
        'sihost.exe',
        'taskhostw.exe',
        'runtimebroker.exe',
        'searchindexer.exe',
        'spoolsv.exe',
    }

    def __init__(self):
        self._warmed_up = False
        self._prev_io = {}

    # ------------------------------------------------------------------ #
    #  Классовые проверки                                                 #
    # ------------------------------------------------------------------ #
    @classmethod
    def is_always_hidden(cls, name: str) -> bool:
        return bool(name) and name.strip().lower() in cls.ALWAYS_HIDDEN

    @classmethod
    def is_system(cls, name: str) -> bool:
        return bool(name) and name.strip().lower() in cls.SYSTEM_NAMES

    # ------------------------------------------------------------------ #
    #  Публичный API                                                      #
    # ------------------------------------------------------------------ #
    def get_processes(self):
        """Полный сбор данных обо всех процессах."""
        procs = list(psutil.process_iter(
            ['pid', 'name', 'exe', 'status', 'memory_info',
             'num_threads', 'username', 'cmdline']
        ))

        self._warm_up_cpu(procs)

        def collect(p):
            try:
                info = p.info
                with p.oneshot():
                    info['cpu_percent'] = p.cpu_percent(None)
                    info['memory_percent'] = p.memory_percent()

                    mem = info.get('memory_info')
                    info['memory_mb'] = (mem.rss / 1024 / 1024) if mem else 0.0

                    try:
                        io = p.io_counters()
                        info['disk_read'] = io.read_bytes
                        info['disk_write'] = io.write_bytes
                    except (psutil.AccessDenied, AttributeError, NotImplementedError):
                        info['disk_read'] = 0
                        info['disk_write'] = 0

                info['net_connections'] = 0
                info['gpu_usage'] = 0.0

                info.setdefault('name', f"PID {info['pid']}")
                info.setdefault('status', 'unknown')
                info.setdefault('exe', '')
                info.setdefault('username', '')
                info.setdefault('cmdline', [])
                info.setdefault('num_threads', 0)

                return info

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                return None
            except Exception:
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as ex:
            results = list(ex.map(collect, procs))

        # Фильтр always-hidden
        processes = [
            r for r in results
            if r is not None and not self.is_always_hidden(r.get('name', ''))
        ]

        processes.sort(key=lambda x: x.get('cpu_percent', 0.0), reverse=True)
        return processes

    def get_processes_fast(self):
        """Быстрый сбор ТОЛЬКО меняющихся метрик."""
        result = {}

        try:
            pids = psutil.pids()
        except Exception:
            return result

        # Прогрев + список объектов Process
        procs = []
        for pid in pids:
            try:
                p = psutil.Process(pid)
                p.cpu_percent(None)
                procs.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        time.sleep(0.05)

        def collect(p):
            try:
                # Имя читаем ДО oneshot, чтобы отфильтровать скрытые
                try:
                    name = p.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return p.pid, None

                if self.is_always_hidden(name):
                    return p.pid, None

                with p.oneshot():
                    cpu = p.cpu_percent(None)
                    mem_pct = p.memory_percent()
                    mem_mb = p.memory_info().rss / 1024 / 1024
                    try:
                        io = p.io_counters()
                        rd, wr = io.read_bytes, io.write_bytes
                    except Exception:
                        rd = wr = 0
                    status = p.status()

                return p.pid, {
                    'cpu_percent': cpu,
                    'memory_percent': mem_pct,
                    'memory_mb': mem_mb,
                    'disk_read': rd,
                    'disk_write': wr,
                    'status': status,
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return p.pid, None
            except Exception:
                return p.pid, None

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as ex:
            for pid, data in ex.map(collect, procs):
                if data is not None:
                    result[pid] = data

        return result

    def get_process_details(self, pid):
        try:
            p = psutil.Process(pid)
            with p.oneshot():
                try:
                    memory_info = p.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                except Exception:
                    memory_mb = 0.0

                try:
                    cmdline = " ".join(p.cmdline()) if p.cmdline() else ""
                except Exception:
                    cmdline = ""

                try:
                    connections = [
                        {
                            'laddr': f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "",
                            'raddr': f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "",
                            'status': c.status,
                        }
                        for c in p.net_connections(kind='inet')
                    ]
                except Exception:
                    connections = []

                try:
                    exe = p.exe()
                except Exception:
                    exe = ''

                try:
                    username = p.username()
                except Exception:
                    username = ''

                return {
                    'pid': pid,
                    'name': p.name(),
                    'exe': exe,
                    'username': username,
                    'status': p.status(),
                    'cpu_percent': p.cpu_percent(None),
                    'memory_mb': memory_mb,
                    'memory_percent': p.memory_percent(),
                    'num_threads': p.num_threads(),
                    'cmdline': cmdline,
                    'connections': connections,
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def kill_process(self, pid, force=True):
        try:
            p = psutil.Process(pid)
            p.kill() if force else p.terminate()
            try:
                p.wait(timeout=3)
            except psutil.TimeoutExpired:
                return False
            return True
        except Exception:
            return False

    def suspend_process(self, pid):
        try:
            psutil.Process(pid).suspend()
            return True
        except Exception:
            return False

    def resume_process(self, pid):
        try:
            psutil.Process(pid).resume()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  Внутреннее                                                         #
    # ------------------------------------------------------------------ #
    def _warm_up_cpu(self, procs):
        for p in procs:
            try:
                p.cpu_percent(None)
            except Exception:
                pass
        time.sleep(0.1)

    @staticmethod
    def _safe(func):
        try:
            return func()
        except Exception:
            return None