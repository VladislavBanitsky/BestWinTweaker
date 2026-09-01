class StatusManager:
    """Менеджер для управления статусом с приоритетами и задержками"""
    
    def __init__(self, status_label):
        self.status_label = status_label
        self.priority = 0
        self.timer = None
        self.hover_timer = None
        self.default_text = "Готов"
        self.default_color = "gray"
        self.last_status = None
        
    def set_status(self, text, color="gray", priority=0, timeout=None, force=False):
        """
        Установка статуса
        
        Args:
            text: Текст статуса
            color: Цвет текста
            priority: 0 - обычный, 1 - важный, 2 - критичный
            timeout: Таймаут в мс
            force: Принудительно установить статус
        """
        if not force and priority < self.priority and self.priority > 0:
            return
        
        # Отменяем таймеры
        self._clear_timers()
        
        self.status_label.configure(text=text, text_color=color)
        self.priority = priority
        
        if timeout and timeout > 0:
            self.timer = self.status_label.after(
                timeout,
                lambda: self.reset(priority)
            )
    
    def show_hover(self, text, delay=250):
        """Показать статус при наведении с задержкой"""
        if self.priority > 0:
            return
        
        self._clear_hover_timer()
        self.hover_timer = self.status_label.after(
            delay,
            lambda: self.status_label.configure(text=text, text_color="orange")
        )
    
    def hide_hover(self):
        """Скрыть статус наведения"""
        self._clear_hover_timer()
        if self.priority == 0:
            self.status_label.configure(text=self.default_text, text_color=self.default_color)
    
    def reset(self, priority):
        """Сброс статуса"""
        if self.priority == priority:
            self.status_label.configure(text=self.default_text, text_color=self.default_color)
            self.priority = 0
    
    def _clear_timers(self):
        if self.timer:
            self.status_label.after_cancel(self.timer)
            self.timer = None
    
    def _clear_hover_timer(self):
        if self.hover_timer:
            self.status_label.after_cancel(self.hover_timer)
            self.hover_timer = None