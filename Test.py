# Добавить в models/transaction.py в enum TransactionType:

class TransactionType(str, Enum):
    """Типы транзакций"""
    
    # Существующие типы
    DEPOSIT_STARS = "deposit_stars"
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