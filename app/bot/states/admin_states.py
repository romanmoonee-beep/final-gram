"""Состояния для админской панели"""

from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    """Состояния админской панели"""
    
    # =============================================================================
    # МОДЕРАЦИЯ ЗАДАНИЙ
    # =============================================================================
    
    # Модерация выполнений
    reviewing_task = State()
    entering_reject_reason = State()
    entering_review_comment = State()
    
    # Массовые действия с заданиями
    confirming_mass_approval = State()
    selecting_moderation_criteria = State()
    
    # =============================================================================
    # УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
    # =============================================================================
    
    # Поиск пользователей
    entering_user_id = State()
    entering_username = State()
    
    # Блокировка/разблокировка
    entering_ban_reason = State()
    confirming_unban = State()
    
    # Управление балансом
    entering_bonus_amount = State()
    entering_balance_operation = State()
    confirming_balance_change = State()
    entering_freeze_amount = State()
    entering_unfreeze_amount = State()
    
    # Отправка сообщений пользователю
    entering_user_message = State()
    confirming_user_message = State()
    
    # Массовые операции
    selecting_mass_operation = State()
    confirming_mass_operation = State()
    entering_mass_bonus_amount = State()
    
    # =============================================================================
    # РАССЫЛКИ И УВЕДОМЛЕНИЯ
    # =============================================================================
    
    # Массовые рассылки
    entering_broadcast_message = State()
    confirming_broadcast = State()
    selecting_broadcast_audience = State()
    entering_broadcast_schedule = State()
    
    # Персональные уведомления
    entering_notification_text = State()
    selecting_notification_type = State()
    
    # =============================================================================
    # СИСТЕМНЫЕ ФУНКЦИИ
    # =============================================================================
    
    # Подтверждения системных операций
    confirming_action = State()
    confirming_cleanup = State()
    confirming_level_update = State()
    confirming_backup = State()
    
    # Экспорт данных
    selecting_export_format = State()
    entering_export_parameters = State()
    confirming_export = State()
    
    # Настройки системы
    entering_setting_value = State()
    confirming_setting_change = State()
    
    # =============================================================================
    # АНАЛИТИКА И ОТЧЕТЫ
    # =============================================================================
    
    # Создание отчетов
    selecting_report_type = State()
    entering_report_parameters = State()
    selecting_report_period = State()
    confirming_report_generation = State()
    
    # Фильтры для аналитики
    entering_date_range = State()
    selecting_analytics_filters = State()
    
    # =============================================================================
    # ЛОГИ И МОНИТОРИНГ
    # =============================================================================
    
    # Просмотр логов
    selecting_log_period = State()
    filtering_logs = State()
    confirming_log_cleanup = State()
    
    # Мониторинг системы
    setting_monitoring_alerts = State()
    configuring_health_checks = State()
    
    # =============================================================================
    # НАСТРОЙКИ БОТА
    # =============================================================================
    
    # Настройки GRAM
    editing_gram_settings = State()
    entering_min_task_reward = State()
    entering_max_task_reward = State()
    entering_commission_rates = State()
    
    # Настройки уровней
    editing_level_thresholds = State()
    entering_level_benefits = State()
    confirming_level_changes = State()
    
    # Настройки заданий
    editing_task_settings = State()
    entering_task_timeout = State()
    entering_task_limits = State()
    
    # Настройки платежей
    editing_payment_settings = State()
    entering_stars_packages = State()
    entering_crypto_settings = State()
    
    # Настройки безопасности
    editing_security_settings = State()
    entering_rate_limits = State()
    entering_fraud_detection = State()
    
    # =============================================================================
    # СПЕЦИАЛЬНЫЕ СОСТОЯНИЯ
    # =============================================================================
    
    # Импорт/Экспорт
    uploading_import_file = State()
    processing_import = State()
    confirming_import = State()
    
    # Резервное копирование
    selecting_backup_options = State()
    confirming_backup_restore = State()
    
    # Техническое обслуживание
    entering_maintenance_message = State()
    confirming_maintenance_mode = State()
    
    # Разработчикам
    entering_sql_query = State()
    confirming_dangerous_operation = State()
    entering_custom_script = State()
    
    # =============================================================================
    # СОСТОЯНИЯ ДЛЯ МУЛЬТИШАГОВОГО ПРОЦЕССА
    # =============================================================================
    
    # Создание сложных отчетов
    report_step_1_type = State()
    report_step_2_period = State()
    report_step_3_filters = State()
    report_step_4_format = State()
    report_step_5_confirmation = State()
    
    # Настройка автоматизации
    automation_step_1_trigger = State()
    automation_step_2_conditions = State()
    automation_step_3_actions = State()
    automation_step_4_schedule = State()
    automation_step_5_confirmation = State()
    
    # Миграция данных
    migration_step_1_source = State()
    migration_step_2_mapping = State()
    migration_step_3_validation = State()
    migration_step_4_execution = State()
    
    # =============================================================================
    # ВСПОМОГАТЕЛЬНЫЕ СОСТОЯНИЯ
    # =============================================================================
    
    # Ожидание подтверждения
    waiting_confirmation = State()
    waiting_file_upload = State()
    waiting_user_input = State()
    
    # Обработка
    processing_request = State()
    generating_report = State()
    executing_operation = State()
    
    # Завершение
    operation_completed = State()
    displaying_results = State()
    
    # =============================================================================
    # СОСТОЯНИЯ ДЛЯ ИНТЕГРАЦИЙ
    # =============================================================================
    
    # Настройка Telegram API
    entering_bot_token = State()
    testing_bot_connection = State()
    configuring_webhooks = State()
    
    # Настройка внешних API
    entering_api_credentials = State()
    testing_api_connection = State()
    configuring_api_limits = State()
    
    # Настройка баз данных
    entering_db_connection = State()
    testing_db_connection = State()
    configuring_db_settings = State()
    
    # =============================================================================
    # DEBUG И РАЗРАБОТКА
    # =============================================================================
    
    # Режим отладки
    debug_entering_command = State()
    debug_viewing_state = State()
    debug_testing_feature = State()
    
    # Тестирование
    test_selecting_module = State()
    test_entering_parameters = State()
    test_running_tests = State()
    
    # Профилирование
    profiler_selecting_target = State()
    profiler_running_analysis = State()
    profiler_viewing_results = State()