from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, desc, or_

from app.database.models.user import User
from app.database.models.task import Task, TaskStatus
from app.database.models.task_execution import TaskExecution, ExecutionStatus
from app.database.models.transaction import Transaction, TransactionType
from app.services.user_service import UserService
from app.services.task_service import TaskService
from app.services.transaction_service import TransactionService
from app.services.check_service import CheckService
from app.bot.keyboards.admin import (
    AdminCallback, get_admin_menu_keyboard, get_moderation_keyboard,
    get_task_moderation_keyboard, get_user_management_keyboard
)
from app.bot.keyboards.main_menu import MainMenuCallback, get_main_menu_keyboard
from app.bot.states.admin_states import AdminStates
from app.bot.filters.admin import AdminFilter
from app.config.settings import settings
from app.database.database import get_session

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
└ Уровень: {user.level.value}

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
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

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
        
        name = type_names.get(tx_type, tx_type.value)
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

@router.message(F.text.in_(["❌ Отмена", "/cancel"]), state="*")
async def cancel_admin_action(message: Message, state: FSMContext):
    """Отмена админского действия"""
    await state.clear()
    
    await message.answer(
        "❌ Действие отменено",
        reply_markup=get_admin_menu_keyboard()
    )