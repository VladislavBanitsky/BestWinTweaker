# config_manager.py
import json
import os
from pathlib import Path

class ConfigManager:
    """Класс для управления настройками приложения"""
    
    def __init__(self):
        self.config_dir = Path(os.environ.get('USERPROFILE', '')) / '.bwt'
        self.config_file = self.config_dir / 'config.json'
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Создает папку конфигурации если её нет"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def get_theme(self):
        """Получить сохраненную тему"""
        config = self._load_config()
        return config.get('theme', 'Light')  # По умолчанию светлая
    
    def set_theme(self, theme):
        """Сохранить тему"""
        config = self._load_config()
        config['theme'] = theme
        self._save_config(config)
    
    def _load_config(self):
        """Загрузить конфигурацию из файла"""
        if not self.config_file.exists():
            return {}
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
            return {}
    
    def _save_config(self, config):
        """Сохранить конфигурацию в файл"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
            return False