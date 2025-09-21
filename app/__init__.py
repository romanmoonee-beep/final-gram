"""
PR GRAM Bot - Telegram бот для взаимного продвижения каналов

Современный асинхронный Telegram бот с поддержкой:
- Создания и выполнения заданий
- Telegram Stars платежей
- Многоуровневой реферальной системы
- Системы чеков и переводов
- Детальной аналитики

Архитектура:
- SQLAlchemy 2.0+ с async/await
- Aiogram 3.7+ для Telegram API
- Redis для кэширования и FSM
- Pydantic для валидации
- Structlog для логирования
"""

__version__ = "1.0.0"
__author__ = "PR GRAM Team"
__email__ = "support@prgram.bot"
__description__ = "Telegram Bot for Channel Promotion"

# Экспорт основных компонентов
from app.config.settings import settings

__all__ = [
    "__version__",
    "__author__", 
    "__email__",
    "__description__",
    "settings"
]