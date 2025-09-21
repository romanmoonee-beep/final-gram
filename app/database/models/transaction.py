from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
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
    from app.database.models.user import User

class TransactionType(StrEnum):
    """Типы транзакций с современным Enum"""
    DEPOSIT_STARS = "deposit_stars"
    DEPOSIT BONUS = "deposit_bonus"
    TASK_REWARD = "task_reward"
    TASK_CREATION = "task_creation"
    REFERRAL_BONUS = "referral_bonus"
    REFERRAL_COMMISSION = "referral_commission"
    
    # Чеки
    CHECK_CREATED = "check_created"
    CHECK_RECEIVED = "check_received"
    CHECK_CANCELLED = "check_cancelled"
    
    # Администрирование
    ADMIN_BONUS = "admin_bonus"
    ADMIN_PENALTY = "admin_penalty"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    
    # Заморозка средств
    BALANCE_FREEZE = "balance_freeze"
    BALANCE_UNFREEZE = "balance_unfreeze"
    
    # Автовывод
    AUTO_WITHDRAWAL = "auto_withdrawal"
    WITHDRAWAL_FEE = "withdrawal_fee"
    
    # Криптоплатежи
    DEPOSIT_CRYPTO = "deposit_crypto"
    CRYPTO_FEE = "crypto_fee"
    
    # Система скидок и бонусов
    LEVEL_BONUS = "level_bonus"
    ACHIEVEMENT_BONUS = "achievement_bonus"
    LOYALTY_BONUS = "loyalty_bonus"
    
    # Возвраты и корректировки
    REFUND = "refund"
    CORRECTION = "correction"
    COMPENSATION = "compensation"
    
    # Конкурсы и события
    CONTEST_PRIZE = "contest_prize"
    EVENT_BONUS = "event_bonus"
    PROMO_BONUS = "promo_bonus"

class TransactionStatus(StrEnum):
    """Статусы транзакций"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class Transaction(Base):
    __tablename__ = "transactions"
    
    # Основные поля
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True
    )
    
    # Детали транзакции
    type: Mapped[TransactionType] = mapped_column(String(50), index=True)
    status: Mapped[TransactionStatus] = mapped_column(
        String(20), 
        default=TransactionStatus.COMPLETED,
        index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    
    # Описание и метаданные
    description: Mapped[str | None] = mapped_column(Text)
    reference_id: Mapped[str | None] = mapped_column(String(255), index=True)
    reference_type: Mapped[str | None] = mapped_column(String(50))  # task, check, referral
    
    # Данные для Telegram Stars
    stars_amount: Mapped[int | None] = mapped_column(Integer)
    stars_transaction_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    
    # Баланс до и после транзакции (для аудита)
    balance_before: Mapped[Decimal | None] = mapped_column(Numeric(precision=15, scale=2))
    balance_after: Mapped[Decimal | None] = mapped_column(Numeric(precision=15, scale=2))
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Связи
    user: Mapped[User] = relationship(back_populates="transactions", lazy="selectin")
    
    # Составные индексы для аналитики
    __table_args__ = (
        Index("ix_transactions_user_type", "user_id", "type"),
        Index("ix_transactions_user_created", "user_id", "created_at"),
        Index("ix_transactions_type_status", "type", "status"),
        Index("ix_transactions_reference", "reference_type", "reference_id"),
    )
    
    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, user_id={self.user_id}, type={self.type}, amount={self.amount})>"