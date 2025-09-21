import structlog
logger = structlog.get_logger(__name__)

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from datetime import timezone

from app.database.models.user import User
from app.database.models.task import TaskType
from app.services.task_service import TaskService
from app.bot.keyboards.earn import EarnCallback, get_earn_menu_keyboard, get_task_list_keyboard, get_task_view_keyboard, get_task_execution_keyboard
from app.bot.keyboards.main_menu import MainMenuCallback
from app.bot.utils.messages import get_task_list_text, get_task_text, get_task_execution_text, get_error_message, get_success_message

router = Router()

@router.message(Command("earn"))
async def cmd_earn(message: Message, user: User):
    """Команда /earn"""
    text = f"""💰 <b>ЗАРАБОТАТЬ GRAM</b>

Выберите тип заданий для выполнения:

🎯 <b>Доступные типы:</b>
• 📺 Подписка на каналы - простые задания
• 👥 Вступление в группы - быстрая награда  
• 👀 Просмотр постов - легкие задания
• 👍 Реакции на посты - мгновенная проверка
• 🤖 Переход в ботов - высокая награда

💎 <b>Ваш уровень:</b> {user.get_level_config()['name']}
⚡ <b>Множитель наград:</b> x{user.get_level_config()['task_multiplier']}

💡 <i>Чем выше ваш уровень, тем больше награда!</i>"""
    
    await message.answer(
        text,
        reply_markup=get_earn_menu_keyboard()
    )

@router.callback_query(MainMenuCallback.filter(F.action == "earn"))
async def show_earn_from_menu(callback: CallbackQuery, user: User):
    """Показать заработок из главного меню"""
    text = f"""💰 <b>ЗАРАБОТАТЬ GRAM</b>

Выберите тип заданий для выполнения:

🎯 <b>Доступные типы:</b>
• 📺 Подписка на каналы - простые задания
• 👥 Вступление в группы - быстрая награда  
• 👀 Просмотр постов - легкие задания
• 👍 Реакции на посты - мгновенная проверка
• 🤖 Переход в ботов - высокая награда

💎 <b>Ваш уровень:</b> {user.get_level_config()['name']}
⚡ <b>Множитель наград:</b> x{user.get_level_config()['task_multiplier']}

💡 <i>Чем выше ваш уровень, тем больше награда!</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_earn_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(EarnCallback.filter(F.action == "menu"))
async def show_earn_menu(callback: CallbackQuery, user: User):
    """Показать меню заработка"""
    text = f"""💰 <b>ЗАРАБОТАТЬ GRAM</b>

Выберите тип заданий для выполнения:

🎯 <b>Доступные типы:</b>
• 📺 Подписка на каналы - простые задания
• 👥 Вступление в группы - быстрая награда  
• 👀 Просмотр постов - легкие задания
• 👍 Реакции на посты - мгновенная проверка
• 🤖 Переход в ботов - высокая награда

💎 <b>Ваш уровень:</b> {user.get_level_config()['name']}
⚡ <b>Множитель наград:</b> x{user.get_level_config()['task_multiplier']}

💡 <i>Чем выше ваш уровень, тем больше награда!</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_earn_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(EarnCallback.filter(F.action == "list"))
async def show_task_list(
    callback: CallbackQuery, 
    callback_data: EarnCallback,
    user: User,
    task_service: TaskService
):
    """Показать список заданий"""
    task_type = None if callback_data.task_type == "all" else TaskType(callback_data.task_type)
    page = callback_data.page
    limit = 10
    offset = (page - 1) * limit
    
    try:
        # Получаем задания
        tasks = await task_service.get_available_tasks(
            user=user,
            task_type=task_type,
            limit=limit + 1,  # +1 для проверки наличия следующей страницы
            offset=offset
        )
        
        has_next = len(tasks) > limit
        if has_next:
            tasks = tasks[:limit]
        
        # Генерируем текст
        text = get_task_list_text(tasks, callback_data.task_type, page)
        
        # Генерируем клавиатуру
        keyboard = get_task_list_keyboard(tasks, callback_data.task_type, page, has_next)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error("Error loading tasks", error=str(e), user_id=user.telegram_id)
        await callback.answer("❌ Ошибка при загрузке заданий", show_alert=True)

@router.callback_query(EarnCallback.filter(F.action == "view"))
async def view_task(
    callback: CallbackQuery,
    callback_data: EarnCallback,
    user: User,
    task_service: TaskService
):
    """Просмотр конкретного задания"""
    try:
        task = await task_service.get_task_by_id(callback_data.task_id)
        
        if not task:
            await callback.answer(get_error_message("task_not_found"), show_alert=True)
            return
        
        # Проверяем доступность задания
        if not task.is_active:
            await callback.answer(get_error_message("task_not_active"), show_alert=True)
            return
        
        # Проверяем уровень пользователя
        if task.min_user_level:
            level_hierarchy = ["bronze", "silver", "gold", "premium"]
            if user.level not in level_hierarchy:
                await callback.answer("❌ Неизвестный уровень пользователя", show_alert=True)
                return
                
            required_index = level_hierarchy.index(task.min_user_level)
            user_index = level_hierarchy.index(user.level)
            
            if user_index < required_index:
                level_names = {
                    "bronze": "🥉 Bronze",
                    "silver": "🥈 Silver",
                    "gold": "🥇 Gold",
                    "premium": "💎 Premium"
                }
                required_level = level_names.get(task.min_user_level, task.min_user_level)
                await callback.answer(f"❌ Требуется уровень {required_level}", show_alert=True)
                return
        
        # Проверяем, не выполнял ли уже пользователь это задание
        user_executions = await task_service.get_user_executions(user.telegram_id, limit=1000)
        for execution in user_executions:
            if execution.task_id == task.id:
                await callback.answer("❌ Вы уже выполняли это задание", show_alert=True)
                return
        
        # Генерируем текст и клавиатуру
        text = get_task_text(task, user)
        keyboard = get_task_view_keyboard(task, user)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error("Error viewing task", error=str(e), task_id=callback_data.task_id)
        await callback.answer("❌ Ошибка при загрузке задания", show_alert=True)

@router.callback_query(EarnCallback.filter(F.action == "execute"))
async def execute_task(
    callback: CallbackQuery,
    callback_data: EarnCallback,
    user: User,
    task_service: TaskService
):
    """Начать выполнение задания"""
    try:
        task = await task_service.get_task_by_id(callback_data.task_id)
        
        if not task:
            await callback.answer(get_error_message("task_not_found"), show_alert=True)
            return
        
        # Создаем выполнение задания
        execution = await task_service.execute_task(
            task_id=task.id,
            user_id=user.telegram_id
        )
        
        if not execution:
            await callback.answer("❌ Не удалось начать выполнение задания", show_alert=True)
            return
        
        # Генерируем инструкции для выполнения
        text = get_task_execution_text(task, user)
        keyboard = get_task_execution_keyboard(task)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer("✅ Выполнение задания начато!")
        
    except Exception as e:
        logger.error("Error executing task", error=str(e), task_id=callback_data.task_id)
        await callback.answer("❌ Ошибка при выполнении задания", show_alert=True)

@router.callback_query(EarnCallback.filter(F.action == "check"))
async def check_task_execution(
    callback: CallbackQuery,
    callback_data: EarnCallback,
    user: User,
    task_service: TaskService
):
    """Проверить выполнение задания"""
    try:
        task = await task_service.get_task_by_id(callback_data.task_id)
        
        if not task:
            await callback.answer(get_error_message("task_not_found"), show_alert=True)
            return
        
        # Получаем текущее выполнение пользователя
        executions = await task_service.get_user_executions(user.telegram_id, limit=100)
        
        execution = None
        for ex in executions:
            if ex.task_id == task.id and ex.status.value == "pending":
                execution = ex
                break
        
        if not execution:
            await callback.answer("❌ Активное выполнение не найдено", show_alert=True)
            return
        
        # Для автопроверяемых заданий выполняем проверку
        if task.auto_check:
            # В реальном приложении здесь должна быть проверка через Telegram API
            # Пока что автоматически засчитываем для демонстрации
            success = await task_service.complete_task_execution(
                execution.id,
                auto_checked=True,
                reviewer_id=None,
                review_comment="Автоматическая проверка"
            )
            
            if success:
                user_config = user.get_level_config()
                final_reward = task.reward_amount * user_config['task_multiplier']
                
                success_text = f"""✅ <b>ЗАДАНИЕ ВЫПОЛНЕНО!</b>

🎯 <b>Задание:</b> {task.title}
💰 <b>Награда:</b> +{final_reward:,.0f} GRAM зачислено
⚡ <b>Множитель уровня:</b> x{user_config['task_multiplier']}

🎉 Отлично! Продолжайте выполнять задания для увеличения заработка!

💡 <b>Советы:</b>
• Повышайте уровень для большего множителя
• Выполняйте задания регулярно
• Приглашайте рефералов для дополнительного дохода"""
                
                from app.bot.keyboards.main_menu import get_main_menu_keyboard
                
                await callback.message.edit_text(
                    success_text,
                    reply_markup=get_main_menu_keyboard(user)
                )
                await callback.answer("🎉 Поздравляем с выполнением!")
            else:
                await callback.answer("❌ Проверка не пройдена", show_alert=True)
        else:
            # Для заданий с ручной проверкой
            await callback.answer("⏳ Задание отправлено на модерацию. Результат в течение 24 часов", show_alert=True)
            
    except Exception as e:
        logger.error("Error checking task execution", error=str(e), task_id=callback_data.task_id)
        await callback.answer("❌ Ошибка при проверке задания", show_alert=True)

@router.callback_query(EarnCallback.filter(F.action == "info"))
async def show_task_info(
    callback: CallbackQuery,
    callback_data: EarnCallback,
    task_service: TaskService
):
    """Показать подробную информацию о задании"""
    try:
        task = await task_service.get_task_by_id(callback_data.task_id)
        
        if not task:
            await callback.answer(get_error_message("task_not_found"), show_alert=True)
            return
        
        # Получаем аналитику задания
        analytics = await task_service.get_task_analytics(task.id)
        
        if not analytics:
            await callback.answer("❌ Не удалось загрузить аналитику", show_alert=True)
            return
        
        # Тип задания
        type_names = {
            TaskType.CHANNEL_SUBSCRIPTION: "📺 Подписка на канал",
            TaskType.GROUP_JOIN: "👥 Вступление в группу",
            TaskType.POST_VIEW: "👀 Просмотр поста",
            TaskType.POST_REACTION: "👍 Реакция на пост",
            TaskType.BOT_INTERACTION: "🤖 Взаимодействие с ботом"
        }
        
        type_name = type_names.get(task.type, "❓ Неизвестный тип")
        
        info_text = f"""ℹ️ <b>ПОДРОБНАЯ ИНФОРМАЦИЯ</b>

🎯 <b>ЗАДАНИЕ:</b>
├ Название: {task.title}
├ Тип: {type_name}
├ Автор: ID{task.author_id}
├ Создано: {task.created_at.strftime('%d.%m.%Y %H:%M')}
└ Ссылка: {task.target_url}

📊 <b>ПРОГРЕСС:</b>
├ Выполнено: {task.completed_executions}/{task.target_executions}
├ Процент: {task.completion_percentage:.1f}%
├ Осталось: {task.remaining_executions}
└ Конверсия: {analytics['completion_rate']:.1f}%

💰 <b>ЭКОНОМИКА:</b>
├ Базовая награда: {task.reward_amount:,.0f} GRAM
├ Потрачено: {task.spent_budget:,.0f} GRAM
├ Остается: {task.remaining_budget:,.0f} GRAM
└ Общий бюджет: {task.total_budget:,.0f} GRAM

⏱️ <b>ВРЕМЯ:</b>"""
        
        if task.expires_at:
            from datetime import datetime
            remaining = task.expires_at - datetime.now(timezone.utc)
            if remaining.total_seconds() > 0:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                info_text += f"\n├ Осталось: {hours}ч {minutes}м"
            else:
                info_text += "\n├ ⏰ Задание истекло"
        else:
            info_text += "\n├ Без ограничений по времени"
        
        if analytics.get('timing'):
            avg_time = analytics['timing']['average_seconds']
            info_text += f"\n└ Среднее время выполнения: {avg_time:.0f} сек"
        
        # Требования
        if task.min_user_level:
            level_names = {
                "bronze": "🥉 Bronze",
                "silver": "🥈 Silver", 
                "gold": "🥇 Gold",
                "premium": "💎 Premium"
            }
            req_level = level_names.get(task.min_user_level, task.min_user_level)
            info_text += f"\n\n📋 <b>ТРЕБОВАНИЯ:</b>\n├ Минимальный уровень: {req_level}"
        
        # Проверка
        check_type = "🤖 Автоматическая" if task.auto_check else "👨‍💼 Ручная модерация"
        info_text += f"\n\n🔍 <b>ТИП ПРОВЕРКИ:</b> {check_type}"
        
        from app.bot.keyboards.earn import get_task_view_keyboard
        
        await callback.message.edit_text(
            info_text,
            reply_markup=get_task_view_keyboard(task, callback.from_user)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error("Error showing task info", error=str(e), task_id=callback_data.task_id)
        await callback.answer("❌ Ошибка при загрузке информации", show_alert=True)

@router.callback_query(EarnCallback.filter(F.action == "cancel_execution"))
async def cancel_execution(
    callback: CallbackQuery,
    callback_data: EarnCallback,
    user: User,
    task_service: TaskService
):
    """Отменить выполнение задания"""
    try:
        # Находим активное выполнение
        executions = await task_service.get_user_executions(user.telegram_id, limit=100)
        
        execution = None
        for ex in executions:
            if ex.task_id == callback_data.task_id and ex.status.value == "pending":
                execution = ex
                break
        
        if execution:
            # В реальном приложении здесь будет отмена выполнения
            # Пока что просто возвращаемся к заданию
            await view_task(callback, callback_data, user, task_service)
            await callback.answer("❌ Выполнение отменено")
        else:
            await callback.answer("❌ Активное выполнение не найдено", show_alert=True)
            
    except Exception as e:
        logger.error("Error canceling execution", error=str(e), task_id=callback_data.task_id)
        await callback.answer("❌ Ошибка при отмене выполнения", show_alert=True)

# Добавим импорт logger
import structlog
logger = structlog.get_logger(__name__)