"""
Модели базы данных

ВАЖНО: Этот файл должен импортировать ВСЕ модели
чтобы SQLAlchemy знал о них при создании таблиц
"""

# Импортируем в правильном порядке (от базовых к зависимым)
from .user import User, UserLevel
from .user_settings import UserSettings
from .transaction import Transaction, TransactionType, TransactionStatus
from .task import Task, TaskType, TaskStatus
from .task_execution import TaskExecution, ExecutionStatus
from .check import Check, CheckType, CheckStatus, CheckActivation

# Экспортируем все модели
__all__ = [
    # User models
    "User", "UserLevel", "UserSettings",
    
    # Transaction models
    "Transaction", "TransactionType", "TransactionStatus",
    
    # Task models
    "Task", "TaskType", "TaskStatus",
    "TaskExecution", "ExecutionStatus",
    
    # Check models
    "Check", "CheckType", "CheckStatus", "CheckActivation",
]

# Для проверки что все модели загружены
def get_all_models():
    """Возвращает список всех моделей"""
    from app.database.database import Base
    return list(Base.metadata.tables.keys())
