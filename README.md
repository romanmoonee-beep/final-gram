# 🤖 PR GRAM Bot

Современный Telegram бот для взаимного продвижения каналов с поддержкой **Telegram Stars** платежей.

## 🌟 Возможности

### 💰 **Зарабатывайте GRAM**
- Подписывайтесь на каналы
- Вступайте в группы
- Просматривайте посты
- Ставьте реакции
- Взаимодействуйте с ботами

### 📢 **Продвигайте проекты**
- Создавайте задания любого типа
- Настраивайте целевую аудиторию
- Получайте быстрые результаты
- Детальная аналитика

### 🎁 **Реферальная система**
- Многоуровневые доходы
- Бонусы за активность рефералов
- Проценты с пополнений

### ⭐ **Telegram Stars интеграция**
- Безопасные платежи
- Мгновенное зачисление
- Бонусная система

## 🏗 Архитектура

### **Backend**
- **Python 3.12+** с современным async/await
- **SQLAlchemy 2.0+** для работы с БД
- **Aiogram 3.7+** для Telegram API
- **Redis** для кэширования и FSM
- **PostgreSQL** как основная БД

### **Структура проекта**
```
app/
├── bot/              # Telegram бот
│   ├── handlers/     # Обработчики сообщений
│   ├── keyboards/    # Клавиатуры
│   ├── middlewares/  # Промежуточные обработчики
│   ├── states/       # FSM состояния
│   └── utils/        # Утилиты
├── database/         # Модели и БД
│   └── models/       # SQLAlchemy модели
├── services/         # Бизнес-логика
├── config/           # Конфигурация
└── cli/              # CLI команды
```

## 🚀 Быстрый старт

### 1. **Клонирование репозитория**
```bash
git clone https://github.com/your-username/pr-gram-bot.git
cd pr-gram-bot
```

### 2. **Установка зависимостей**

**С Poetry (рекомендуется):**
```bash
poetry install
poetry shell
```

**С pip:**
```bash
pip install -r requirements.txt
```

### 3. **Настройка окружения**
```bash
cp .env.example .env
# Отредактируйте .env файл
```

**Минимальные настройки:**
```env
BOT_TOKEN=your_bot_token_from_botfather
DB_PASSWORD=your_database_password
ADMIN_IDS=your_telegram_id
```

### 4. **Запуск с Docker (рекомендуется)**
```bash
docker-compose up -d postgres redis  # Только БД
# или
docker-compose up -d  # Полный стек
```

### 5. **Инициализация базы данных**
```bash
python -m app.cli.database init
python -m app.cli.database upgrade
python -m app.cli.database seed  # Тестовые данные
```

### 6. **Запуск бота**
```bash
python -m app.main
```

## ⚙️ Конфигурация

### **Переменные окружения**

| Переменная | Описание | Обязательная |
|------------|----------|--------------|
| `BOT_TOKEN` | Токен бота от @BotFather | ✅ |
| `DB_PASSWORD` | Пароль БД PostgreSQL | ✅ |
| `ADMIN_IDS` | ID администраторов через запятую | ✅ |
| `SECRET_KEY` | Секретный ключ для подписи | ✅ |
| `DEBUG` | Режим отладки | ❌ |
| `WEBHOOK_URL` | URL для webhook (продакшн) | ❌ |

### **Уровни пользователей**

| Уровень | Порог | Комиссия | Множитель | Лимит заданий |
|---------|-------|----------|-----------|---------------|
| 🥉 Bronze | 0 GRAM | 7% | 1.0x | 5/день |
| 🥈 Silver | 10K GRAM | 6% | 1.2x | 15/день |
| 🥇 Gold | 50K GRAM | 5% | 1.35x | 30/день |
| 💎 Premium | 100K GRAM | 3% | 1.5x | ∞ |

## 🛠 CLI команды

```bash
# Управление БД
python -m app.cli.database status     # Статус БД
python -m app.cli.database migrate "описание"  # Создать миграцию
python -m app.cli.database upgrade    # Применить миграции
python -m app.cli.database seed       # Тестовые данные
python -m app.cli.database reset      # Сброс БД (осторожно!)
```

## 📊 Мониторинг

### **Логирование**
- Структурированные логи с `structlog`
- Разные уровни для разработки/продакшн
- Интеграция с Sentry

### **Метрики**
```bash
docker-compose --profile monitoring up  # Запуск Prometheus + Grafana
```
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## 🔧 Разработка

### **Структура базы данных**

```sql
-- Пользователи
users (telegram_id, balance, level, referrer_id, ...)

-- Задания  
tasks (id, author_id, type, reward_amount, status, ...)

-- Выполнения заданий
task_executions (id, task_id, user_id, status, ...)

-- Транзакции
transactions (id, user_id, amount, type, ...)
```

### **Добавление новых обработчиков**

1. Создайте файл в `app/bot/handlers/`
2. Зарегистрируйте в `app/bot/handlers/__init__.py`
3. Добавьте состояния в `app/bot/states/` если нужно
4. Создайте клавиатуры в `app/bot/keyboards/`

### **Тестирование**
pytest                    # Запуск тестов
pytest --cov             # С покрытием кода
black .                  # Форматирование
isort .                  # Сортировка импортов
mypy app/                # Проверка типов
```

## 🚀 Деплой

### **Docker (рекомендуется)**
```bash
# Продакшн
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# С мониторингом
docker-compose --profile monitoring up -d
```

### **Переменные для продакшн**
```env
DEBUG=false
ENVIRONMENT=production
WEBHOOK_URL=https://yourdomain.com
SENTRY_DSN=https://your-sentry-dsn
```

## 📋 Чек-лист запуска

- [ ] Создан бот в @BotFather
- [ ] Настроены переменные окружения
- [ ] Запущена PostgreSQL БД
- [ ] Запущен Redis
- [ ] Применены миграции БД
- [ ] Бот добавлен в админы (если нужно)
- [ ] Настроен домен для webhook (продакшн)
- [ ] Настроен мониторинг (опционально)

## 🆘 Поддержка

### **Частые проблемы**

**Ошибки подключения к БД:**
```bash
# Проверьте статус
python -m app.cli.database status

# Пересоздайте БД
python -m app.cli.database reset --force
```

**Проблемы с миграциями:**
```bash
# Откатите и примените заново
python -m app.cli.database downgrade base
python -m app.cli.database upgrade
```

### **Логи**
```bash
# Посмотреть логи Docker
docker-compose logs -f bot

# Логи приложения
tail -f logs/app.log
```

## 📄 Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## 🤝 Контрибьюция

1. Fork репозитория
2. Создайте feature branch
3. Сделайте commit изменений
4. Создайте Pull Request

---

**Сделано с ❤️ ZOPH**# final-gram
