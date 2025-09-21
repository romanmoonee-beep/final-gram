from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from app.bot.keyboards.main_menu import MainMenuCallback

class AdminCallback(CallbackData, prefix="admin"):
    """Callback данные для админки"""
    action: str
    target_id: int = 0
    page: int = 1

def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админки"""
    builder = InlineKeyboardBuilder()
    
    # Модерация
    builder.row(
        InlineKeyboardButton(
            text="🔍 Модерация заданий",
            callback_data=AdminCallback(action="moderation").pack()
        )
    )
    
    # Управление пользователями
    builder.row(
        InlineKeyboardButton(
            text="👥 Управление пользователями",
            callback_data=AdminCallback(action="users").pack()
        )
    )
    
    # Статистика
    builder.row(
        InlineKeyboardButton(
            text="📊 Статистика системы",
            callback_data=AdminCallback(action="stats").pack()
        ),
        InlineKeyboardButton(
            text="💰 Финансовая статистика",
            callback_data=AdminCallback(action="finance_stats").pack()
        )
    )
    
    # Системные функции
    builder.row(
        InlineKeyboardButton(
            text="⚙️ Системные функции",
            callback_data=AdminCallback(action="system").pack()
        )
    )
    
    # Назад в меню
    builder.row(
        InlineKeyboardButton(
            text="🏠 В главное меню",
            callback_data=MainMenuCallback(action="main_menu").pack()
        )
    )
    
    return builder.as_markup()

def get_moderation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура модерации"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="⏳ Ожидают проверки",
            callback_data=AdminCallback(action="pending_tasks").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="✅ Массовое одобрение",
            callback_data=AdminCallback(action="approve_auto").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="📊 Статистика модерации",
            callback_data=AdminCallback(action="moderation_stats").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в админку",
            callback_data=AdminCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup()

def get_task_moderation_keyboard(execution_id: int) -> InlineKeyboardMarkup:
    """Клавиатура модерации конкретного задания"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✅ Принять",
            callback_data=AdminCallback(action="approve", target_id=execution_id).pack()
        ),
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=AdminCallback(action="reject", target_id=execution_id).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔍 Подробнее",
            callback_data=AdminCallback(action="execution_details", target_id=execution_id).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ К списку",
            callback_data=AdminCallback(action="pending_tasks").pack()
        )
    )
    
    return builder.as_markup()

def get_user_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления пользователями"""
    builder = InlineKeyboardBuilder()
    
    # Поиск и управление
    builder.row(
        InlineKeyboardButton(
            text="🔍 Найти пользователя",
            callback_data=AdminCallback(action="find_user").pack()
        )
    )
    
    # Массовые операции
    builder.row(
        InlineKeyboardButton(
            text="📊 ТОП пользователей",
            callback_data=AdminCallback(action="top_users").pack()
        ),
        InlineKeyboardButton(
            text="🚫 Заблокированные",
            callback_data=AdminCallback(action="banned_users").pack()
        )
    )
    
    # Статистика
    builder.row(
        InlineKeyboardButton(
            text="📈 Аналитика пользователей",
            callback_data=AdminCallback(action="user_analytics").pack()
        )
    )
    
    # Массовые действия
    builder.row(
        InlineKeyboardButton(
            text="💰 Массовое начисление",
            callback_data=AdminCallback(action="mass_bonus").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в админку",
            callback_data=AdminCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup()

def get_user_profile_keyboard(user_id: int, is_banned: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура профиля пользователя для админа"""
    builder = InlineKeyboardBuilder()
    
    # Действия с пользователем
    if not is_banned:
        builder.row(
            InlineKeyboardButton(
                text="🚫 Заблокировать",
                callback_data=AdminCallback(action="ban_user", target_id=user_id).pack()
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Разблокировать",
                callback_data=AdminCallback(action="unban_user", target_id=user_id).pack()
            )
        )
    
    # Финансовые операции
    builder.row(
        InlineKeyboardButton(
            text="💰 Изменить баланс",
            callback_data=AdminCallback(action="change_balance", target_id=user_id).pack()
        ),
        InlineKeyboardButton(
            text="📜 История транзакций",
            callback_data=AdminCallback(action="user_transactions", target_id=user_id).pack()
        )
    )
    
    # Аналитика
    builder.row(
        InlineKeyboardButton(
            text="📊 Детальная статистика",
            callback_data=AdminCallback(action="user_details", target_id=user_id).pack()
        ),
        InlineKeyboardButton(
            text="🎯 Задания пользователя",
            callback_data=AdminCallback(action="user_tasks", target_id=user_id).pack()
        )
    )
    
    # Уведомления
    builder.row(
        InlineKeyboardButton(
            text="📤 Отправить сообщение",
            callback_data=AdminCallback(action="send_message", target_id=user_id).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к управлению",
            callback_data=AdminCallback(action="users").pack()
        )
    )
    
    return builder.as_markup()

def get_system_functions_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура системных функций"""
    builder = InlineKeyboardBuilder()
    
    # Очистка и обслуживание
    builder.row(
        InlineKeyboardButton(
            text="🧹 Очистить истекшие",
            callback_data=AdminCallback(action="cleanup").pack()
        ),
        InlineKeyboardButton(
            text="⬆️ Обновить уровни",
            callback_data=AdminCallback(action="update_levels").pack()
        )
    )
    
    # Рассылки и уведомления
    builder.row(
        InlineKeyboardButton(
            text="📢 Массовая рассылка",
            callback_data=AdminCallback(action="broadcast").pack()
        )
    )
    
    # Экспорт и резервное копирование
    builder.row(
        InlineKeyboardButton(
            text="📊 Экспорт данных",
            callback_data=AdminCallback(action="export_data").pack()
        ),
        InlineKeyboardButton(
            text="💾 Резервная копия",
            callback_data=AdminCallback(action="backup").pack()
        )
    )
    
    # Настройки системы
    builder.row(
        InlineKeyboardButton(
            text="⚙️ Настройки бота",
            callback_data=AdminCallback(action="bot_settings").pack()
        )
    )
    
    # Мониторинг
    builder.row(
        InlineKeyboardButton(
            text="📈 Мониторинг системы",
            callback_data=AdminCallback(action="system_monitor").pack()
        ),
        InlineKeyboardButton(
            text="🔍 Логи ошибок",
            callback_data=AdminCallback(action="error_logs").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в админку",
            callback_data=AdminCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup()

def get_statistics_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура статистики"""
    builder = InlineKeyboardBuilder()
    
    # Основная статистика
    builder.row(
        InlineKeyboardButton(
            text="👥 Пользователи",
            callback_data=AdminCallback(action="user_stats").pack()
        ),
        InlineKeyboardButton(
            text="🎯 Задания",
            callback_data=AdminCallback(action="task_stats").pack()
        )
    )
    
    # Финансовая статистика
    builder.row(
        InlineKeyboardButton(
            text="💰 Финансы",
            callback_data=AdminCallback(action="finance_stats").pack()
        ),
        InlineKeyboardButton(
            text="⭐ Stars платежи",
            callback_data=AdminCallback(action="stars_stats").pack()
        )
    )
    
    # Аналитика по времени
    builder.row(
        InlineKeyboardButton(
            text="📅 За сегодня",
            callback_data=AdminCallback(action="today_stats").pack()
        ),
        InlineKeyboardButton(
            text="📊 За неделю",
            callback_data=AdminCallback(action="week_stats").pack()
        )
    )
    
    # Детальная аналитика
    builder.row(
        InlineKeyboardButton(
            text="🔬 Детальная аналитика",
            callback_data=AdminCallback(action="detailed_analytics").pack()
        )
    )
    
    # Экспорт отчетов
    builder.row(
        InlineKeyboardButton(
            text="📋 Экспорт отчета",
            callback_data=AdminCallback(action="export_report").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔄 Обновить данные",
            callback_data=AdminCallback(action="stats").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в админку",
            callback_data=AdminCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup()

def get_broadcast_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения рассылки"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✅ Отправить всем",
            callback_data="confirm_broadcast"
        ),
        InlineKeyboardButton(
            text="📝 Редактировать",
            callback_data="edit_broadcast"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="👥 Выбрать аудиторию",
            callback_data=AdminCallback(action="select_audience").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel_broadcast"
        )
    )
    
    return builder.as_markup()

def get_audience_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора аудитории для рассылки"""
    builder = InlineKeyboardBuilder()
    
    # По уровням
    builder.row(
        InlineKeyboardButton(
            text="🥉 Bronze",
            callback_data=AdminCallback(action="broadcast_level", target_id=1).pack()
        ),
        InlineKeyboardButton(
            text="🥈 Silver",
            callback_data=AdminCallback(action="broadcast_level", target_id=2).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🥇 Gold",
            callback_data=AdminCallback(action="broadcast_level", target_id=3).pack()
        ),
        InlineKeyboardButton(
            text="💎 Premium",
            callback_data=AdminCallback(action="broadcast_level", target_id=4).pack()
        )
    )
    
    # По активности
    builder.row(
        InlineKeyboardButton(
            text="🔥 Активные (7 дней)",
            callback_data=AdminCallback(action="broadcast_active").pack()
        )
    )
    
    # По балансу
    builder.row(
        InlineKeyboardButton(
            text="💰 С балансом > 1000",
            callback_data=AdminCallback(action="broadcast_balance").pack()
        )
    )
    
    # Все пользователи
    builder.row(
        InlineKeyboardButton(
            text="👥 Всем пользователям",
            callback_data="confirm_broadcast"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=AdminCallback(action="broadcast").pack()
        )
    )
    
    return builder.as_markup()

def get_balance_operation_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура операций с балансом"""
    builder = InlineKeyboardBuilder()
    
    # Быстрые суммы
    builder.row(
        InlineKeyboardButton(
            text="+100 GRAM",
            callback_data=AdminCallback(action="quick_bonus", target_id=user_id, page=100).pack()
        ),
        InlineKeyboardButton(
            text="+500 GRAM",
            callback_data=AdminCallback(action="quick_bonus", target_id=user_id, page=500).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="+1000 GRAM",
            callback_data=AdminCallback(action="quick_bonus", target_id=user_id, page=1000).pack()
        ),
        InlineKeyboardButton(
            text="+5000 GRAM",
            callback_data=AdminCallback(action="quick_bonus", target_id=user_id, page=5000).pack()
        )
    )
    
    # Пользовательская сумма
    builder.row(
        InlineKeyboardButton(
            text="💰 Своя сумма",
            callback_data=AdminCallback(action="change_balance", target_id=user_id).pack()
        )
    )
    
    # Заморозка/разморозка
    builder.row(
        InlineKeyboardButton(
            text="🧊 Заморозить средства",
            callback_data=AdminCallback(action="freeze_balance", target_id=user_id).pack()
        ),
        InlineKeyboardButton(
            text="🔓 Разморозить средства",
            callback_data=AdminCallback(action="unfreeze_balance", target_id=user_id).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к пользователю",
            callback_data=AdminCallback(action="user_profile", target_id=user_id).pack()
        )
    )
    
    return builder.as_markup()

def get_pagination_keyboard(
    action: str,
    current_page: int,
    has_next: bool,
    has_prev: bool = None,
    additional_buttons: list = None
) -> InlineKeyboardMarkup:
    """Универсальная клавиатура с пагинацией"""
    builder = InlineKeyboardBuilder()
    
    # Дополнительные кнопки сверху
    if additional_buttons:
        for button in additional_buttons:
            builder.row(button)
    
    # Навигация
    nav_buttons = []
    
    if has_prev is None:
        has_prev = current_page > 1
    
    if has_prev:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=AdminCallback(action=action, page=current_page-1).pack()
            )
        )
    
    # Текущая страница
    nav_buttons.append(
        InlineKeyboardButton(
            text=f"📄 {current_page}",
            callback_data="current_page"
        )
    )
    
    if has_next:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Вперед",
                callback_data=AdminCallback(action=action, page=current_page+1).pack()
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Кнопка возврата
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в админку",
            callback_data=AdminCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup()

def get_confirmation_keyboard(
    confirm_action: str,
    cancel_action: str = "menu",
    confirm_text: str = "✅ Подтвердить",
    cancel_text: str = "❌ Отмена"
) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=confirm_text,
            callback_data=confirm_action
        ),
        InlineKeyboardButton(
            text=cancel_text,
            callback_data=cancel_action
        )
    )
    
    return builder.as_markup()

def get_error_logs_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для просмотра логов ошибок"""
    builder = InlineKeyboardBuilder()
    
    # Фильтры по времени
    builder.row(
        InlineKeyboardButton(
            text="🕐 За час",
            callback_data=AdminCallback(action="logs_hour").pack()
        ),
        InlineKeyboardButton(
            text="📅 За день",
            callback_data=AdminCallback(action="logs_day").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="📊 За неделю",
            callback_data=AdminCallback(action="logs_week").pack()
        ),
        InlineKeyboardButton(
            text="🗓️ За месяц",
            callback_data=AdminCallback(action="logs_month").pack()
        )
    )
    
    # Фильтры по типу
    builder.row(
        InlineKeyboardButton(
            text="⚠️ Предупреждения",
            callback_data=AdminCallback(action="logs_warnings").pack()
        ),
        InlineKeyboardButton(
            text="❌ Ошибки",
            callback_data=AdminCallback(action="logs_errors").pack()
        )
    )
    
    # Действия
    builder.row(
        InlineKeyboardButton(
            text="🧹 Очистить логи",
            callback_data=AdminCallback(action="clear_logs").pack()
        ),
        InlineKeyboardButton(
            text="📁 Экспорт логов",
            callback_data=AdminCallback(action="export_logs").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к системным функциям",
            callback_data=AdminCallback(action="system").pack()
        )
    )
    
    return builder.as_markup()

def get_bot_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек бота"""
    builder = InlineKeyboardBuilder()
    
    # Основные настройки
    builder.row(
        InlineKeyboardButton(
            text="💰 Настройки GRAM",
            callback_data=AdminCallback(action="gram_settings").pack()
        ),
        InlineKeyboardButton(
            text="📊 Настройки уровней",
            callback_data=AdminCallback(action="level_settings").pack()
        )
    )
    
    # Задания
    builder.row(
        InlineKeyboardButton(
            text="🎯 Настройки заданий",
            callback_data=AdminCallback(action="task_settings").pack()
        ),
        InlineKeyboardButton(
            text="💳 Настройки чеков",
            callback_data=AdminCallback(action="check_settings").pack()
        )
    )
    
    # Платежи
    builder.row(
        InlineKeyboardButton(
            text="⭐ Настройки Stars",
            callback_data=AdminCallback(action="stars_settings").pack()
        ),
        InlineKeyboardButton(
            text="💎 Настройки криптоплатежей",
            callback_data=AdminCallback(action="crypto_settings").pack()
        )
    )
    
    # Безопасность
    builder.row(
        InlineKeyboardButton(
            text="🔐 Настройки безопасности",
            callback_data=AdminCallback(action="security_settings").pack()
        )
    )
    
    # Уведомления
    builder.row(
        InlineKeyboardButton(
            text="📢 Настройки уведомлений",
            callback_data=AdminCallback(action="notification_settings").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к системным функциям",
            callback_data=AdminCallback(action="system").pack()
        )
    )
    
    return builder.as_markup()