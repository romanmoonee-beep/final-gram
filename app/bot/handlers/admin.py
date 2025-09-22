import asyncio
import logging
import structlog

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, desc, or_

from aiogram.types import Message
from aiogram.filters import StateFilter

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database.models.user import User
from app.database.models.task import Task, TaskStatus
from app.database.models.task_execution import TaskExecution, ExecutionStatus
from app.database.models.transaction import Transaction, TransactionType
from app.services.user_service import UserService
from app.services.task_service import TaskService
from app.services.transaction_service import TransactionService
from app.services.subscription_check import CheckService
from app.bot.keyboards.admin import (
    AdminCallback, get_admin_menu_keyboard, get_moderation_keyboard,
    get_task_moderation_keyboard, get_user_management_keyboard
)
from app.bot.keyboards.main_menu import MainMenuCallback, get_main_menu_keyboard
from app.bot.states.admin_states import AdminStates
from app.bot.filters.admin import AdminFilter
from app.config.settings import settings
from app.database.database import get_session
from app.database.models.required_subscription import RequiredSubscription

logger = structlog.get_logger(__name__)

router = Router()
router.message.filter(AdminFilter())  # Только для админов
router.callback_query.filter(AdminFilter())

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда /admin"""
    text = """🔧 <b>АДМИН ПАНЕЛЬ</b>
    
Добро пожаловать в панель администратора!

🎯 <b>Доступные функции:</b>
• Модерация заданий и выполнений
• Управление пользователями
• Системная статистика
• Финансовая аналитика
• Системные функции"""
    
    await message.answer(
        text,
        reply_markup=get_admin_menu_keyboard()
    )

@router.callback_query(AdminCallback.filter(F.action == "menu"))
async def show_admin_menu(callback: CallbackQuery):
    """Показать главное меню админки"""
    text = """🔧 <b>АДМИН ПАНЕЛЬ</b>
    
Добро пожаловать в панель администратора!

🎯 <b>Доступные функции:</b>
• Модерация заданий и выполнений
• Управление пользователями
• Системная статистика
• Финансовая аналитика
• Системные функции"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()

# =============================================================================
# МОДЕРАЦИЯ ЗАДАНИЙ
# =============================================================================

@router.callback_query(AdminCallback.filter(F.action == "moderation"))
async def show_moderation_menu(callback: CallbackQuery):
    """Показать меню модерации"""
    
    async with get_session() as session:
        # Количество выполнений ожидающих проверки
        pending_result = await session.execute(
            select(func.count(TaskExecution.id))
            .where(TaskExecution.status == ExecutionStatus.PENDING)
        )
        pending_count = pending_result.scalar() or 0
        
        # Количество заданий требующих ручной проверки
        manual_result = await session.execute(
            select(func.count(TaskExecution.id))
            .where(
                and_(
                    TaskExecution.status == ExecutionStatus.PENDING,
                    TaskExecution.auto_checked == False
                )
            )
        )
        manual_count = manual_result.scalar() or 0
    
    text = f"""🔍 <b>МОДЕРАЦИЯ ЗАДАНИЙ</b>

📊 <b>СТАТИСТИКА:</b>
├ Ожидают проверки: {pending_count}
├ Ручная проверка: {manual_count}
├ Автопроверка: {pending_count - manual_count}
└ Всего активных: {pending_count}

⚡ <b>БЫСТРЫЕ ДЕЙСТВИЯ:</b>
• Просмотр заданий на проверке
• Массовое одобрение простых заданий
• Автообработка по критериям"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_moderation_keyboard()
    )
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "pending_tasks"))
async def show_pending_tasks(
    callback: CallbackQuery,
    callback_data: AdminCallback
):
    """Показать задания на проверке"""
    page = callback_data.page
    limit = 5
    offset = (page - 1) * limit
    
    async with get_session() as session:
        result = await session.execute(
            select(TaskExecution)
            .where(TaskExecution.status == ExecutionStatus.PENDING)
            .order_by(desc(TaskExecution.created_at))
            .limit(limit + 1)
            .offset(offset)
        )
        
        executions = list(result.scalars().all())
        has_next = len(executions) > limit
        if has_next:
            executions = executions[:limit]
    
    if not executions:
        text = """🔍 <b>ЗАДАНИЯ НА ПРОВЕРКЕ</b>

✅ Все задания проверены!

📊 В очереди модерации заданий нет."""
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=AdminCallback(action="moderation").pack()
            )
        )
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
        return
    
    text = f"""🔍 <b>ЗАДАНИЯ НА ПРОВЕРКЕ</b>

📄 Страница {page} | Всего: {len(executions)}

Выберите задание для модерации:"""
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    # Задания
    for execution in executions:
        # Получаем связанные данные
        task_title = "Неизвестное задание"
        username = f"ID{execution.user_id}"
        
        # Здесь нужно получить task и user через relations или отдельные запросы
        task_result = await session.execute(
            select(Task).where(Task.id == execution.task_id)
        )
        task = task_result.scalar_one_or_none()
        
        user_result = await session.execute(
            select(User).where(User.telegram_id == execution.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if task:
            task_title = task.title[:30] + "..." if len(task.title) > 30 else task.title
        if user:
            username = user.username or f"ID{user.telegram_id}"
        
        button_text = f"🎯 {task_title} | @{username}"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=AdminCallback(action="review_task", target_id=execution.id).pack()
            )
        )
    
    # Навигация
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=AdminCallback(action="pending_tasks", page=page-1).pack()
            )
        )
    
    if has_next:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Вперед",
                callback_data=AdminCallback(action="pending_tasks", page=page+1).pack()
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Массовые действия
    builder.row(
        InlineKeyboardButton(
            text="✅ Одобрить все автопроверки",
            callback_data=AdminCallback(action="approve_auto").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в модерацию",
            callback_data=AdminCallback(action="moderation").pack()
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "review_task"))
async def review_task_execution(
    callback: CallbackQuery,
    callback_data: AdminCallback
):
    """Детальный просмотр выполнения задания"""
    execution_id = callback_data.target_id
    
    async with get_session() as session:
        result = await session.execute(
            select(TaskExecution).where(TaskExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
    
    if not execution:
        await callback.answer("❌ Выполнение не найдено", show_alert=True)
        return
    
    # Получаем связанные данные
    async with get_session() as session:
        task_result = await session.execute(
            select(Task).where(Task.id == execution.task_id)
        )
        task = task_result.scalar_one_or_none()
        
        user_result = await session.execute(
            select(User).where(User.telegram_id == execution.user_id)
        )
        user = user_result.scalar_one_or_none()
    
    if not task or not user:
        await callback.answer("❌ Данные не найдены", show_alert=True)
        return
    
    # Проверяем автопроверку
    auto_check_text = "✅ Пройдена" if execution.auto_checked else "⏳ Требует проверки"
    
    text = f"""📋 <b>ПРОВЕРКА ВЫПОЛНЕНИЯ</b>

🎯 <b>ЗАДАНИЕ:</b>
├ Название: {task.title}
├ Тип: {task.type.value}
├ Автор: ID{task.author_id}
└ Награда: {execution.reward_amount:,.0f} GRAM

👤 <b>ИСПОЛНИТЕЛЬ:</b>
├ Пользователь: @{user.username or 'без username'}
├ ID: {user.telegram_id}
├ Уровень: {user.level.value}
└ Дата выполнения: {execution.created_at.strftime('%d.%m.%Y %H:%M')}

🔍 <b>ПРОВЕРКА:</b>
├ Автопроверка: {auto_check_text}
├ Ссылка: {task.target_url}
└ Статус: {execution.status.value}"""
    
    if execution.user_comment:
        text += f"\n\n💬 <b>Комментарий:</b>\n{execution.user_comment}"
    
    if execution.screenshot_url:
        text += f"\n\n📷 <b>Скриншот:</b> Прикреплен"
    
    keyboard = get_task_moderation_keyboard(execution.id)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "approve"))
async def approve_task_execution(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    task_service: TaskService
):
    """Одобрить выполнение задания"""
    execution_id = callback_data.target_id
    
    success = await task_service.complete_task_execution(
        execution_id,
        auto_checked=False,
        reviewer_id=callback.from_user.id,
        review_comment="Одобрено администратором"
    )
    
    if success:
        await callback.answer("✅ Выполнение одобрено и оплачено")
        # Возвращаемся к списку
        await show_pending_tasks(
            callback,
            AdminCallback(action="pending_tasks", page=1)
        )
    else:
        await callback.answer("❌ Не удалось одобрить выполнение", show_alert=True)

@router.callback_query(AdminCallback.filter(F.action == "reject"))
async def start_reject_task(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    state: FSMContext
):
    """Начать процесс отклонения задания"""
    execution_id = callback_data.target_id
    
    await state.set_state(AdminStates.entering_reject_reason)
    await state.update_data(execution_id=execution_id)
    
    text = """❌ <b>ОТКЛОНЕНИЕ ВЫПОЛНЕНИЯ</b>

Введите причину отклонения:

💡 <b>Примеры причин:</b>
• Задание не выполнено
• Недостаточно доказательств
• Нарушение условий
• Фальшивый скриншот

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await callback.message.edit_text(text)
    await callback.answer()

@router.message(AdminStates.entering_reject_reason)
async def process_reject_reason(
    message: Message,
    state: FSMContext
):
    """Обработать причину отклонения"""
    reason = message.text.strip()
    
    if len(reason) > 200:
        await message.answer("❌ Причина слишком длинная (максимум 200 символов)")
        return
    
    data = await state.get_data()
    execution_id = data['execution_id']
    
    # Отклоняем выполнение
    async with get_session() as session:
        result = await session.execute(
            select(TaskExecution).where(TaskExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        
        if execution:
            execution.status = ExecutionStatus.REJECTED
            execution.reviewer_id = message.from_user.id
            execution.review_comment = reason
            execution.reviewed_at = datetime.utcnow()
            
            await session.commit()
    
    await state.clear()
    
    text = f"""✅ <b>ВЫПОЛНЕНИЕ ОТКЛОНЕНО</b>

Причина: {reason}

Пользователь будет уведомлен об отклонении."""
    
    await message.answer(
        text,
        reply_markup=get_admin_menu_keyboard()
    )

@router.callback_query(AdminCallback.filter(F.action == "approve_auto"))
async def mass_approve_auto_checks(
    callback: CallbackQuery,
    task_service: TaskService
):
    """Массовое одобрение автопроверок"""
    
    async with get_session() as session:
        # Находим все автопроверенные выполнения
        result = await session.execute(
            select(TaskExecution).where(
                and_(
                    TaskExecution.status == ExecutionStatus.PENDING,
                    TaskExecution.auto_checked == True
                )
            )
        )
        
        auto_executions = list(result.scalars().all())
        approved_count = 0
        
        for execution in auto_executions:
            success = await task_service.complete_task_execution(
                execution.id,
                auto_checked=True,
                reviewer_id=callback.from_user.id,
                review_comment="Массовое одобрение автопроверок"
            )
            
            if success:
                approved_count += 1
    
    text = f"""✅ <b>МАССОВОЕ ОДОБРЕНИЕ ЗАВЕРШЕНО</b>

📊 Одобрено автопроверок: {approved_count}

Все задания с успешной автопроверкой были одобрены и оплачены."""
    
    await callback.answer(f"✅ Одобрено {approved_count} заданий")
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard()
    )

# =============================================================================
# УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
# =============================================================================

@router.callback_query(AdminCallback.filter(F.action == "users"))
async def show_user_management(callback: CallbackQuery):
    """Показать управление пользователями"""
    
    async with get_session() as session:
        # Общая статистика
        total_users = await session.execute(select(func.count(User.id)))
        total_count = total_users.scalar() or 0
        
        # По уровням
        levels_stats = await session.execute(
            select(User.level, func.count(User.id))
            .group_by(User.level)
        )
        
        levels_data = dict(levels_stats.fetchall())
        
        # Активные пользователи (были онлайн за последние 7 дней)
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        active_users = await session.execute(
            select(func.count(User.id))
            .where(User.last_activity >= week_ago)
        )
        active_count = active_users.scalar() or 0
        
        # Заблокированные
        banned_users = await session.execute(
            select(func.count(User.id))
            .where(User.is_banned == True)
        )
        banned_count = banned_users.scalar() or 0
    
    text = f"""👥 <b>УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ</b>

📊 <b>ОБЩАЯ СТАТИСТИКА:</b>
├ Всего пользователей: {total_count:,}
├ Активных (7 дней): {active_count:,}
├ Заблокированных: {banned_count:,}
└ Конверсия активности: {(active_count/total_count*100 if total_count > 0 else 0):.1f}%

📈 <b>ПО УРОВНЯМ:</b>
├ 🥉 Bronze: {levels_data.get('bronze', 0):,}
├ 🥈 Silver: {levels_data.get('silver', 0):,}
├ 🥇 Gold: {levels_data.get('gold', 0):,}
└ 💎 Premium: {levels_data.get('premium', 0):,}

⚡ <b>ДЕЙСТВИЯ:</b>
• Поиск пользователя
• Управление балансом
• Блокировка/разблокировка
• Массовые рассылки"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_user_management_keyboard()
    )
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "find_user"))
async def start_find_user(callback: CallbackQuery, state: FSMContext):
    """Начать поиск пользователя"""
    
    await state.set_state(AdminStates.entering_user_id)
    
    text = """🔍 <b>ПОИСК ПОЛЬЗОВАТЕЛЯ</b>

Введите ID пользователя или username:

💡 <b>Примеры:</b>
• <code>123456789</code> (Telegram ID)
• <code>@username</code> (username)

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await callback.message.edit_text(text)
    await callback.answer()

@router.message(AdminStates.entering_user_id)
async def process_find_user(
    message: Message,
    state: FSMContext,
    user_service: UserService
):
    """Обработать поиск пользователя"""
    query = message.text.strip()
    
    # Парсим запрос
    if query.startswith('@'):
        username = query[1:]
        # Поиск по username
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
    else:
        try:
            user_id = int(query)
            user = await user_service.get_user(user_id)
        except ValueError:
            await message.answer("❌ Некорректный ID или username")
            return
    
    if not user:
        await message.answer("❌ Пользователь не найден")
        return
    
    # Получаем статистику пользователя
    stats = await user_service.get_user_stats(user.telegram_id)
    
    status_text = "✅ Активен"
    if user.is_banned:
        status_text = f"❌ Заблокирован: {user.ban_reason}"
    
    text = f"""👤 <b>ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ</b>

🆔 <b>ОСНОВНОЕ:</b>
├ ID: <code>{user.telegram_id}</code>
├ Username: @{user.username or 'не указан'}
├ Имя: {user.first_name or 'не указано'}
├ Статус: {status_text}
└ Уровень: {user.level}

💰 <b>ФИНАНСЫ:</b>
├ Баланс: {user.balance:,.0f} GRAM
├ Заморожено: {user.frozen_balance:,.0f} GRAM
├ Заработано: {user.total_earned:,.0f} GRAM
└ Потрачено: {user.total_spent:,.0f} GRAM

📊 <b>АКТИВНОСТЬ:</b>
├ Заданий выполнено: {user.tasks_completed}
├ Заданий создано: {user.tasks_created}
├ Рефералов: {user.total_referrals}
├ Транзакций: {stats['total_transactions']}
└ Возраст аккаунта: {stats['account_age_days']} дн.

📅 <b>ДАТЫ:</b>
├ Регистрация: {user.created_at.strftime('%d.%m.%Y %H:%M')}
└ Последняя активность: {user.last_activity.strftime('%d.%m.%Y %H:%M') if user.last_activity else 'давно'}"""
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    # Действия с пользователем
    if not user.is_banned:
        builder.row(
            InlineKeyboardButton(
                text="🚫 Заблокировать",
                callback_data=AdminCallback(action="ban_user", target_id=user.telegram_id).pack()
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Разблокировать",
                callback_data=AdminCallback(action="unban_user", target_id=user.telegram_id).pack()
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="💰 Изменить баланс",
            callback_data=AdminCallback(action="change_balance", target_id=user.telegram_id).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="📊 Подробная статистика",
            callback_data=AdminCallback(action="user_details", target_id=user.telegram_id).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к управлению",
            callback_data=AdminCallback(action="users").pack()
        )
    )
    
    await message.answer(text, reply_markup=builder.as_markup())
    await state.clear()

@router.callback_query(AdminCallback.filter(F.action == "change_balance"))
async def start_change_balance(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    state: FSMContext
):
    """Начать изменение баланса пользователя"""
    user_id = callback_data.target_id
    
    await state.set_state(AdminStates.entering_bonus_amount)
    await state.update_data(user_id=user_id)
    
    text = """💰 <b>ИЗМЕНЕНИЕ БАЛАНСА</b>

Введите сумму для изменения:

💡 <b>Формат:</b>
• +1000 - добавить 1000 GRAM
• -500 - списать 500 GRAM
• 2000 - установить баланс 2000 GRAM

⚠️ <b>Внимание:</b> Операция необратима!

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await callback.message.edit_text(text)
    await callback.answer()

@router.message(AdminStates.entering_bonus_amount)
async def process_balance_change(
    message: Message,
    state: FSMContext,
    user_service: UserService
):
    """Обработать изменение баланса"""
    try:
        amount_str = message.text.strip()
        data = await state.get_data()
        user_id = data['user_id']
        
        # Получаем пользователя
        user = await user_service.get_user(user_id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            await state.clear()
            return
        
        old_balance = user.balance
        
        # Парсим сумму
        if amount_str.startswith('+'):
            # Добавить к балансу
            amount = Decimal(amount_str[1:])
            operation = "Начисление"
            operation_type = TransactionType.ADMIN_BONUS
        elif amount_str.startswith('-'):
            # Списать с баланса
            amount = Decimal(amount_str[1:])
            if old_balance < amount:
                await message.answer("❌ Недостаточно средств для списания")
                return
            amount = -amount  # Для транзакции
            operation = "Списание"
            operation_type = TransactionType.ADMIN_PENALTY
        else:
            # Установить баланс
            new_balance = Decimal(amount_str)
            amount = new_balance - old_balance
            operation = "Установка баланса"
            operation_type = TransactionType.ADMIN_ADJUSTMENT
        
        # Обновляем баланс
        success = await user_service.update_balance(
            user_id,
            amount,
            operation_type,
            f"{operation} администратором #{message.from_user.id}"
        )
        
        if success:
            updated_user = await user_service.get_user(user_id)
            text = f"""✅ <b>БАЛАНС ИЗМЕНЕН</b>

👤 Пользователь: ID{user_id}
💰 Было: {old_balance:,.0f} GRAM
💰 Стало: {updated_user.balance:,.0f} GRAM
📊 Изменение: {amount:+,.0f} GRAM

Операция выполнена администратором #{message.from_user.id}"""
            
            await message.answer(text, reply_markup=get_admin_menu_keyboard())
        else:
            await message.answer("❌ Не удалось изменить баланс")
        
    except (ValueError, InvalidOperation):
        await message.answer("❌ Некорректная сумма. Используйте числа и +/- префиксы")
        return
    
    await state.clear()

@router.callback_query(AdminCallback.filter(F.action == "ban_user"))
async def start_ban_user(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    state: FSMContext
):
    """Начать блокировку пользователя"""
    
    user_id = callback_data.target_id
    await state.set_state(AdminStates.entering_ban_reason)
    await state.update_data(user_id=user_id)
    
    text = """🚫 <b>БЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ</b>

Введите причину блокировки:

💡 <b>Примеры причин:</b>
• Мошенничество
• Нарушение правил
• Спам
• Фейковая активность

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await callback.message.edit_text(text)
    await callback.answer()

@router.message(AdminStates.entering_ban_reason)
async def process_ban_user(
    message: Message,
    state: FSMContext,
    user_service: UserService
):
    """Обработать блокировку пользователя"""
    reason = message.text.strip()
    
    if len(reason) > 200:
        await message.answer("❌ Причина слишком длинная (максимум 200 символов)")
        return
    
    data = await state.get_data()
    user_id = data['user_id']
    
    success = await user_service.ban_user(
        user_id,
        reason,
        message.from_user.id
    )
    
    await state.clear()
    
    if success:
        text = f"""✅ <b>ПОЛЬЗОВАТЕЛЬ ЗАБЛОКИРОВАН</b>

ID: {user_id}
Причина: {reason}

Пользователь больше не сможет пользоваться ботом."""
    else:
        text = "❌ Не удалось заблокировать пользователя"
    
    await message.answer(
        text,
        reply_markup=get_admin_menu_keyboard()
    )

@router.callback_query(AdminCallback.filter(F.action == "unban_user"))
async def unban_user(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    user_service: UserService
):
    """Разблокировать пользователя"""
    
    user_id = callback_data.target_id
    
    success = await user_service.unban_user(user_id, callback.from_user.id)
    
    if success:
        await callback.answer("✅ Пользователь разблокирован")
        text = f"""✅ <b>ПОЛЬЗОВАТЕЛЬ РАЗБЛОКИРОВАН</b>

ID: {user_id}

Пользователь снова может пользоваться ботом."""
    else:
        await callback.answer("❌ Не удалось разблокировать", show_alert=True)
        return
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard()
    )

# =============================================================================
# СТАТИСТИКА
# =============================================================================

@router.callback_query(AdminCallback.filter(F.action == "stats"))
async def show_system_stats(callback: CallbackQuery):
    """Показать системную статистику"""
    
    async with get_session() as session:
        # Статистика пользователей
        users_total = await session.execute(select(func.count(User.id)))
        users_count = users_total.scalar() or 0
        
        # Статистика заданий
        tasks_stats = await session.execute(
            select(Task.status, func.count(Task.id))
            .group_by(Task.status)
        )
        tasks_by_status = dict(tasks_stats.fetchall())
        
        # Статистика выполнений
        executions_stats = await session.execute(
            select(TaskExecution.status, func.count(TaskExecution.id))
            .group_by(TaskExecution.status)
        )
        executions_by_status = dict(executions_stats.fetchall())
        
        # Финансовая статистика
        total_gram = await session.execute(
            select(func.sum(User.balance))
        )
        total_balance = total_gram.scalar() or 0
        
        # Транзакции за 24 часа
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_transactions = await session.execute(
            select(func.count(Transaction.id))
            .where(Transaction.created_at >= yesterday)
        )
        recent_tx_count = recent_transactions.scalar() or 0
        
        # Новые пользователи за 24 часа
        new_users = await session.execute(
            select(func.count(User.id))
            .where(User.created_at >= yesterday)
        )
        new_users_count = new_users.scalar() or 0
    
    text = f"""📊 <b>СИСТЕМНАЯ СТАТИСТИКА</b>

👥 <b>ПОЛЬЗОВАТЕЛИ:</b>
├ Всего: {users_count:,}
├ Новых за 24ч: {new_users_count:,}
└ Рост: {(new_users_count/users_count*100 if users_count > 0 else 0):.2f}%

🎯 <b>ЗАДАНИЯ:</b>
├ Активных: {tasks_by_status.get(TaskStatus.ACTIVE, 0):,}
├ Завершенных: {tasks_by_status.get(TaskStatus.COMPLETED, 0):,}
├ Приостановленных: {tasks_by_status.get(TaskStatus.PAUSED, 0):,}
└ Отмененных: {tasks_by_status.get(TaskStatus.CANCELLED, 0):,}

💼 <b>ВЫПОЛНЕНИЯ:</b>
├ Ожидают: {executions_by_status.get(ExecutionStatus.PENDING, 0):,}
├ Завершены: {executions_by_status.get(ExecutionStatus.COMPLETED, 0):,}
├ Отклонены: {executions_by_status.get(ExecutionStatus.REJECTED, 0):,}
└ Просрочены: {executions_by_status.get(ExecutionStatus.EXPIRED, 0):,}

💰 <b>ФИНАНСЫ:</b>
├ Общий баланс: {total_balance:,.0f} GRAM
├ Транзакций за 24ч: {recent_tx_count:,}
└ Средний баланс: {(total_balance/users_count if users_count > 0 else 0):,.0f} GRAM

🕐 <b>Последнее обновление:</b> {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}"""
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="💰 Финансовая статистика",
            callback_data=AdminCallback(action="finance_stats").pack()
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

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
    except:
        await callback.answer("Данные обновлены ✅")

@router.callback_query(AdminCallback.filter(F.action == "finance_stats"))
async def show_finance_stats(callback: CallbackQuery):
    """Показать финансовую статистику"""
    
    async with get_session() as session:
        # Статистика по типам транзакций
        tx_types_stats = await session.execute(
            select(
                Transaction.type,
                func.count(Transaction.id).label('count'),
                func.sum(Transaction.amount).label('total')
            )
            .group_by(Transaction.type)
        )
        
        # Статистика за последние 7 дней
        week_ago = datetime.utcnow() - timedelta(days=7)
        weekly_stats = await session.execute(
            select(
                func.sum(Transaction.amount).filter(Transaction.amount > 0).label('income'),
                func.sum(Transaction.amount).filter(Transaction.amount < 0).label('spending'),
                func.count(Transaction.id).label('total_tx')
            )
            .where(Transaction.created_at >= week_ago)
        )
        
        weekly = weekly_stats.first()
        
        # ТОП пользователей по балансу
        top_users = await session.execute(
            select(User.telegram_id, User.username, User.balance)
            .order_by(User.balance.desc())
            .limit(5)
        )
        
        # Статистика Stars платежей
        stars_stats = await session.execute(
            select(
                func.count(Transaction.id).label('count'),
                func.sum(Transaction.amount).label('total_gram'),
                func.sum(Transaction.stars_amount).label('total_stars')
            )
            .where(Transaction.type == TransactionType.DEPOSIT_STARS)
        )
        
        stars = stars_stats.first()
    
    # Формируем статистику по типам
    types_text = ""
    for row in tx_types_stats:
        tx_type = row.type
        count = row.count
        total = row.total or 0
        
        type_names = {
            TransactionType.DEPOSIT_STARS: '⭐ Stars',
            TransactionType.TASK_REWARD: '🎯 Награды',
            TransactionType.TASK_CREATION: '📢 Создание',
            TransactionType.REFERRAL_BONUS: '👥 Рефералы'
        }
        
        name = type_names.get(tx_type)
        types_text += f"├ {name}: {count:,} шт. | {total:,.0f} GRAM\n"
    
    text = f"""💰 <b>ФИНАНСОВАЯ СТАТИСТИКА</b>

📊 <b>ЗА НЕДЕЛЮ:</b>
├ Доходы: +{float(weekly.income or 0):,.0f} GRAM
├ Расходы: {float(weekly.spending or 0):,.0f} GRAM
├ Транзакций: {weekly.total_tx:,}
└ Прибыль: {float((weekly.income or 0) + (weekly.spending or 0)):,.0f} GRAM

🌟 <b>TELEGRAM STARS:</b>
├ Платежей: {stars.count or 0:,}
├ Получено GRAM: {float(stars.total_gram or 0):,.0f}
└ Получено Stars: {stars.total_stars or 0:,}

📈 <b>ПО ТИПАМ ТРАНЗАКЦИЙ:</b>
{types_text}

🏆 <b>ТОП ПОЛЬЗОВАТЕЛЕЙ:</b>"""
    
    for i, user in enumerate(top_users, 1):
        username = user.username or f"ID{user.telegram_id}"
        text += f"\n{i}. @{username}: {user.balance:,.0f} GRAM"
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📊 Детальная аналитика",
            callback_data=AdminCallback(action="detailed_analytics").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к статистике",
            callback_data=AdminCallback(action="stats").pack()
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "top_users"))
async def show_top_users(callback: CallbackQuery):
    """Показать ТОП пользователей"""
    async with get_session() as session:
        # ТОП по балансу
        top_balance = await session.execute(
            select(User.telegram_id, User.username, User.balance)
            .order_by(User.balance.desc())
            .limit(10)
        )

        # ТОП по заданиям
        top_tasks = await session.execute(
            select(User.telegram_id, User.username, User.tasks_completed)
            .order_by(User.tasks_completed.desc())
            .limit(10)
        )

    text = "🏆 <b>ТОП ПОЛЬЗОВАТЕЛЕЙ</b>\n\n💰 <b>ПО БАЛАНСУ:</b>\n"

    for i, user in enumerate(top_balance, 1):
        username = user.username or f"ID{user.telegram_id}"
        text += f"{i}. @{username}: {user.balance:,.0f} GRAM\n"

    text += "\n🎯 <b>ПО ЗАДАНИЯМ:</b>\n"
    for i, user in enumerate(top_tasks, 1):
        username = user.username or f"ID{user.telegram_id}"
        text += f"{i}. @{username}: {user.tasks_completed} заданий\n"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к управлению",
            callback_data=AdminCallback(action="users").pack()
        )
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "user_analytics"))
async def show_user_analytics(callback: CallbackQuery):
    """Показать аналитику пользователей"""
    async with get_session() as session:
        # Общая статистика
        total_users = await session.execute(select(func.count(User.id)))
        week_ago = datetime.utcnow() - timedelta(days=7)

        new_users = await session.execute(
            select(func.count(User.id))
            .where(User.created_at >= week_ago)
        )

        active_users = await session.execute(
            select(func.count(User.id))
            .where(User.last_activity >= week_ago)
        )

        # По уровням
        levels_stats = await session.execute(
            select(User.level, func.count(User.id))
            .group_by(User.level)
        )

    total_count = total_users.scalar() or 0
    new_count = new_users.scalar() or 0
    active_count = active_users.scalar() or 0

    text = f"""📊 <b>АНАЛИТИКА ПОЛЬЗОВАТЕЛЕЙ</b>

👥 <b>ОБЩАЯ СТАТИСТИКА:</b>
├ Всего пользователей: {total_count:,}
├ Новых за неделю: {new_count:,}
├ Активных за неделю: {active_count:,}
└ Коэффициент активности: {(active_count / total_count * 100 if total_count > 0 else 0):.1f}%

📈 <b>ПО УРОВНЯМ:</b>"""

    levels_data = dict(levels_stats.fetchall())
    level_names = {"bronze": "🥉 Bronze", "silver": "🥈 Silver", "gold": "🥇 Gold", "premium": "💎 Premium"}

    for level, name in level_names.items():
        count = levels_data.get(level, 0)
        text += f"\n├ {name}: {count:,}"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к управлению",
            callback_data=AdminCallback(action="users").pack()
        )
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "mass_bonus"))
async def start_mass_bonus(callback: CallbackQuery, state: FSMContext):
    """Начать массовое начисление"""
    await state.set_state(AdminStates.entering_mass_bonus_amount)

    text = """💰 <b>МАССОВОЕ НАЧИСЛЕНИЕ</b>

Введите сумму для начисления всем пользователям:

💡 <b>Примеры:</b>
- 100 - начислить 100 GRAM всем
- 500 - начислить 500 GRAM всем

⚠️ <b>Внимание:</b> Операция необратима!

❌ <i>Для отмены отправьте /cancel</i>"""

    await callback.message.edit_text(text)
    await callback.answer()


@router.message(AdminStates.entering_mass_bonus_amount)
async def process_mass_bonus(
        message: Message,
        state: FSMContext,
        user_service: UserService
):
    """Обработать массовое начисление"""
    try:
        amount = Decimal(message.text.strip())

        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return

        # Получаем всех активных пользователей
        async with get_session() as session:
            result = await session.execute(
                select(User.telegram_id).where(
                    and_(User.is_active == True, User.is_banned == False)
                )
            )
            user_ids = [row[0] for row in result.fetchall()]

        # Подтверждение
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"confirm_mass_bonus_{amount}"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel_mass_bonus"
            )
        )

        await state.update_data(amount=float(amount), user_ids=user_ids)

        text = f"""💰 <b>ПОДТВЕРЖДЕНИЕ МАССОВОГО НАЧИСЛЕНИЯ</b>

💰 Сумма: {amount:,.0f} GRAM на пользователя
👥 Пользователей: {len(user_ids):,}
💳 Общая сумма: {float(amount) * len(user_ids):,.0f} GRAM

⚠️ <b>Эта операция необратима!</b>"""

        await message.answer(text, reply_markup=builder.as_markup())

    except (ValueError, InvalidOperation):
        await message.answer("❌ Введите корректную сумму")


@router.callback_query(F.data.startswith("confirm_mass_bonus_"))
async def confirm_mass_bonus(callback: CallbackQuery, state: FSMContext, user_service: UserService):
    """Подтвердить массовое начисление"""
    data = await state.get_data()
    amount = data.get('amount')
    user_ids = data.get('user_ids', [])

    if not amount or not user_ids:
        await callback.answer("❌ Данные не найдены", show_alert=True)
        await state.clear()
        return

    await callback.message.edit_text("⏳ Выполняется массовое начисление...")

    success_count = 0
    for user_id in user_ids:
        success = await user_service.update_balance(
            user_id,
            amount,
            "admin_bonus",
            f"Массовое начисление от администратора #{callback.from_user.id}"
        )
        if success:
            success_count += 1

    text = f"""✅ <b>МАССОВОЕ НАЧИСЛЕНИЕ ЗАВЕРШЕНО</b>

💰 Начислено: {amount:,.0f} GRAM
👥 Успешно: {success_count:,} пользователей
❌ Ошибок: {len(user_ids) - success_count}

Общая сумма: {float(amount) * success_count:,.0f} GRAM"""

    await callback.message.edit_text(text, reply_markup=get_admin_menu_keyboard())
    await state.clear()
    await callback.answer("✅ Массовое начисление завершено")

@router.callback_query(AdminCallback.filter(F.action == "subscriptions"))
async def show_subscriptions_menu(callback: CallbackQuery):
    """Показать меню управления подписками"""

    async with get_session() as session:
        # Получаем все подписки
        result = await session.execute(
            select(RequiredSubscription)
            .order_by(RequiredSubscription.order_index, RequiredSubscription.id)
        )
        subscriptions = list(result.scalars().all())

        active_count = len([s for s in subscriptions if s.is_active])

    text = f"""📺 <b>УПРАВЛЕНИЕ ПОДПИСКАМИ</b>

📊 <b>СТАТИСТИКА:</b>
├ Всего каналов: {len(subscriptions)}
├ Активных: {active_count}
├ Отключенных: {len(subscriptions) - active_count}
└ Статус системы: {'🟢 Включена' if active_count > 0 else '🔴 Отключена'}

⚙️ <b>ФУНКЦИИ:</b>
• Добавление обязательных каналов
• Включение/отключение каналов
• Изменение порядка отображения
• Просмотр статистики подписок

💡 <i>Админы не проверяются на подписки</i>"""

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()

    # Управление каналами
    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить канал",
            callback_data=AdminCallback(action="add_subscription").pack()
        )
    )

    if subscriptions:
        builder.row(
            InlineKeyboardButton(
                text="📋 Список каналов",
                callback_data=AdminCallback(action="list_subscriptions").pack()
            ),
            InlineKeyboardButton(
                text="📊 Статистика",
                callback_data=AdminCallback(action="subscription_stats").pack()
            )
        )

    # Массовые действия
    if subscriptions:
        builder.row(
            InlineKeyboardButton(
                text="🟢 Включить все",
                callback_data=AdminCallback(action="enable_all_subs").pack()
            ),
            InlineKeyboardButton(
                text="🔴 Отключить все",
                callback_data=AdminCallback(action="disable_all_subs").pack()
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в админку",
            callback_data=AdminCallback(action="menu").pack()
        )
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "add_subscription"))
async def start_add_subscription(callback: CallbackQuery, state: FSMContext):
    """Начать добавление канала"""

    await state.set_state(AdminStates.entering_channel_url)

    text = """➕ <b>ДОБАВЛЕНИЕ КАНАЛА</b>

Введите ссылку на канал:

💡 <b>Поддерживаемые форматы:</b>
• @username
• https://t.me/username
• https://t.me/joinchat/xxxxx

📝 <b>Примеры:</b>
• @my_channel
• https://t.me/my_channel
• https://t.me/joinchat/AAAA1A1aA1aA1a

❌ <i>Для отмены отправьте /cancel</i>"""

    await callback.message.edit_text(text)
    await callback.answer()


@router.message(AdminStates.entering_channel_url)
async def process_channel_url(message: Message, state: FSMContext):
    """Обработать ссылку на канал"""
    from app.services.telegram_api_service import TelegramAPIService
    from app.bot.utils.validators import TelegramValidator

    url = message.text.strip()

    # Валидация URL
    is_valid, error = TelegramValidator.validate_channel_url(url)
    if not is_valid:
        await message.answer(f"❌ {error}\n\nПопробуйте еще раз:")
        return

    # Проверяем существование канала
    telegram_api = TelegramAPIService()
    channel_info = await telegram_api.get_chat_info(url)

    if not channel_info:
        await message.answer("❌ Канал не найден или недоступен\n\nПопробуйте еще раз:")
        return

    # Нормализуем URL
    if url.startswith('@'):
        normalized_url = f"https://t.me/{url[1:]}"
        username = url
    elif 'joinchat' in url or '+' in url:
        normalized_url = url
        username = channel_info.get('title', 'Приватный канал')
    else:
        normalized_url = url
        username = f"@{channel_info.get('username', '')}"

    # Проверяем, не добавлен ли уже
    async with get_session() as session:
        existing = await session.execute(
            select(RequiredSubscription)
            .where(RequiredSubscription.channel_url == normalized_url)
        )

        if existing.scalar_one_or_none():
            await message.answer("❌ Этот канал уже добавлен в обязательные подписки")
            await state.clear()
            return

        # Создаем запись
        subscription = RequiredSubscription(
            channel_username=username,
            channel_title=channel_info.get('title'),
            channel_url=normalized_url,
            created_by=message.from_user.id,
            order_index=0  # Добавляем в начало
        )

        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)

    text = f"""✅ <b>КАНАЛ ДОБАВЛЕН!</b>

📺 <b>Канал:</b> {subscription.display_name}
🔗 <b>Ссылка:</b> {normalized_url}
📊 <b>Участников:</b> {channel_info.get('member_count', 'неизвестно')}

Канал добавлен в список обязательных подписок и автоматически активирован."""

    await message.answer(text, reply_markup=get_admin_menu_keyboard())
    await state.clear()


@router.callback_query(AdminCallback.filter(F.action == "list_subscriptions"))
async def show_subscriptions_list(callback: CallbackQuery):
    """Показать список каналов"""

    async with get_session() as session:
        result = await session.execute(
            select(RequiredSubscription)
            .order_by(RequiredSubscription.order_index, RequiredSubscription.id)
        )
        subscriptions = list(result.scalars().all())

    if not subscriptions:
        text = """📋 <b>СПИСОК КАНАЛОВ</b>

📭 Обязательные каналы не настроены.

Добавьте первый канал:"""

        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="➕ Добавить канал",
                callback_data=AdminCallback(action="add_subscription").pack()
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=AdminCallback(action="subscriptions").pack()
            )
        )

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
        return

    text = f"""📋 <b>СПИСОК КАНАЛОВ</b>

📊 Всего: {len(subscriptions)} каналов

Выберите канал для управления:"""

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()

    # Список каналов
    for subscription in subscriptions:
        status_icon = "🟢" if subscription.is_active else "🔴"

        button_text = f"{status_icon} {subscription.display_name}"

        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=AdminCallback(action="manage_subscription", target_id=subscription.id).pack()
            )
        )

    # Управление
    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить канал",
            callback_data=AdminCallback(action="add_subscription").pack()
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=AdminCallback(action="subscriptions").pack()
        )
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "manage_subscription"))
async def manage_subscription(callback: CallbackQuery, callback_data: AdminCallback):
    """Управление конкретным каналом"""
    subscription_id = callback_data.target_id

    async with get_session() as session:
        result = await session.execute(
            select(RequiredSubscription).where(RequiredSubscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()

    if not subscription:
        await callback.answer("❌ Канал не найден", show_alert=True)
        return

    status_text = "🟢 Активен" if subscription.is_active else "🔴 Отключен"

    text = f"""📺 <b>УПРАВЛЕНИЕ КАНАЛОМ</b>

🏷️ <b>Название:</b> {subscription.display_name}
🔗 <b>Ссылка:</b> {subscription.channel_url}
📊 <b>Статус:</b> {status_text}
📅 <b>Добавлен:</b> {subscription.created_at.strftime('%d.%m.%Y %H:%M')}
👤 <b>Админ:</b> ID{subscription.created_by}
🔢 <b>Порядок:</b> {subscription.order_index}

⚙️ <b>Доступные действия:</b>"""

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()

    # Включение/отключение
    if subscription.is_active:
        builder.row(
            InlineKeyboardButton(
                text="🔴 Отключить",
                callback_data=AdminCallback(action="disable_subscription", target_id=subscription.id).pack()
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="🟢 Включить",
                callback_data=AdminCallback(action="enable_subscription", target_id=subscription.id).pack()
            )
        )

    # Изменение порядка
    builder.row(
        InlineKeyboardButton(
            text="⬆️ Поднять",
            callback_data=AdminCallback(action="move_subscription_up", target_id=subscription.id).pack()
        ),
        InlineKeyboardButton(
            text="⬇️ Опустить",
            callback_data=AdminCallback(action="move_subscription_down", target_id=subscription.id).pack()
        )
    )

    # Удаление
    builder.row(
        InlineKeyboardButton(
            text="❌ Удалить канал",
            callback_data=AdminCallback(action="delete_subscription", target_id=subscription.id).pack()
        )
    )

    # Назад
    builder.row(
        InlineKeyboardButton(
            text="⬅️ К списку каналов",
            callback_data=AdminCallback(action="list_subscriptions").pack()
        )
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "enable_subscription"))
async def enable_subscription(callback: CallbackQuery, callback_data: AdminCallback):
    """Включить канал"""
    subscription_id = callback_data.target_id

    async with get_session() as session:
        result = await session.execute(
            select(RequiredSubscription).where(RequiredSubscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.is_active = True
            await session.commit()

            await callback.answer("🟢 Канал включен")
            await manage_subscription(callback, callback_data)
        else:
            await callback.answer("❌ Канал не найден", show_alert=True)


@router.callback_query(AdminCallback.filter(F.action == "disable_subscription"))
async def disable_subscription(callback: CallbackQuery, callback_data: AdminCallback):
    """Отключить канал"""
    subscription_id = callback_data.target_id

    async with get_session() as session:
        result = await session.execute(
            select(RequiredSubscription).where(RequiredSubscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.is_active = False
            await session.commit()

            await callback.answer("🔴 Канал отключен")
            await manage_subscription(callback, callback_data)
        else:
            await callback.answer("❌ Канал не найден", show_alert=True)


@router.callback_query(AdminCallback.filter(F.action == "delete_subscription"))
async def delete_subscription_confirm(callback: CallbackQuery, callback_data: AdminCallback):
    """Подтверждение удаления канала"""
    subscription_id = callback_data.target_id

    async with get_session() as session:
        result = await session.execute(
            select(RequiredSubscription).where(RequiredSubscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()

    if not subscription:
        await callback.answer("❌ Канал не найден", show_alert=True)
        return

    text = f"""⚠️ <b>УДАЛЕНИЕ КАНАЛА</b>

📺 <b>Канал:</b> {subscription.display_name}
🔗 <b>Ссылка:</b> {subscription.channel_url}

Вы уверены, что хотите удалить этот канал из обязательных подписок?

❌ <b>Это действие необратимо!</b>"""

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=AdminCallback(action="delete_subscription_confirm", target_id=subscription.id).pack()
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=AdminCallback(action="manage_subscription", target_id=subscription.id).pack()
        )
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "delete_subscription_confirm"))
async def delete_subscription_final(callback: CallbackQuery, callback_data: AdminCallback):
    """Окончательное удаление канала"""
    subscription_id = callback_data.target_id

    async with get_session() as session:
        result = await session.execute(
            select(RequiredSubscription).where(RequiredSubscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            channel_name = subscription.display_name
            await session.delete(subscription)
            await session.commit()

            text = f"""✅ <b>КАНАЛ УДАЛЕН</b>

📺 Канал "{channel_name}" удален из обязательных подписок.

Пользователи больше не будут проверяться на подписку этого канала."""

            await callback.message.edit_text(
                text,
                reply_markup=get_admin_menu_keyboard()
            )
            await callback.answer("✅ Канал удален")
        else:
            await callback.answer("❌ Канал не найден", show_alert=True)


@router.callback_query(AdminCallback.filter(F.action.in_(["enable_all_subs", "disable_all_subs"])))
async def toggle_all_subscriptions(callback: CallbackQuery, callback_data: AdminCallback):
    """Включить/отключить все каналы"""
    enable = callback_data.action == "enable_all_subs"

    async with get_session() as session:
        result = await session.execute(select(RequiredSubscription))
        subscriptions = list(result.scalars().all())

        count = 0
        for subscription in subscriptions:
            if subscription.is_active != enable:
                subscription.is_active = enable
                count += 1

        await session.commit()

    action_text = "включены" if enable else "отключены"
    icon = "🟢" if enable else "🔴"

    await callback.answer(f"{icon} {count} каналов {action_text}")
    await show_subscriptions_menu(callback)


@router.callback_query(AdminCallback.filter(F.action == "subscription_stats"))
async def show_subscription_stats(callback: CallbackQuery):
    """Показать статистику подписок"""

    from app.services.telegram_api_service import TelegramAPIService
    telegram_api = TelegramAPIService()

    async with get_session() as session:
        # Получаем все каналы
        channels_result = await session.execute(
            select(RequiredSubscription)
            .order_by(RequiredSubscription.order_index, RequiredSubscription.id)
        )
        channels = list(channels_result.scalars().all())

        # Общая статистика пользователей
        total_users = await session.execute(select(func.count(User.id)))
        total_count = total_users.scalar() or 0

        # Активные пользователи за неделю
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_users_result = await session.execute(
            select(User.telegram_id)
            .where(
                and_(
                    User.is_active == True,
                    User.is_banned == False,
                    User.last_activity >= week_ago
                )
            )
        )
        active_users = [row[0] for row in active_users_result.fetchall()]

        # Админы (исключаем из проверки)
        admins_count = len([uid for uid in active_users if uid in settings.ADMIN_IDS])
        non_admin_users = [uid for uid in active_users if uid not in settings.ADMIN_IDS]

    if not channels:
        text = """📊 <b>СТАТИСТИКА ПОДПИСОК</b>

📭 Обязательные каналы не настроены.

Добавьте каналы для получения статистики."""

        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="➕ Добавить канал",
                callback_data=AdminCallback(action="add_subscription").pack()
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=AdminCallback(action="subscriptions").pack()
            )
        )

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
        return

    # Инициализируем сообщение о загрузке
    await callback.message.edit_text("📊 Загрузка статистики подписок...")

    channel_stats = []
    total_subscribed = 0
    total_checks = 0

    # Проверяем подписки для каждого канала
    for channel in channels:
        if not channel.is_active:
            continue

        subscribed_count = 0
        checked_count = 0

        # Проверяем подписки активных пользователей (не админов)
        for user_id in non_admin_users[:50]:  # Ограничиваем для производительности
            try:
                is_subscribed = await telegram_api.check_user_subscription(
                    user_id, channel.channel_url
                )
                checked_count += 1
                if is_subscribed:
                    subscribed_count += 1

                # Небольшая задержка чтобы не превысить лимиты API
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.warning(f"Failed to check subscription for user {user_id}: {e}")
                continue

        subscription_rate = (subscribed_count / checked_count * 100) if checked_count > 0 else 0

        channel_stats.append({
            'channel': channel,
            'subscribed': subscribed_count,
            'checked': checked_count,
            'rate': subscription_rate
        })

        total_subscribed += subscribed_count
        total_checks += checked_count

    # Получаем информацию о каналах
    for stat in channel_stats:
        try:
            channel_info = await telegram_api.get_chat_info(stat['channel'].channel_url)
            stat['member_count'] = channel_info.get('member_count', 0) if channel_info else 0
        except:
            stat['member_count'] = 0

    # Формируем текст статистики
    overall_rate = (total_subscribed / total_checks * 100) if total_checks > 0 else 0

    text = f"""📊 <b>СТАТИСТИКА ПОДПИСОК</b>

👥 <b>ОБЩИЕ ПОКАЗАТЕЛИ:</b>
├ Всего пользователей: {total_count:,}
├ Активных пользователей: {len(active_users):,}
├ Админов (не проверяются): {admins_count}
├ Проверено пользователей: {len(non_admin_users):,}
└ Общий уровень подписок: {overall_rate:.1f}%

📺 <b>ПО КАНАЛАМ:</b>"""

    active_channels = [s for s in channel_stats if s['channel'].is_active]

    if not active_channels:
        text += "\n📭 Нет активных каналов"
    else:
        for i, stat in enumerate(active_channels, 1):
            channel = stat['channel']
            subscribed = stat['subscribed']
            checked = stat['checked']
            rate = stat['rate']
            member_count = stat['member_count']

            text += f"\n\n{i}. <b>{channel.display_name}</b>"
            text += f"\n├ Подписано: {subscribed}/{checked} ({rate:.1f}%)"
            text += f"\n├ Участников в канале: {member_count:,}"
            text += f"\n└ Статус: {'🟢 Активен' if channel.is_active else '🔴 Отключен'}"

    # Анализ и рекомендации
    text += f"\n\n📈 <b>АНАЛИЗ:</b>"

    if overall_rate >= 90:
        text += "\n✅ Отличный уровень подписок!"
    elif overall_rate >= 70:
        text += "\n⚠️ Хороший уровень, но есть потери"
    elif overall_rate >= 50:
        text += "\n❌ Средний уровень, много отписок"
    else:
        text += "\n💥 Низкий уровень подписок!"

    if len(active_channels) > 3:
        text += "\n💡 Много каналов может снижать конверсию"

    # Рекомендации
    worst_channel = min(active_channels, key=lambda x: x['rate']) if active_channels else None
    if worst_channel and worst_channel['rate'] < 50:
        text += f"\n🔍 Проблемный канал: {worst_channel['channel'].display_name}"

    # Кнопки навигации и действий
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()

    # Обновить статистику
    builder.row(
        InlineKeyboardButton(
            text="🔄 Обновить статистику",
            callback_data=AdminCallback(action="subscription_stats").pack()
        )
    )

    # Детальная статистика по каналам
    if active_channels:
        builder.row(
            InlineKeyboardButton(
                text="📋 Детали по каналам",
                callback_data=AdminCallback(action="detailed_channel_stats").pack()
            )
        )

    # Экспорт данных
    builder.row(
        InlineKeyboardButton(
            text="📊 Экспорт CSV",
            callback_data=AdminCallback(action="export_subscription_stats").pack()
        )
    )

    # Назад
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=AdminCallback(action="subscriptions").pack()
        )
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "detailed_channel_stats"))
async def show_detailed_channel_stats(callback: CallbackQuery):
    """Показать детальную статистику по каналам"""

    from app.services.telegram_api_service import TelegramAPIService
    telegram_api = TelegramAPIService()

    await callback.message.edit_text("📊 Загрузка детальной статистики...")

    async with get_session() as session:
        # Получаем активные каналы
        channels_result = await session.execute(
            select(RequiredSubscription)
            .where(RequiredSubscription.is_active == True)
            .order_by(RequiredSubscription.order_index)
        )
        channels = list(channels_result.scalars().all())

        if not channels:
            text = "📭 Нет активных каналов для анализа"

            from aiogram.utils.keyboard import InlineKeyboardBuilder
            from aiogram.types import InlineKeyboardButton

            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=AdminCallback(action="subscription_stats").pack()
                )
            )

            await callback.message.edit_text(text, reply_markup=builder.as_markup())
            await callback.answer()
            return

        # Получаем пользователей
        users_result = await session.execute(
            select(User.telegram_id, User.username, User.level)
            .where(
                and_(
                    User.is_active == True,
                    User.is_banned == False
                )
            )
            .limit(30)  # Ограничиваем для производительности
        )
        users = list(users_result.fetchall())
        non_admin_users = [u for u in users if u.telegram_id not in settings.ADMIN_IDS]

    text = f"""📊 <b>ДЕТАЛЬНАЯ СТАТИСТИКА</b>

👥 Проверено пользователей: {len(non_admin_users)}
📺 Активных каналов: {len(channels)}

📈 <b>ПОДРОБНОСТИ ПО КАНАЛАМ:</b>"""

    for i, channel in enumerate(channels, 1):
        # Получаем информацию о канале
        try:
            channel_info = await telegram_api.get_chat_info(channel.channel_url)
            member_count = channel_info.get('member_count', 0) if channel_info else 0
        except:
            member_count = 0

        # Считаем подписки (упрощенная версия для примера)
        subscribed_count = 0
        total_checked = min(len(non_admin_users), 20)  # Проверяем только первых 20

        for user in non_admin_users[:20]:
            try:
                is_subscribed = await telegram_api.check_user_subscription(
                    user.telegram_id, channel.channel_url
                )
                if is_subscribed:
                    subscribed_count += 1
                await asyncio.sleep(0.05)  # Небольшая задержка
            except:
                continue

        subscription_rate = (subscribed_count / total_checked * 100) if total_checked > 0 else 0

        text += f"\n\n{i}. <b>{channel.display_name}</b>"
        text += f"\n├ 📊 Подписано: {subscribed_count}/{total_checked} ({subscription_rate:.1f}%)"
        text += f"\n├ 👥 Участников: {member_count:,}"
        text += f"\n├ 📅 Добавлен: {channel.created_at.strftime('%d.%m.%Y')}"
        text += f"\n└ 🔗 Ссылка: {channel.channel_url}"

    # Анализ эффективности
    text += f"\n\n🎯 <b>АНАЛИЗ ЭФФЕКТИВНОСТИ:</b>"
    text += f"\n• Каналы упорядочены по приоритету"
    text += f"\n• Первые каналы критически важны"
    text += f"\n• Рекомендуется ≥80% подписок"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data=AdminCallback(action="detailed_channel_stats").pack()
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="⬅️ К общей статистике",
            callback_data=AdminCallback(action="subscription_stats").pack()
        )
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "export_subscription_stats"))
async def export_subscription_stats(callback: CallbackQuery):
    """Экспорт статистики подписок"""

    current_time = datetime.utcnow().strftime('%d.%m.%Y %H:%M')

    async with get_session() as session:
        # Получаем данные
        channels_result = await session.execute(
            select(RequiredSubscription)
            .order_by(RequiredSubscription.order_index)
        )
        channels = list(channels_result.scalars().all())

        users_count = await session.execute(select(func.count(User.id)))
        total_users = users_count.scalar() or 0

    # Формируем CSV-подобные данные в текстовом виде
    export_text = f"""📊 <b>ЭКСПОРТ СТАТИСТИКИ ПОДПИСОК</b>

📅 <b>Дата экспорта:</b> {current_time}
👥 <b>Всего пользователей:</b> {total_users:,}
📺 <b>Всего каналов:</b> {len(channels)}

📋 <b>ДАННЫЕ ПО КАНАЛАМ:</b>

| № | Канал | Статус | Ссылка |
|---|-------|--------|--------|"""

    for i, channel in enumerate(channels, 1):
        status = "Активен" if channel.is_active else "Отключен"
        export_text += f"\n| {i} | {channel.display_name} | {status} | {channel.channel_url} |"

    export_text += f"\n\n📈 <b>НАСТРОЙКИ ЭКСПОРТА:</b>"
    export_text += f"\n• Формат: Текстовая таблица"
    export_text += f"\n• Кодировка: UTF-8"
    export_text += f"\n• Источник: PR GRAM Bot Admin Panel"

    export_text += f"\n\n💡 <i>Для полного CSV экспорта обратитесь к разработчику</i>"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📋 Скопировать данные",
            callback_data="copy_export_data"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к статистике",
            callback_data=AdminCallback(action="subscription_stats").pack()
        )
    )

    await callback.message.edit_text(export_text, reply_markup=builder.as_markup())
    await callback.answer("📊 Данные экспортированы")

# =============================================================================
# СИСТЕМНЫЕ ФУНКЦИИ
# =============================================================================

@router.callback_query(AdminCallback.filter(F.action == "system"))
async def show_system_functions(callback: CallbackQuery):
    """Показать системные функции"""
    
    text = """⚙️ <b>СИСТЕМНЫЕ ФУНКЦИИ</b>

🛠️ <b>ДОСТУПНЫЕ ДЕЙСТВИЯ:</b>
• Очистка истекших чеков
• Очистка истекших заданий
• Обновление уровней пользователей
• Массовая рассылка
• Резервное копирование

⚠️ <b>ВНИМАНИЕ:</b>
Системные функции влияют на всех пользователей!
Используйте осторожно."""
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🧹 Очистить истекшие",
            callback_data=AdminCallback(action="cleanup").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="📢 Массовая рассылка",
            callback_data=AdminCallback(action="broadcast").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬆️ Обновить уровни",
            callback_data=AdminCallback(action="update_levels").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="📊 Экспорт данных",
            callback_data=AdminCallback(action="export_data").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в админку",
            callback_data=AdminCallback(action="menu").pack()
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "cleanup"))
async def system_cleanup(
    callback: CallbackQuery,
    check_service: CheckService
):
    """Системная очистка"""
    
    # Очистка истекших чеков
    expired_checks = await check_service.cleanup_expired_checks()
    
    # Очистка истекших выполнений заданий
    expired_executions = 0
    async with get_session() as session:
        # Находим истекшие выполнения
        expired_time = datetime.utcnow() - timedelta(hours=24)
        result = await session.execute(
            select(TaskExecution).where(
                and_(
                    TaskExecution.status == ExecutionStatus.PENDING,
                    TaskExecution.created_at < expired_time
                )
            )
        )
        
        for execution in result.scalars():
            execution.status = ExecutionStatus.EXPIRED
            expired_executions += 1
        
        await session.commit()
    
    text = f"""🧹 <b>СИСТЕМНАЯ ОЧИСТКА ЗАВЕРШЕНА</b>

📊 <b>РЕЗУЛЬТАТЫ:</b>
├ Истекших чеков удалено: {expired_checks}
├ Истекших выполнений: {expired_executions}
└ Освобождено средств: автоматически

✅ Система очищена от устаревших данных."""
    
    await callback.answer("🧹 Очистка выполнена")
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard()
    )

@router.callback_query(AdminCallback.filter(F.action == "broadcast"))
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начать массовую рассылку"""
    
    await state.set_state(AdminStates.entering_broadcast_message)
    
    text = """📢 <b>МАССОВАЯ РАССЫЛКА</b>

Введите сообщение для рассылки:

⚠️ <b>ВНИМАНИЕ:</b>
• Сообщение будет отправлено ВСЕМ пользователям
• Используйте разметку HTML
• Максимум 4096 символов

💡 <b>Доступна разметка:</b>
• <code>&lt;b&gt;жирный&lt;/b&gt;</code>
• <code>&lt;i&gt;курсив&lt;/i&gt;</code>
• <code>&lt;code&gt;код&lt;/code&gt;</code>

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await callback.message.edit_text(text)
    await callback.answer()

@router.message(AdminStates.entering_broadcast_message)
async def process_broadcast(
    message: Message,
    state: FSMContext
):
    """Обработать массовую рассылку"""
    broadcast_text = message.text
    
    if len(broadcast_text) > 4096:
        await message.answer("❌ Сообщение слишком длинное (максимум 4096 символов)")
        return
    
    # Подтверждение рассылки
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Отправить всем",
            callback_data="confirm_broadcast"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel_broadcast"
        )
    )
    
    await state.update_data(broadcast_message=broadcast_text)
    
    preview_text = f"""📢 <b>ПОДТВЕРЖДЕНИЕ РАССЫЛКИ</b>

<b>Сообщение для отправки:</b>

{broadcast_text}

⚠️ <b>Это сообщение будет отправлено ВСЕМ пользователям!</b>"""
    
    await message.answer(preview_text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "confirm_broadcast")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Подтвердить и выполнить рассылку"""
    
    data = await state.get_data()
    broadcast_message = data.get('broadcast_message')
    
    if not broadcast_message:
        await callback.answer("❌ Сообщение не найдено", show_alert=True)
        await state.clear()
        return
    
    # Получаем всех активных пользователей
    async with get_session() as session:
        result = await session.execute(
            select(User.telegram_id).where(
                and_(
                    User.is_active == True,
                    User.is_banned == False
                )
            )
        )
        user_ids = [row[0] for row in result.fetchall()]
    
    # Начинаем рассылку
    await callback.message.edit_text(
        f"📤 <b>РАССЫЛКА ЗАПУЩЕНА</b>\n\nОтправка {len(user_ids):,} пользователям..."
    )
    
    sent_count = 0
    failed_count = 0
    
    for user_id in user_ids:
        try:
            await callback.bot.send_message(
                chat_id=user_id,
                text=broadcast_message,
                parse_mode="HTML"
            )
            sent_count += 1
            
            # Небольшая задержка чтобы не превысить лимиты
            if sent_count % 30 == 0:
                import asyncio
                await asyncio.sleep(1)
                
        except Exception:
            failed_count += 1
            continue
    
    result_text = f"""✅ <b>РАССЫЛКА ЗАВЕРШЕНА</b>

📊 <b>РЕЗУЛЬТАТЫ:</b>
├ Отправлено: {sent_count:,}
├ Не доставлено: {failed_count:,}
└ Всего попыток: {len(user_ids):,}

📈 Успешность: {(sent_count/len(user_ids)*100 if user_ids else 0):.1f}%"""
    
    await callback.message.edit_text(
        result_text,
        reply_markup=get_admin_menu_keyboard()
    )
    
    await state.clear()
    await callback.answer("✅ Рассылка завершена")

@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отменить рассылку"""
    await state.clear()
    
    await callback.message.edit_text(
        "❌ <b>РАССЫЛКА ОТМЕНЕНА</b>",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer("❌ Рассылка отменена")

@router.callback_query(AdminCallback.filter(F.action == "update_levels"))
async def update_user_levels(callback: CallbackQuery, user_service: UserService):
    """Обновить уровни всех пользователей"""
    
    updated_count = 0
    
    async with get_session() as session:
        # Получаем всех пользователей
        result = await session.execute(select(User))
        users = list(result.scalars().all())
        
        for user in users:
            old_level = user.level
            
            # Пересчитываем уровень
            if user.balance >= settings.LEVEL_THRESHOLDS["premium"]:
                new_level = "premium"
            elif user.balance >= settings.LEVEL_THRESHOLDS["gold"]:
                new_level = "gold"
            elif user.balance >= settings.LEVEL_THRESHOLDS["silver"]:
                new_level = "silver"
            else:
                new_level = "bronze"
            
            if old_level != new_level:
                user.level = new_level
                updated_count += 1
        
        await session.commit()
    
    text = f"""⬆️ <b>ОБНОВЛЕНИЕ УРОВНЕЙ ЗАВЕРШЕНО</b>

📊 Обновлено пользователей: {updated_count:,}

Все уровни пересчитаны согласно текущим балансам."""
    
    await callback.answer(f"⬆️ Обновлено {updated_count} уровней")
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard()
    )

@router.callback_query(AdminCallback.filter(F.action == "export_data"))
async def export_system_data(callback: CallbackQuery):
    """Экспорт системных данных"""
    
    async with get_session() as session:
        # Основная статистика
        stats = {
            'users': await session.execute(select(func.count(User.id))),
            'tasks': await session.execute(select(func.count(Task.id))),
            'executions': await session.execute(select(func.count(TaskExecution.id))),
            'transactions': await session.execute(select(func.count(Transaction.id)))
        }
        
        export_time = datetime.utcnow().strftime('%d.%m.%Y %H:%M')
        
        export_text = f"""📊 <b>ЭКСПОРТ СИСТЕМНЫХ ДАННЫХ</b>

📅 <b>Дата экспорта:</b> {export_time}

📈 <b>ОСНОВНЫЕ ПОКАЗАТЕЛИ:</b>
├ Пользователей: {stats['users'].scalar():,}
├ Заданий: {stats['tasks'].scalar():,}
├ Выполнений: {stats['executions'].scalar():,}
└ Транзакций: {stats['transactions'].scalar():,}

💾 <b>Формат:</b> Текстовый отчет
🔐 <b>Доступ:</b> Только администраторы

💡 <i>Для полного экспорта в CSV/JSON обратитесь к разработчику</i>"""
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="⬅️ Назад к системным функциям",
                callback_data=AdminCallback(action="system").pack()
            )
        )
        
        await callback.message.edit_text(export_text, reply_markup=builder.as_markup())
        await callback.answer("📊 Данные экспортированы")

# =============================================================================
# ОБРАБОТЧИКИ ОТМЕНЫ
# =============================================================================

class SomeState(StatesGroup):
    some_state = State()

@router.message(F.text.in_(["❌ Отмена", "/cancel"]), StateFilter(SomeState.some_state))
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено")