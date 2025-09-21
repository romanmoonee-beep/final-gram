from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base

if TYPE_CHECKING:
    from app.database.models.task import Task
    from app.database.models.transaction import Transaction
    from app.database.models.user_settings import UserSettings

class UserLevel(StrEnum):
    """Современный Enum с поддержкой строк"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PREMIUM = "premium"

class User(Base):
    __tablename__ = "users"
    
    # Первичный ключ и Telegram данные
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(32), index=True)
    first_name: Mapped[str | None] = mapped_column(String(64))
    last_name: Mapped[str | None] = mapped_column(String(64))
    language_code: Mapped[str] = mapped_column(String(10), default="ru")
    
    # Финансовая информация с Decimal для точности
    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), 
        default=Decimal("0.00"),
        index=True
    )
    frozen_balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), 
        default=Decimal("0.00")
    )
    total_deposited: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), 
        default=Decimal("0.00")
    )
    total_withdrawn: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), 
        default=Decimal("0.00")
    )
    
    # Статус и уровень
    level: Mapped[UserLevel] = mapped_column(
        String(20), 
        default=UserLevel.BRONZE,
        index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    ban_reason: Mapped[str | None] = mapped_column(Text)
    
    # Реферальная система
    referrer_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    total_referrals: Mapped[int] = mapped_column(Integer, default=0)
    premium_referrals: Mapped[int] = mapped_column(Integer, default=0)
    referral_earnings: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), 
        default=Decimal("0.00")
    )
    
    # Статистика активности
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    tasks_created: Mapped[int] = mapped_column(Integer, default=0)
    total_earned: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), 
        default=Decimal("0.00")
    )
    total_spent: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), 
        default=Decimal("0.00")
    )
    
    # Дневные лимиты (сбрасываются каждый день)
    daily_tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    daily_tasks_created: Mapped[int] = mapped_column(Integer, default=0)
    last_task_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Временные метки с timezone support
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    last_activity: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True
    )
    premium_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Настройки и preferences
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_withdraw_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    min_task_reward: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        default=Decimal("50.00")
    )
    
    # Связи с современным синтаксисом - ИСПРАВЛЕНО
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="user",
        lazy="select",  # Изменено с selectin на select
        cascade="all, delete-orphan"
    )
    created_tasks: Mapped[list["Task"]] = relationship(
        foreign_keys="Task.author_id",
        lazy="select"  # Изменено с selectin на select
    )
    settings: Mapped[Optional["UserSettings"]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # Составные индексы для оптимизации запросов
    __table_args__ = (
        Index("ix_users_level_balance", "level", "balance"),
        Index("ix_users_referrer_active", "referrer_id", "is_active"),
        Index("ix_users_created_activity", "created_at", "last_activity"),
    )
    
    def __repr__(self) -> str:
        return f"<User(telegram_id={self.telegram_id}, username={self.username}, level={self.level})>"
    
    @property
    def available_balance(self) -> Decimal:
        """Доступный баланс (баланс - замороженные средства)"""
        return self.balance - self.frozen_balance
    
    @property
    def full_name(self) -> str:
        """Полное имя пользователя"""
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts)) or self.username or str(self.telegram_id)
    
    def get_level_config(self) -> dict[str, any]:
        """Конфигурация текущего уровня с современным типизированием"""
        configs = {
            UserLevel.BRONZE: {
                "name": "🥉 Bronze",
                "emoji": "🥉",
                "min_balance": Decimal("0"),
                "commission_rate": Decimal("0.07"),
                "max_daily_tasks": 5,
                "referral_bonus": Decimal("1000"),
                "task_multiplier": Decimal("1.0"),
                "max_task_reward": Decimal("500"),
                "features": ["basic_tasks", "referrals"]
            },
            UserLevel.SILVER: {
                "name": "🥈 Silver",
                "emoji": "🥈", 
                "min_balance": Decimal("10000"),
                "commission_rate": Decimal("0.06"),
                "max_daily_tasks": 15,
                "referral_bonus": Decimal("1500"),
                "task_multiplier": Decimal("1.2"),
                "max_task_reward": Decimal("1000"),
                "features": ["basic_tasks", "referrals", "priority_support"]
            },
            UserLevel.GOLD: {
                "name": "🥇 Gold",
                "emoji": "🥇",
                "min_balance": Decimal("50000"),
                "commission_rate": Decimal("0.05"),
                "max_daily_tasks": 30,
                "referral_bonus": Decimal("2000"),
                "task_multiplier": Decimal("1.35"),
                "max_task_reward": Decimal("2000"),
                "features": ["basic_tasks", "referrals", "priority_support", "exclusive_tasks"]
            },
            UserLevel.PREMIUM: {
                "name": "💎 Premium",
                "emoji": "💎",
                "min_balance": Decimal("100000"),
                "commission_rate": Decimal("0.03"),
                "max_daily_tasks": -1,  # Безлимит
                "referral_bonus": Decimal("3000"),
                "task_multiplier": Decimal("1.5"),
                "max_task_reward": Decimal("5000"),
                "features": ["all"]
            }
        }
        return configs.get(self.level, configs[UserLevel.BRONZE])
