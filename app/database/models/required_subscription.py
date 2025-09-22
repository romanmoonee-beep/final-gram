# app/database/models/required_subscription.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database.database import Base

class RequiredSubscription(Base):
    """Модель обязательных подписок"""
    __tablename__ = "required_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_username = Column(String(100), nullable=False)  # @username или ссылка
    channel_title = Column(String(200), nullable=True)  # Название канала
    channel_url = Column(String(300), nullable=False)  # Полная ссылка
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)  # Порядок отображения
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, nullable=False)  # ID админа
    
    def __repr__(self):
        return f"<RequiredSubscription {self.channel_username}>"
    
    @property
    def display_name(self):
        return self.channel_title or self.channel_username