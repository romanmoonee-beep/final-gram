"""Модель настроек пользователя"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric, ForeignKey, BigInteger
from sqlalchemy.orm import relationship

from app.database.database import Base

class UserSettings(Base):
    """Настройки пользователя"""
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), unique=True, nullable=False)
    
    # =============================================================================
    # ЛОКАЛИЗАЦИЯ
    # =============================================================================
    
    language = Column(String(5), default="ru", nullable=False)  # ru, en
    timezone = Column(String(20), default="UTC+6", nullable=False)
    date_format = Column(String(20), default="%d.%m.%Y", nullable=False)
    time_format = Column(String(10), default="24h", nullable=False)  # 24h, 12h
    
    # =============================================================================
    # УВЕДОМЛЕНИЯ
    # =============================================================================
    
    # Основные уведомления
    task_notifications = Column(Boolean, default=True, nullable=False)
    payment_notifications = Column(Boolean, default=True, nullable=False)
    referral_notifications = Column(Boolean, default=True, nullable=False)
    admin_notifications = Column(Boolean, default=True, nullable=False)
    
    # Безопасность
    login_notifications = Column(Boolean, default=False, nullable=False)
    suspicious_activity_alerts = Column(Boolean, default=True, nullable=False)
    
    # Маркетинг
    promotional_notifications = Column(Boolean, default=True, nullable=False)
    newsletter_subscription = Column(Boolean, default=False, nullable=False)
    
    # Настройки времени уведомлений
    quiet_hours_enabled = Column(Boolean, default=False, nullable=False)
    quiet_hours_start = Column(String(5), default="22:00", nullable=True)  # HH:MM
    quiet_hours_end = Column(String(5), default="08:00", nullable=True)    # HH:MM
    
    # =============================================================================
    # ПРИВАТНОСТЬ
    # =============================================================================
    
    # Видимость профиля
    hide_profile = Column(Boolean, default=False, nullable=False)
    hide_stats = Column(Boolean, default=False, nullable=False)
    hide_from_leaderboard = Column(Boolean, default=False, nullable=False)
    hide_online_status = Column(Boolean, default=False, nullable=False)
    
    # Реферальная система
    allow_referral_mentions = Column(Boolean, default=True, nullable=False)
    hide_referral_earnings = Column(Boolean, default=False, nullable=False)
    
    # Контакты
    allow_direct_messages = Column(Boolean, default=True, nullable=False)
    show_telegram_username = Column(Boolean, default=True, nullable=False)
    
    # =============================================================================
    # АВТОВЫВОД СРЕДСТВ
    # =============================================================================
    
    auto_withdraw_enabled = Column(Boolean, default=False, nullable=False)
    auto_withdraw_threshold = Column(Numeric(precision=15, scale=2), nullable=True)
    auto_withdraw_method = Column(String(50), nullable=True)  # card, crypto, wallet
    auto_withdraw_address = Column(Text, nullable=True)       # Реквизиты
    auto_withdraw_min_amount = Column(Numeric(precision=15, scale=2), default=Decimal("100"), nullable=True)
    
    # Расписание автовывода
    auto_withdraw_frequency = Column(String(20), default="immediate", nullable=False)  # immediate, daily, weekly
    auto_withdraw_day = Column(Integer, nullable=True)        # День недели (1-7) или месяца (1-31)
    auto_withdraw_time = Column(String(5), nullable=True)     # HH:MM
    
    # =============================================================================
    # БЕЗОПАСНОСТЬ
    # =============================================================================
    
    # Двухфакторная аутентификация
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(32), nullable=True)
    two_factor_backup_codes = Column(Text, nullable=True)     # JSON array
    
    # API доступ
    api_access_enabled = Column(Boolean, default=False, nullable=False)
    api_key = Column(String(64), nullable=True)
    api_key_created_at = Column(DateTime, nullable=True)
    api_rate_limit = Column(Integer, default=100, nullable=False)  # requests per hour
    
    # Сессии
    max_active_sessions = Column(Integer, default=3, nullable=False)
    force_logout_on_suspicious = Column(Boolean, default=True, nullable=False)
    
    # =============================================================================
    # ИНТЕРФЕЙС
    # =============================================================================
    
    # Внешний вид
    theme = Column(String(20), default="default", nullable=False)  # default, dark, light
    compact_mode = Column(Boolean, default=False, nullable=False)
    show_animations = Column(Boolean, default=True, nullable=False)
    
    # Помощь и подсказки
    show_hints = Column(Boolean, default=True, nullable=False)
    show_tooltips = Column(Boolean, default=True, nullable=False)
    tutorial_completed = Column(Boolean, default=False, nullable=False)
    
    # Клавиатура и навигация
    keyboard_layout = Column(String(20), default="standard", nullable=False)  # standard, compact, minimal
    quick_actions_enabled = Column(Boolean, default=True, nullable=False)
    
    # =============================================================================
    # ЗАДАНИЯ И ЗАРАБОТОК
    # =============================================================================
    
    # Фильтры заданий
    preferred_task_types = Column(Text, nullable=True)        # JSON array
    min_task_reward = Column(Numeric(precision=15, scale=2), nullable=True)
    max_task_reward = Column(Numeric(precision=15, scale=2), nullable=True)
    
    # Автоматизация
    auto_accept_tasks = Column(Boolean, default=False, nullable=False)
    auto_accept_threshold = Column(Numeric(precision=15, scale=2), nullable=True)
    
    # Уведомления о заданиях
    notify_new_tasks = Column(Boolean, default=True, nullable=False)
    notify_task_completion = Column(Boolean, default=True, nullable=False)
    notify_high_reward_tasks = Column(Boolean, default=True, nullable=False)
    high_reward_threshold = Column(Numeric(precision=15, scale=2), default=Decimal("1000"), nullable=True)
    
    # =============================================================================
    # РЕФЕРАЛЬНАЯ СИСТЕМА
    # =============================================================================
    
    # Настройки рефералов
    referral_auto_messages = Column(Boolean, default=False, nullable=False)
    referral_welcome_message = Column(Text, nullable=True)
    referral_bonus_notifications = Column(Boolean, default=True, nullable=False)
    
    # Статистика
    track_referral_performance = Column(Boolean, default=True, nullable=False)
    share_referral_stats = Column(Boolean, default=False, nullable=False)
    
    # =============================================================================
    # ЭКСПЕРИМЕНТАЛЬНЫЕ ФУНКЦИИ
    # =============================================================================
    
    # Beta функции
    beta_features_enabled = Column(Boolean, default=False, nullable=False)
    experimental_ui = Column(Boolean, default=False, nullable=False)
    
    # Аналитика
    allow_analytics = Column(Boolean, default=True, nullable=False)
    allow_performance_tracking = Column(Boolean, default=True, nullable=False)
    
    # =============================================================================
    # МЕТАДАННЫЕ
    # =============================================================================
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Версия настроек (для миграций)
    settings_version = Column(Integer, default=1, nullable=False)
    
    # Связи
    user = relationship("User", back_populates="settings")
    
    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, language={self.language})>"
    
    # =============================================================================
    # МЕТОДЫ
    # =============================================================================
    
    def to_dict(self) -> dict:
        """Конвертация в словарь"""
        return {
            "localization": {
                "language": self.language,
                "timezone": self.timezone,
                "date_format": self.date_format,
                "time_format": self.time_format
            },
            "notifications": {
                "tasks": self.task_notifications,
                "payments": self.payment_notifications,
                "referrals": self.referral_notifications,
                "admin": self.admin_notifications,
                "login": self.login_notifications,
                "suspicious_activity": self.suspicious_activity_alerts,
                "promotional": self.promotional_notifications,
                "newsletter": self.newsletter_subscription,
                "quiet_hours": {
                    "enabled": self.quiet_hours_enabled,
                    "start": self.quiet_hours_start,
                    "end": self.quiet_hours_end
                }
            },
            "privacy": {
                "hide_profile": self.hide_profile,
                "hide_stats": self.hide_stats,
                "hide_from_leaderboard": self.hide_from_leaderboard,
                "hide_online_status": self.hide_online_status,
                "allow_referral_mentions": self.allow_referral_mentions,
                "hide_referral_earnings": self.hide_referral_earnings,
                "allow_direct_messages": self.allow_direct_messages,
                "show_telegram_username": self.show_telegram_username
            },
            "auto_withdraw": {
                "enabled": self.auto_withdraw_enabled,
                "threshold": float(self.auto_withdraw_threshold) if self.auto_withdraw_threshold else None,
                "method": self.auto_withdraw_method,
                "address": self.auto_withdraw_address,
                "min_amount": float(self.auto_withdraw_min_amount) if self.auto_withdraw_min_amount else None,
                "frequency": self.auto_withdraw_frequency,
                "day": self.auto_withdraw_day,
                "time": self.auto_withdraw_time
            },
            "security": {
                "two_factor_enabled": self.two_factor_enabled,
                "api_access_enabled": self.api_access_enabled,
                "api_rate_limit": self.api_rate_limit,
                "max_active_sessions": self.max_active_sessions,
                "force_logout_on_suspicious": self.force_logout_on_suspicious
            },
            "interface": {
                "theme": self.theme,
                "compact_mode": self.compact_mode,
                "show_animations": self.show_animations,
                "show_hints": self.show_hints,
                "show_tooltips": self.show_tooltips,
                "tutorial_completed": self.tutorial_completed,
                "keyboard_layout": self.keyboard_layout,
                "quick_actions_enabled": self.quick_actions_enabled
            },
            "tasks": {
                "preferred_types": self.preferred_task_types,
                "min_reward": float(self.min_task_reward) if self.min_task_reward else None,
                "max_reward": float(self.max_task_reward) if self.max_task_reward else None,
                "auto_accept": self.auto_accept_tasks,
                "auto_accept_threshold": float(self.auto_accept_threshold) if self.auto_accept_threshold else None,
                "notifications": {
                    "new_tasks": self.notify_new_tasks,
                    "completion": self.notify_task_completion,
                    "high_reward": self.notify_high_reward_tasks,
                    "high_reward_threshold": float(self.high_reward_threshold) if self.high_reward_threshold else None
                }
            },
            "referrals": {
                "auto_messages": self.referral_auto_messages,
                "welcome_message": self.referral_welcome_message,
                "bonus_notifications": self.referral_bonus_notifications,
                "track_performance": self.track_referral_performance,
                "share_stats": self.share_referral_stats
            },
            "experimental": {
                "beta_features": self.beta_features_enabled,
                "experimental_ui": self.experimental_ui,
                "allow_analytics": self.allow_analytics,
                "allow_performance_tracking": self.allow_performance_tracking
            }
        }
    
    def is_notification_allowed(self, notification_type: str) -> bool:
        """Проверить, разрешены ли уведомления данного типа"""
        notification_map = {
            "task": self.task_notifications,
            "payment": self.payment_notifications,
            "referral": self.referral_notifications,
            "admin": self.admin_notifications,
            "login": self.login_notifications,
            "suspicious": self.suspicious_activity_alerts,
            "promotional": self.promotional_notifications
        }
        
        return notification_map.get(notification_type, False)
    
    def is_quiet_hours(self) -> bool:
        """Проверить, включены ли тихие часы в данный момент"""
        if not self.quiet_hours_enabled:
            return False
        
        from datetime import datetime, time
        
        now = datetime.now().time()
        start = datetime.strptime(self.quiet_hours_start, "%H:%M").time()
        end = datetime.strptime(self.quiet_hours_end, "%H:%M").time()
        
        if start <= end:
            return start <= now <= end
        else:  # Период через полночь
            return now >= start or now <= end
    
    def get_display_language(self) -> str:
        """Получить язык для отображения"""
        language_names = {
            "ru": "Русский",
            "en": "English"
        }
        return language_names.get(self.language, "Unknown")
    
    def get_theme_emoji(self) -> str:
        """Получить эмодзи темы"""
        theme_emojis = {
            "default": "🎨",
            "dark": "🌙",
            "light": "☀️"
        }
        return theme_emojis.get(self.theme, "🎨")