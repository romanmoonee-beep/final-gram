# app/bot/middlewares/subscription.py
from typing import Callable, Dict, Any, Awaitable

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from app.database.database import get_session
from app.database.models.required_subscription import RequiredSubscription
from app.services.telegram_api_service import TelegramAPIService
from app.config.settings import settings

logger = structlog.get_logger(__name__)

class SubscriptionMiddleware(BaseMiddleware):
    """Middleware для проверки обязательных подписок"""
    
    def __init__(self):
        self.telegram_api = TelegramAPIService()
        self.subscription_enabled = True  # Будем получать из настроек
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        
        # Проверяем админов - им проверка не нужна
        if user_id in settings.ADMIN_IDS:
            return await handler(event, data)
        
        # Команды, которые всегда разрешены
        allowed_commands = ['/start', '/check_subscription']
        
        if isinstance(event, Message) and event.text:
            if any(event.text.startswith(cmd) for cmd in allowed_commands):
                return await handler(event, data)
        
        # Callback'и проверки подписок всегда разрешены
        if isinstance(event, CallbackQuery) and event.data:
            if event.data.startswith(('check_subscription', 'subscribe_')):
                return await handler(event, data)
        
        # Получаем настройки подписок
        async with get_session() as session:
            result = await session.execute(
                select(RequiredSubscription)
                .where(RequiredSubscription.is_active == True)
                .order_by(RequiredSubscription.order_index)
            )
            required_channels = list(result.scalars().all())
        
        # Если нет обязательных каналов, пропускаем проверку
        if not required_channels:
            return await handler(event, data)
        
        # Проверяем подписки
        unsubscribed_channels = []
        
        for channel in required_channels:
            is_subscribed = await self.telegram_api.check_user_subscription(
                user_id, channel.channel_url
            )
            
            if not is_subscribed:
                unsubscribed_channels.append(channel)
        
        # Если есть неподписанные каналы, показываем сообщение
        if unsubscribed_channels:
            await self._send_subscription_message(event, unsubscribed_channels)
            return
        
        # Все проверки пройдены, выполняем обработчик
        return await handler(event, data)
    
    async def _send_subscription_message(
        self, 
        event: Message | CallbackQuery, 
        channels: list[RequiredSubscription]
    ):
        """Отправить сообщение о необходимости подписки"""
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        
        text = """🔒 <b>ОБЯЗАТЕЛЬНАЯ ПОДПИСКА</b>

Для использования бота необходимо подписаться на наши каналы:

"""
        
        builder = InlineKeyboardBuilder()
        
        # Добавляем кнопки каналов
        for i, channel in enumerate(channels, 1):
            text += f"{i}. {channel.display_name}\n"
            
            builder.row(
                InlineKeyboardButton(
                    text=f"📺 {channel.display_name}",
                    url=channel.channel_url
                )
            )
        
        # Кнопка проверки
        builder.row(
            InlineKeyboardButton(
                text="✅ Проверить подписки",
                callback_data="check_subscription"
            )
        )
        
        text += "\n💡 <i>После подписки нажмите \"Проверить подписки\"</i>"
        
        if isinstance(event, Message):
            await event.answer(text, reply_markup=builder.as_markup())
        elif isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=builder.as_markup())
            await event.answer("🔒 Требуется подписка на каналы")

# Обработчик проверки подписок
from aiogram import Router, F
from aiogram.types import CallbackQuery

subscription_router = Router()

@subscription_router.callback_query(F.data == "check_subscription")
async def check_subscriptions(callback: CallbackQuery):
    """Проверить подписки пользователя"""
    user_id = callback.from_user.id
    telegram_api = TelegramAPIService()
    
    # Получаем обязательные каналы
    async with get_session() as session:
        result = await session.execute(
            select(RequiredSubscription)
            .where(RequiredSubscription.is_active == True)
            .order_by(RequiredSubscription.order_index)
        )
        required_channels = list(result.scalars().all())
    
    if not required_channels:
        await callback.answer("✅ Нет обязательных подписок", show_alert=True)
        return
    
    # Проверяем подписки
    unsubscribed = []
    
    for channel in required_channels:
        is_subscribed = await telegram_api.check_user_subscription(
            user_id, channel.channel_url
        )
        
        if not is_subscribed:
            unsubscribed.append(channel)
    
    if unsubscribed:
        # Есть неподписанные каналы
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        
        text = "❌ <b>ВЫ НЕ ПОДПИСАНЫ НА:</b>\n\n"
        
        builder = InlineKeyboardBuilder()
        
        for channel in unsubscribed:
            text += f"• {channel.display_name}\n"
            builder.row(
                InlineKeyboardButton(
                    text=f"📺 {channel.display_name}",
                    url=channel.channel_url
                )
            )
        
        builder.row(
            InlineKeyboardButton(
                text="🔄 Проверить снова",
                callback_data="check_subscription"
            )
        )
        
        text += "\n💡 <i>Подпишитесь и проверьте снова</i>"
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer("❌ Не все подписки оформлены")
    else:
        # Все подписки оформлены
        from app.bot.keyboards.main_menu import get_main_menu_keyboard
        from app.services.user_service import UserService
        
        user_service = UserService()
        user = await user_service.get_user(user_id)
        
        text = """✅ <b>ПОДПИСКИ ОФОРМЛЕНЫ!</b>

Спасибо за подписку! Теперь вы можете пользоваться всеми функциями бота.

💰 Начните зарабатывать GRAM уже сейчас!"""
        
        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard(user)
        )
        await callback.answer("✅ Все подписки оформлены!")