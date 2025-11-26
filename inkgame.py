import discord
from discord.ext import commands
from discord import app_commands
import random
import os
import re
import aiohttp
import asyncio
import json
import logging
import threading
from typing import Optional, cast
from dotenv import load_dotenv
from flask import Flask
import datetime
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

# Загрузка переменных окружения
load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Система переводов
TRANSLATIONS = {
    'ru': {
        # Команда language
        'language_set': '🌐 Язык установлен на русский!',
        'language_current': 'Текущий язык: русский',
        
        # Общие сообщения
        'command_server_only': '❌ Эта команда работает только на сервере',
        'error_occurred': '❌ Произошла ошибка',
        'processing_command': '🔄 Обработка команды...',
        'registration_system': 'Система регистрации',
        'unknown_server': 'Неизвестный сервер',
        'yes': 'ДА',
        'no': 'НЕТ',
        'and_more_errors': 'и еще {count} ошибок',
        'price_label': 'Цена',
        'status': 'Статус',
        'view': 'Просмотр',
        'you_are_already_participating': 'Вы уже участвуете в событии',
        'all_numbers_taken_description': 'Все номера распределены',
        
        # Команда register
        'registration_success': '✅ РЕГИСТРАЦИЯ УСПЕШНА',
        'registration_closed': '🚫 Регистрация закрыта',
        'all_spots_taken': '🎯 Все места заняты',
        'already_registered': '⚠️ Уже зарегистрирован',
        'wait_for_registration': 'Ожидайте открытия регистрации администратором',
        'registration_completed': 'Регистрация завершена, все {max_players} мест распределены',
        'all_numbers_taken': '❌ Ошибка системы: Все номера распределены',
        'welcome_to_game': 'Добро пожаловать в игру...\n\nОжидайте начало игры...\n**Номер {number}**',
        'your_game_number': '🎫 Ваш игровой номер',
        'your_spot': '📊 Ваше место в списке',
        'status_registered': '```Зарегистрирован```',
        'important_info': '💡 Важная информация',
        'number_identifier': 'Во время события ваш номер будет вашим идентификатором',
        'role_creation_reason': 'Роль для зарегистрированных игроков',
        'role_creation_error': '❌ Ошибка прав доступа',
        'role_creation_error_desc': 'Не удалось создать роль',
        'role_assignment_error': '❌ Ошибка прав доступа',
        'role_assignment_error_desc': 'Не удалось выдать роль',
        
        # Команда status
        'registration_status': '📊 СТАТУС РЕГИСТРАЦИИ',
        'status_open': '🟢 ОТКРЫТА',
        'status_closed': '🔴 ЗАКРЫТА',
        'registration_active': 'Регистрация активна, можно присоединиться',
        'registration_inactive': 'Регистрация неактивна',
        'game_status_active': '🟢 АКТИВНА',
        'game_status_completed': '🔴 ЗАВЕРШЕНА',
        'event_in_progress': 'Событие в процессе',
        'event_completed': 'Событие завершено',
        'registration_status_label': '🎯 Статус регистрации',
        'game_status_label': '🎮 Статус игры',
        'registered_players': '👥 Зарегистрировано',
        'available_spots': '🎫 Свободных мест',
        'used_numbers': '🔢 Использовано номеров',
        'players': 'игроков',
        'spots': 'мест',
        'out_of': 'из',
        'join_now': '🎮 Присоединиться',
        'use_register_command': 'Используйте команду `/register` для регистрации',
        
        # Команда start
        'registration_opened': '🎮 РЕГИСТРАЦИЯ ОТКРЫТА',
        'players_can_join': 'Игроки теперь могут присоединиться к событию',
        'statistics': '📊 Статистика',
        'available_spots_info': 'Доступно мест: {available}/{max}',
        'number_range': 'Диапазон номеров: {min:03d}-{max:03d}',
        'check_status': '📋 Проверить статус',
        'use_status_command': '```/status```',
        
        # Команда end
        'registration_already_closed': '🎮 ИГРА УЖЕ ЗАВЕРШЕНА',
        'game_already_completed': 'Событие уже было завершено ранее',
        'registration_closed_title': '🔒 РЕГИСТРАЦИЯ ЗАКРЫТА',
        'registration_closed_desc': 'Новые игроки не могут присоединиться. Игра продолжается для зарегистрированных участников.',
        'next_step': '💡 Следующий шаг',
        'use_end_again': 'Для полного завершения события используйте команду `/end` еще раз',
        'game_completing': '⏳ ЗАВЕРШЕНИЕ ИГРЫ',
        'game_completing_desc': 'Идет процесс завершения... Начисление денег и сброс данных',
        'progress': '📊 Прогресс',
        'processing_players': 'Обработка игроков...',
        'game_completed': '🎮 ИГРА ЗАВЕРШЕНА',
        'game_completed_desc': 'Событие полностью завершено, все данные сброшены',
        'completion_results': '📊 Результаты завершения',
        'successfully_reset': 'Успешно сброшено: {reset}/{total} игроков',
        'money_sent': 'Деньги начислены: {sent}/{total}',
        'rewards': '💰 Награды',
        'each_received': 'Каждый участник получил **{amount:,}$**',
        'prizes_top3': '🏆 Призы за первые три места',
        'completed_actions': '🔄 Выполненные действия',
        'actions_list': '• Регистрация закрыта\n• Игра завершена\n• Роли удалены\n• Ники восстановлены\n• Данные очищены\n• Деньги начислены\n• 🏆 Титулы сохранены',
        'role_remove_errors': '⚠️ Ошибки удаления ролей',
        'role_remove_failed': 'Не удалось убрать роль у {count} игроков',
        'nick_restore_errors': '⚠️ Ошибки восстановления ников',
        'nick_restore_failed': 'Не удалось восстановить ники у {count} игроков',
        'money_errors': '⚠️ Ошибки начисления денег',
        'prize_errors': '⚠️ Ошибки распределения призов',
        
        # Команда server_info
        'server_settings': '⚙️ НАСТРОЙКИ СЕРВЕРА',
        'server_config': 'Конфигурация для **{server}**',
        'limits': '📊 Лимиты',
        'limits_info': '• Макс. игроков: `{max_players}`\n• Диапазон номеров: `{min:03d}-{max:03d}`\n• Награда за участие: `{reward:,}$`',
        'status_info': '🎮 Статус',
        'status_details': '• Регистрация: `{reg_status}`\n• Игра: `{game_status}`\n• Призы выданы: `{prizes_status}`',
        'statistics_info': '📈 Статистика',
        'stats_details': '• Зарегистрировано: `{registered}/{max_players}`\n• Использовано номеров: `{used_numbers}`\n• Титулов выдано: `{titles}`',
        'management': '🔧 Управление',
        'management_commands': 'Используйте команды:\n• `/players <число>` - изменить макс. игроков\n• `/reward <сумма>` - изменить награду\n• `/start` - открыть регистрацию\n• `/end` - завершить игру',
        
        # Команда players
        'max_players_changed': '✅ МАКСИМАЛЬНОЕ ЧИСЛО ИГРОКОВ ИЗМЕНЕНО',
        'new_max_players': 'Установлено новое максимальное количество игроков для сервера **{server}**',
        'was': '📊 Было',
        'now': '📈 Стало',
        'current_stats': '🎯 Текущая статистика',
        'registered_info': 'Зарегистрировано: {current}/{max}',
        
        # Команда reward
        'reward_changed': '💰 НАГРАДА ИЗМЕНЕНА',
        'new_reward_set': 'Установлена новая награда за участие для сервера **{server}**',
        'reward_info': 'Эта награда будет выдана каждому участнику при завершении игры командой `/end`',
        
        # Титулы
        'titles_shop': '🏆 МАГАЗИН ТИТУЛОВ',
        'titles_desc': 'Приобретите уникальный титул для отображения в лидерборде!',
        'free_reward': '🎁 Бесплатно (выдается админами)',
        'price': '💵 {price:,}$',
        'purchased': '✅ Куплен',
        'available': '🛒 Доступен',
        'how_to_buy': '🛒 Как купить',
        'use_buy_command': 'Используйте команду `/buy <название_титула>` для покупки',
        'inventory': '🎒 Инвентарь',
        'use_inv_command': 'Используйте `/inv` для просмотра ваших титулов',
        'equip_title': '👑 Надеть титул',
        'use_equip_command': 'Используйте `/equip <титул>` чтобы надеть титул',
        
        # Команда equip
        'no_titles': '❌ Ошибка: У вас нет титулов',
        'dont_have_title': '❌ Ошибка: У вас нет этого титула',
        'title_equipped': '👑 ТИТУЛ НАДЕТ',
        'equipped_success': 'Вы надели титул **{title}**!',
        'view_in_leaderboard': '👀 Просмотр: Теперь ваш титул отображается в лидерборде',
        
        # Команда inv
        'inventory_empty': '🎒 ИНВЕНТАРЬ ТИТУЛОВ: У вас пока нет титулов. Используйте `/titles` для покупки.',
        'inventory_title': '🎒 ИНВЕНТАРЬ ТИТУЛОВ',
        'total_titles': 'Всего титулов: {count}',
        'equipped_title': '👑 Надетый титул',
        'no_equipped': '❌ Нет надетого титула',
        'your_titles': '📜 Ваши титулы',
        'unequip_title': '❌ Снять титул',
        'use_unequip_command': 'Используйте `/unequip` чтобы снять текущий титул',
        
        # Команда unequip
        'no_equipped_title': '❌ Ошибка: У вас нет надетого титула',
        'title_unequipped': '❌ ТИТУЛ СНЯТ',
        'unequipped_success': 'Вы сняли титул **{title}**',
        'not_shown_leaderboard': '💡 Информация: Теперь в лидерборде ваш титул не отображается',
        
        # Команда buy
        'title_not_exist': '❌ Ошибка: Такого титула не существует. Используйте `/titles` для просмотра доступных титулов.',
        'already_have_title': '❌ Ошибка: У вас уже есть этот титул!',
        'balance_check_failed': '❌ Ошибка: Не удалось проверить баланс: {error}',
        'insufficient_funds': '❌ Недостаточно средств',
        'you_have_need': 'У вас {have:,}$, а нужно {need:,}$',
        'payment_error': '❌ Ошибка оплаты',
        'payment_failed': 'Не удалось списать средства: {error}',
        'title_purchased': '✅ ТИТУЛ ПРИОБРЕТЕН',
        'purchased_success': 'Вы успешно приобрели титул **{title}**!',
        'cost': '💵 Стоимость',
        'auto_equipped': '👑 Статус: Титул автоматически надет',
        'now_have_titles': '🎒 Инвентарь: Теперь у вас {count} титулов',
        'view_in_lb': '👀 Просмотр: Ваш титул теперь отображается в лидерборде',
        
        # Лидерборд
        'leaderboard': '📊 ЛИДЕРБОРД',
        'no_players': 'Пока нет зарегистрированных игроков',
        'players_by_registration': 'Игроки в порядке регистрации | {server}',
        'players_range': '🎮 Игроки ({start}-{end})',
        'no_data': 'Нет данных',
        'top3_prizes': '🏆 Призы за первые три места',
        'prizes_info': '🥇 1 место: **{first:,}$**\n🥈 2 место: **{second:,}$**\n🥉 3 место: **{third:,}$**',
        'page_info': 'Страница {current}/{total} • Лидерборд • {server}',
        
        # Команда cc
        'title_given': '🎁 ТИТУЛ ВЫДАН',
        'title_given_to': 'Игрок {user} получил титул **Контент Креэйтор**!',
        'special_title': 'Специальный титул',
        
        # Команда set_leaderboard
        'leaderboard_set': '✅ ЛИДЕРБОРД УСТАНОВЛЕН',
        'leaderboard_set_success': 'Сообщение лидерборда успешно установлено!',
        'auto_update_info': '📊 Автообновление: Лидерборд будет автоматически обновляться при:\n• Регистрации новых игроков\n• Покупке титулов\n• Смене титулов\n• Снятии титулов\n• Выдаче титулов админами',
        
        # Команда update_leaderboard
        'leaderboard_updated': '✅ ЛИДЕРБОРД ОБНОВЛЕН',
        'leaderboard_updated_success': 'Лидерборд успешно обновлен!',
        
        # Команда mytitle
        'your_title': '🏆 ВАШ ТИТУЛ',
        'no_equipped_yet': 'У вас пока нет надетого титула. Используйте `/titles` для покупки и `/equip` для надевания.',
        'total_titles_count': '🎒 Всего титулов',
        
        # Команда help
        'help_title': '📚 СПРАВКА ПО КОМАНДАМ',
        'all_players': '🎮 Для всех игроков',
        'all_players_commands': '`/register` - Зарегистрироваться\n`/status` - Статус регистрации\n`/mynumber` - Мой номер\n`/players_list` - Список участников\n`/ping` - Проверить пинг\n`/titles` - Магазин титулов\n`/buy` - Купить титул\n`/mytitle` - Мой титул\n`/leaderboard` - Таблица лидеров\n`/server_info` - Информация о сервере',
        'admin_commands': '⚙️ Для администраторов',
        'admin_commands_list': '`/start` - Открыть регистрацию\n`/end` - Завершить игру\n`/list` - Список игроков\n`/reset` - Сбросить игрока\n`/broadcast` - Рассылка\n`/changenumber` - Изменить номер\n`/freenumbers` - Свободные номера\n`/save` - Сохранить данные\n`/load` - Загрузить данные\n`/cc` - Выдать титул Контент Креэйтор\n`/backup` - Создать резервную копию\n`/restore` - Восстановить из копии\n`/players` - Установить макс. игроков\n`/reward` - Установить награду\n`/set_leaderboard` - Установить лидерборд\n`/update_leaderboard` - Обновить лидерборд\n`/language` - Установить язык',
        
        # Команда ping
        'pong': '🏓 PONG!',
        'latency': '📶 Задержка',
        'online_status': '🟢 Статус: ```Онлайн```',
        
        # Команда freenumbers
        'free_numbers': '🎫 СВОБОДНЫЕ НОМЕРА',
        'no_free_numbers': '❌ Свободных номеров нет',
        'available_count': 'Доступно: {count}',
        'showing_first_20': 'ℹ️ Показаны первые 20',
        'total_free': 'Всего свободно: {count} номеров',
        
        # Команда changenumber
        'player_not_registered': '❌ Игрок не зарегистрирован',
        'number_out_of_range': '❌ Номер должен быть от {min} до {max}',
        'number_changed': '🔢 НОМЕР ИЗМЕНЕН',
        'new_number_set': 'Игроку {user} установлен новый номер',
        'new_number': '🎫 Новый номер',
        
        # Команда backup
        'creating_backup': '🔄 Создаю резервную копию...',
        'manual_backup_created': '💾 РУЧНОЙ БЭКАП СОЗДАН',
        'backup_sent_to_channel': 'Бэкап данных успешно отправлен в канал',
        'backup_error': '❌ ОШИБКА БЭКАПА',
        'backup_failed': 'Не удалось создать бэкап. Проверьте настройки канала.',
        
        # Команда set_backup_channel
        'backup_channel_set': '✅ КАНАЛ ДЛЯ БЭКАПОВ УСТАНОВЛЕН',
        'backup_channel_desc': 'Этот канал будет использоваться для автоматических бэкапов данных',
        'auto_backups': '💾 Автоматические бэкапы: Бэкапы будут отправляться при:\n• Регистрации игроков\n• Покупке титулов\n• Изменении титулов\n• Завершении игры\n• Любых других изменениях данных',
        
        # Команда restore
        'checking_file': '🔄 Проверяю файл...',
        'wrong_format': '❌ ОШИБКА ФОРМАТА: Пожалуйста, загрузите файл в формате JSON',
        'file_read_error': '❌ ОШИБКА ЧТЕНИЯ: Не удалось прочитать файл. Убедитесь, что это валидный JSON файл.',
        'invalid_format': '❌ НЕВЕРНЫЙ ФОРМАТ: В файле отсутствуют обязательные поля: {fields}',
        'restore_warning': '⚠️ ПРЕДУПРЕЖДЕНИЕ',
        'restore_warning_desc': 'Вы собираетесь восстановить данные из резервной копии.\n\n**ВСЕ ТЕКУЩИЕ ДАННЫЕ БУДУТ ПЕРЕЗАПИСАНЫ!**\n\nЭто действие нельзя отменить.\nПожалуйста, подтвердите восстановление.',
        'restore_data_info': '📊 Данные для восстановления',
        'restore_players_count': '• Игроков: {players}\n• Номеров: {numbers}\n• Титулов: {titles}\n• Версия: {version}',
        'restore_action': '🔄 Действие: Нажмите кнопку ниже для подтверждения восстановления',
        'restore_confirm': '✅ Подтвердить восстановление',
        'restore_cancel': '❌ Отмена',
        'restore_cancelled': '❌ ВОССТАНОВЛЕНИЕ ОТМЕНЕНО: Действие отменено пользователем',
        'restoring_data': '🔄 ВОССТАНОВЛЕНИЕ ДАННЫХ: Идет процесс восстановления...',
        'data_restored': '✅ ДАННЫЕ ВОССТАНОВЛЕНЫ: Все данные успешно восстановлены из резервной копии!',
        'restored_data_info': '📊 Восстановленные данные',
        'restored_details': '• Игроков: {players}\n• Номеров: {numbers}\n• Титулов: {titles}\n• Регистрация: {reg_status}\n• Игра: {game_status}',
        'next_steps': '💡 Следующие шаги',
        'restore_next_steps': '• Проверьте корректность данных\n• Убедитесь, что лидерборд отображается правильно\n• При необходимости используйте `/update_leaderboard`',
        'restore_error': '❌ ОШИБКА ВОССТАНОВЛЕНИЯ: Не удалось восстановить данные из файла',
        'restore_exception': '❌ ОШИБКА ВОССТАНОВЛЕНИЯ: Произошла ошибка при восстановлении: {error}',
        
        # Команда broadcast
        'no_players_for_broadcast': '❌ Нет игроков для рассылки',
        'starting_broadcast': '📤 Начинаю рассылку для {count} игроков...',
        'announcement': '📢 ОБЪЯВЛЕНИЕ',
        'from_admin': 'От администратора • {admin}',
        'broadcast_results': '📊 РЕЗУЛЬТАТ РАССЫЛКИ',
        'successfully_sent': '✅ Успешно отправлено',
        'sent_to_players': '{count} игрокам',
        'broadcast_errors': '❌ Ошибки',
        
        # Команда players_list
        'participants': '👥 УЧАСТНИКИ',
        'registered_count': 'Зарегистрировано: {current}/{max} игроков',
        'first_players': '🎮 Игроки (первые {count})',
        
        # Команда mynumber
        'not_registered': '❌ Не зарегистрирован: Вы не зарегистрированы в игре',
        'your_number': '🎫 ВАШ НОМЕР: **Ваш игровой номер:** `{number}`',
        'number_usage': '💡 Информация: Этот номер будет вашим идентификатором во время события',
        
        # Команда list
        'players_list': '📝 СПИСОК ИГРОКОВ',
        'no_registered_players': 'На данный момент нет зарегистрированных игроков',
        'registered_players': '📋 ЗАРЕГИСТРИРОВАННЫЕ ИГРОКИ',
        'players_chunk': '🎯 Игроки {start}-{end}',
        'total_stats': '📊 Общая статистика',
        'total_players_info': 'Всего игроков: {current}/{max}',
        
        # Команда save
        'data_saved': '💾 ДАННЫЕ СОХРАНЕНЫ: Все данные игры успешно сохранены',
        'saved_by': '👤 Сохранил',
        'save_error': '❌ ОШИБКА СОХРАНЕНИЯ: Не удалось сохранить данные',
        
        # Команда load
        'data_loaded': '📂 ДАННЫЕ ЗАГРУЖЕНЫ: Данные игры успешно загружены',
        'load_error': '❌ ОШИБКА ЗАГРУЗКИ: Не удалось загрузить данные',
        
        # Команда sync
        'sync_success': '✅ СИНХРОНИЗАЦИЯ УСПЕШНА: Загружено {count} команд',
        'sync_error': '❌ ОШИБКА СИНХРОНИЗАЦИИ: Ошибка: {error}',
        
        # Команда reset
        'player_not_in_system': '❌ Ошибка: {user} не зарегистрирован в системе',
        'registration_reset': '🔄 РЕГИСТРАЦИЯ СБРОШЕНА: Регистрация игрока {user} была успешно отменена',
        
        # Автоматические бэкапы
        'auto_backup': '💾 АВТОМАТИЧЕСКИЙ БЭКАП',
        'auto_backup_desc': 'Создан автоматический бэкап данных игры для сервера **{server}**',
        'server_stats': '📊 Статистика сервера',
        'server_stats_info': '• Игроков: {players}\n• Номеров: {numbers}\n• Титулов: {titles}\n• Регистрация: {reg_status}\n• Игра: {game_status}',
        'server_settings_info': '⚙️ Настройки сервера',
        'server_settings_details': '• Макс. игроков: {max_players}\n• Награда: {reward:,}$\n• Номера: {min:03d}-{max:03d}',
        'creation_time': '🕐 Время создания',
        'auto_backup_system': 'Автоматическая система бэкапов • {server}',
        
        # Призы
        'not_enough_players': 'Недостаточно игроков для распределения призов',
        'prizes_already_distributed': 'Призы уже были распределены ранее',
    },
    'en': {
        # Language command
        'language_set': '🌐 Language set to English!',
        'language_current': 'Current language: English',
        
        # Common messages
        'command_server_only': '❌ This command only works on a server',
        'error_occurred': '❌ An error occurred',
        'processing_command': '🔄 Processing command...',
        'registration_system': 'Registration system',
        'unknown_server': 'Unknown server',
        'yes': 'YES',
        'no': 'NO',
        'and_more_errors': 'and {count} more errors',
        'price_label': 'Price',
        'status': 'Status',
        'view': 'View',
        'you_are_already_participating': 'You are already participating in the event',
        'all_numbers_taken_description': 'All numbers are taken',
        
        # Register command
        'registration_success': '✅ REGISTRATION SUCCESSFUL',
        'registration_closed': '🚫 Registration closed',
        'all_spots_taken': '🎯 All spots taken',
        'already_registered': '⚠️ Already registered',
        'wait_for_registration': 'Wait for administrator to open registration',
        'registration_completed': 'Registration completed, all {max_players} spots are taken',
        'all_numbers_taken': '❌ System error: All numbers are taken',
        'welcome_to_game': 'Welcome to the game...\n\nWait for the game to start...\n**Number {number}**',
        'your_game_number': '🎫 Your game number',
        'your_spot': '📊 Your spot in list',
        'status_registered': '```Registered```',
        'important_info': '💡 Important information',
        'number_identifier': 'During the event, your number will be your identifier',
        'role_creation_reason': 'Role for registered players',
        'role_creation_error': '❌ Permission error',
        'role_creation_error_desc': 'Failed to create role',
        'role_assignment_error': '❌ Permission error',
        'role_assignment_error_desc': 'Failed to assign role',
        
        # Status command
        'registration_status': '📊 REGISTRATION STATUS',
        'status_open': '🟢 OPEN',
        'status_closed': '🔴 CLOSED',
        'registration_active': 'Registration active, you can join',
        'registration_inactive': 'Registration inactive',
        'game_status_active': '🟢 ACTIVE',
        'game_status_completed': '🔴 COMPLETED',
        'event_in_progress': 'Event in progress',
        'event_completed': 'Event completed',
        'registration_status_label': '🎯 Registration status',
        'game_status_label': '🎮 Game status',
        'registered_players': '👥 Registered',
        'available_spots': '🎫 Available spots',
        'used_numbers': '🔢 Used numbers',
        'players': 'players',
        'spots': 'spots',
        'out_of': 'out of',
        'join_now': '🎮 Join now',
        'use_register_command': 'Use `/register` command to register',
        
        # Start command
        'registration_opened': '🎮 REGISTRATION OPENED',
        'players_can_join': 'Players can now join the event',
        'statistics': '📊 Statistics',
        'available_spots_info': 'Available spots: {available}/{max}',
        'number_range': 'Number range: {min:03d}-{max:03d}',
        'check_status': '📋 Check status',
        'use_status_command': '```/status```',
        
        # End command
        'registration_already_closed': '🎮 GAME ALREADY COMPLETED',
        'game_already_completed': 'The event was already completed earlier',
        'registration_closed_title': '🔒 REGISTRATION CLOSED',
        'registration_closed_desc': 'New players cannot join. The game continues for registered participants.',
        'next_step': '💡 Next step',
        'use_end_again': 'To completely finish the event, use the `/end` command again',
        'game_completing': '⏳ COMPLETING GAME',
        'game_completing_desc': 'Completion in progress... Adding money and resetting data',
        'progress': '📊 Progress',
        'processing_players': 'Processing players...',
        'game_completed': '🎮 GAME COMPLETED',
        'game_completed_desc': 'Event completely finished, all data reset',
        'completion_results': '📊 Completion results',
        'successfully_reset': 'Successfully reset: {reset}/{total} players',
        'money_sent': 'Money sent: {sent}/{total}',
        'rewards': '💰 Rewards',
        'each_received': 'Each participant received **{amount:,}$**',
        'prizes_top3': '🏆 Prizes for top 3',
        'completed_actions': '🔄 Completed actions',
        'actions_list': '• Registration closed\n• Game completed\n• Roles removed\n• Nicknames restored\n• Data cleared\n• Money added\n• 🏆 Titles saved',
        'role_remove_errors': '⚠️ Role removal errors',
        'role_remove_failed': 'Failed to remove role from {count} players',
        'nick_restore_errors': '⚠️ Nickname restore errors',
        'nick_restore_failed': 'Failed to restore nicknames for {count} players',
        'money_errors': '⚠️ Money adding errors',
        'prize_errors': '⚠️ Prize distribution errors',
        
        # Server info command
        'server_settings': '⚙️ SERVER SETTINGS',
        'server_config': 'Configuration for **{server}**',
        'limits': '📊 Limits',
        'limits_info': '• Max players: `{max_players}`\n• Number range: `{min:03d}-{max:03d}`\n• Participation reward: `{reward:,}$`',
        'status_info': '🎮 Status',
        'status_details': '• Registration: `{reg_status}`\n• Game: `{game_status}`\n• Prizes distributed: `{prizes_status}`',
        'statistics_info': '📈 Statistics',
        'stats_details': '• Registered: `{registered}/{max_players}`\n• Numbers used: `{used_numbers}`\n• Titles given: `{titles}`',
        'management': '🔧 Management',
        'management_commands': 'Use commands:\n• `/players <number>` - change max players\n• `/reward <amount>` - change reward\n• `/start` - open registration\n• `/end` - finish game',
        
        # Players command
        'max_players_changed': '✅ MAX PLAYERS CHANGED',
        'new_max_players': 'Set new maximum player count for server **{server}**',
        'was': '📊 Was',
        'now': '📈 Now',
        'current_stats': '🎯 Current statistics',
        'registered_info': 'Registered: {current}/{max}',
        
        # Reward command
        'reward_changed': '💰 REWARD CHANGED',
        'new_reward_set': 'Set new participation reward for server **{server}**',
        'reward_info': 'This reward will be given to each participant when finishing the game with `/end`',
        
        # Titles
        'titles_shop': '🏆 TITLES SHOP',
        'titles_desc': 'Buy unique title to display in leaderboard!',
        'free_reward': '🎁 Free (given by admins)',
        'price': '💵 {price:,}$',
        'purchased': '✅ Purchased',
        'available': '🛒 Available',
        'how_to_buy': '🛒 How to buy',
        'use_buy_command': 'Use `/buy <title_name>` command to buy',
        'inventory': '🎒 Inventory',
        'use_inv_command': 'Use `/inv` to view your titles',
        'equip_title': '👑 Equip title',
        'use_equip_command': 'Use `/equip <title>` to equip title',
        
        # Equip command
        'no_titles': '❌ Error: You have no titles',
        'dont_have_title': '❌ Error: You don\'t have this title',
        'title_equipped': '👑 TITLE EQUIPPED',
        'equipped_success': 'You equipped title **{title}**!',
        'view_in_leaderboard': '👀 View: Your title is now displayed in leaderboard',
        
        # Inv command
        'inventory_empty': '🎒 TITLES INVENTORY: You have no titles yet. Use `/titles` to buy.',
        'inventory_title': '🎒 TITLES INVENTORY',
        'total_titles': 'Total titles: {count}',
        'equipped_title': '👑 Equipped title',
        'no_equipped': '❌ No equipped title',
        'your_titles': '📜 Your titles',
        'unequip_title': '❌ Unequip title',
        'use_unequip_command': 'Use `/unequip` to unequip current title',
        
        # Unequip command
        'no_equipped_title': '❌ Error: You have no equipped title',
        'title_unequipped': '❌ TITLE UNEQUIPPED',
        'unequipped_success': 'You unequipped title **{title}**',
        'not_shown_leaderboard': '💡 Information: Your title is no longer shown in leaderboard',
        
        # Buy command
        'title_not_exist': '❌ Error: This title doesn\'t exist. Use `/titles` to view available titles.',
        'already_have_title': '❌ Error: You already have this title!',
        'balance_check_failed': '❌ Error: Failed to check balance: {error}',
        'insufficient_funds': '❌ Insufficient funds',
        'you_have_need': 'You have {have:,}$, but need {need:,}$',
        'payment_error': '❌ Payment error',
        'payment_failed': 'Failed to deduct funds: {error}',
        'title_purchased': '✅ TITLE PURCHASED',
        'purchased_success': 'You successfully purchased title **{title}**!',
        'cost': '💵 Cost',
        'auto_equipped': '👑 Status: Title automatically equipped',
        'now_have_titles': '🎒 Inventory: Now you have {count} titles',
        'view_in_lb': '👀 View: Your title is now displayed in leaderboard',
        
        # Leaderboard
        'leaderboard': '📊 LEADERBOARD',
        'no_players': 'No registered players yet',
        'players_by_registration': 'Players by registration order | {server}',
        'players_range': '🎮 Players ({start}-{end})',
        'no_data': 'No data',
        'top3_prizes': '🏆 Prizes for top 3',
        'prizes_info': '🥇 1st place: **{first:,}$**\n🥈 2nd place: **{second:,}$**\n🥉 3rd place: **{third:,}$**',
        'page_info': 'Page {current}/{total} • Leaderboard • {server}',
        
        # CC command
        'title_given': '🎁 TITLE GIVEN',
        'title_given_to': 'Player {user} received title **Content Creator**!',
        'special_title': 'Special title',
        
        # Set leaderboard command
        'leaderboard_set': '✅ LEADERBOARD SET',
        'leaderboard_set_success': 'Leaderboard message successfully set!',
        'auto_update_info': '📊 Auto-update: Leaderboard will automatically update on:\n• New player registrations\n• Title purchases\n• Title changes\n• Title unequips\n• Title gives by admins',
        
        # Update leaderboard command
        'leaderboard_updated': '✅ LEADERBOARD UPDATED',
        'leaderboard_updated_success': 'Leaderboard successfully updated!',
        
        # Mytitle command
        'your_title': '🏆 YOUR TITLE',
        'no_equipped_yet': 'You have no equipped title yet. Use `/titles` to buy and `/equip` to equip.',
        'total_titles_count': '🎒 Total titles',
        
        # Help command
        'help_title': '📚 COMMAND HELP',
        'all_players': '🎮 For all players',
        'all_players_commands': '`/register` - Register\n`/status` - Registration status\n`/mynumber` - My number\n`/players_list` - Participants list\n`/ping` - Check ping\n`/titles` - Titles shop\n`/buy` - Buy title\n`/mytitle` - My title\n`/leaderboard` - Leaderboard\n`/server_info` - Server information',
        'admin_commands': '⚙️ For administrators',
        'admin_commands_list': '`/start` - Open registration\n`/end` - Finish game\n`/list` - Players list\n`/reset` - Reset player\n`/broadcast` - Broadcast\n`/changenumber` - Change number\n`/freenumbers` - Free numbers\n`/save` - Save data\n`/load` - Load data\n`/cc` - Give Content Creator title\n`/backup` - Create backup\n`/restore` - Restore from backup\n`/players` - Set max players\n`/reward` - Set reward\n`/set_leaderboard` - Set leaderboard\n`/update_leaderboard` - Update leaderboard\n`/language` - Set language',
        
        # Ping command
        'pong': '🏓 PONG!',
        'latency': '📶 Latency',
        'online_status': '🟢 Status: ```Online```',
        
        # Freenumbers command
        'free_numbers': '🎫 FREE NUMBERS',
        'no_free_numbers': '❌ No free numbers',
        'available_count': 'Available: {count}',
        'showing_first_20': 'ℹ️ Showing first 20',
        'total_free': 'Total free: {count} numbers',
        
        # Changenumber command
        'player_not_registered': '❌ Player not registered',
        'number_out_of_range': '❌ Number must be from {min} to {max}',
        'number_changed': '🔢 NUMBER CHANGED',
        'new_number_set': 'Player {user} got new number',
        'new_number': '🎫 New number',
        
        # Backup command
        'creating_backup': '🔄 Creating backup...',
        'manual_backup_created': '💾 MANUAL BACKUP CREATED',
        'backup_sent_to_channel': 'Backup data successfully sent to channel',
        'backup_error': '❌ BACKUP ERROR',
        'backup_failed': 'Failed to create backup. Check channel settings.',
        
        # Set backup channel command
        'backup_channel_set': '✅ BACKUP CHANNEL SET',
        'backup_channel_desc': 'This channel will be used for automatic backups',
        'auto_backups': '💾 Automatic backups: Backups will be sent on:\n• Player registrations\n• Title purchases\n• Title changes\n• Game completion\n• Any other data changes',
        
        # Restore command
        'checking_file': '🔄 Checking file...',
        'wrong_format': '❌ FORMAT ERROR: Please upload JSON file',
        'file_read_error': '❌ READ ERROR: Failed to read file. Make sure it\'s valid JSON.',
        'invalid_format': '❌ INVALID FORMAT: File missing required fields: {fields}',
        'restore_warning': '⚠️ WARNING',
        'restore_warning_desc': 'You are about to restore data from backup.\n\n**ALL CURRENT DATA WILL BE OVERWRITTEN!**\n\nThis action cannot be undone.\nPlease confirm restoration.',
        'restore_data_info': '📊 Data for restoration',
        'restore_players_count': '• Players: {players}\n• Numbers: {numbers}\n• Titles: {titles}\n• Version: {version}',
        'restore_action': '🔄 Action: Click button below to confirm restoration',
        'restore_confirm': '✅ Confirm restoration',
        'restore_cancel': '❌ Cancel',
        'restore_cancelled': '❌ RESTORATION CANCELLED: Action cancelled by user',
        'restoring_data': '🔄 RESTORING DATA: Restoration in progress...',
        'data_restored': '✅ DATA RESTORED: All data successfully restored from backup!',
        'restored_data_info': '📊 Restored data',
        'restored_details': '• Players: {players}\n• Numbers: {numbers}\n• Titles: {titles}\n• Registration: {reg_status}\n• Game: {game_status}',
        'next_steps': '💡 Next steps',
        'restore_next_steps': '• Check data correctness\n• Make sure leaderboard displays correctly\n• Use `/update_leaderboard` if needed',
        'restore_error': '❌ RESTORATION ERROR: Failed to restore data from file',
        'restore_exception': '❌ RESTORATION ERROR: Error occurred during restoration: {error}',
        
        # Broadcast command
        'no_players_for_broadcast': '❌ No players for broadcast',
        'starting_broadcast': '📤 Starting broadcast for {count} players...',
        'announcement': '📢 ANNOUNCEMENT',
        'from_admin': 'From administrator • {admin}',
        'broadcast_results': '📊 BROADCAST RESULTS',
        'successfully_sent': '✅ Successfully sent',
        'sent_to_players': 'to {count} players',
        'broadcast_errors': '❌ Errors',
        
        # Players list command
        'participants': '👥 PARTICIPANTS',
        'registered_count': 'Registered: {current}/{max} players',
        'first_players': '🎮 Players (first {count})',
        
        # Mynumber command
        'not_registered': '❌ Not registered: You are not registered in the game',
        'your_number': '🎫 YOUR NUMBER: **Your game number:** `{number}`',
        'number_usage': '💡 Information: This number will be your identifier during the event',
        
        # List command
        'players_list': '📝 PLAYERS LIST',
        'no_registered_players': 'No registered players at the moment',
        'registered_players': '📋 REGISTERED PLAYERS',
        'players_chunk': '🎯 Players {start}-{end}',
        'total_stats': '📊 Total statistics',
        'total_players_info': 'Total players: {current}/{max}',
        
        # Save command
        'data_saved': '💾 DATA SAVED: All game data successfully saved',
        'saved_by': '👤 Saved by',
        'save_error': '❌ SAVE ERROR: Failed to save data',
        
        # Load command
        'data_loaded': '📂 DATA LOADED: Game data successfully loaded',
        'load_error': '❌ LOAD ERROR: Failed to load data',
        
        # Sync command
        'sync_success': '✅ SYNC SUCCESSFUL: Loaded {count} commands',
        'sync_error': '❌ SYNC ERROR: Error: {error}',
        
        # Reset command
        'player_not_in_system': '❌ Error: {user} not registered in system',
        'registration_reset': '🔄 REGISTRATION RESET: Player {user} registration successfully cancelled',
        
        # Automatic backups
        'auto_backup': '💾 AUTOMATIC BACKUP',
        'auto_backup_desc': 'Created automatic game data backup for server **{server}**',
        'server_stats': '📊 Server statistics',
        'server_stats_info': '• Players: {players}\n• Numbers: {numbers}\n• Titles: {titles}\n• Registration: {reg_status}\n• Game: {game_status}',
        'server_settings_info': '⚙️ Server settings',
        'server_settings_details': '• Max players: {max_players}\n• Reward: {reward:,}$\n• Numbers: {min:03d}-{max:03d}',
        'creation_time': '🕐 Creation time',
        'auto_backup_system': 'Automatic backup system • {server}',
        
        # Prizes
        'not_enough_players': 'Not enough players for prize distribution',
        'prizes_already_distributed': 'Prizes were already distributed earlier',
    }
}

def tr(language: str, key: str, **kwargs) -> str:
    """Get translated text for the specified language"""
    lang_dict = TRANSLATIONS.get(language, TRANSLATIONS['en'])
    text = lang_dict.get(key, key)
    
    # Replace placeholders if any
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
            
    return text

# Конфигурация по умолчанию для нового сервера
DEFAULT_CONFIG = {
    'max_players': 90,
    'min_number': 1,
    'max_number': 456,
    'registration_role_name': 'Registered',
    'used_numbers': set(),
    'registered_players': set(),
    'player_numbers': {},
    'registration_open': False,
    'game_active': False,
    'player_titles': {},
    'registration_order': [],
    'leaderboard_message_id': None,
    'leaderboard_channel_id': None,
    'prizes_distributed': False,
    'backup_channel_id': None,
    'reward_amount': 25000,
    'guild_name': 'Unknown Server',
    'language': 'en'  # По умолчанию английский
}

# Глобальная структура данных
GUILD_DATA = {}

# Доступные титулы
AVAILABLE_TITLES = {
    "EchoFan": 0x800080,
    "Legend": 0x00FFFF,
    "Rich": 0xFFD700,
    "mastermind": 0xFFFFFF,
    "Content Creator": 0xFF0000
}

# Цены титулов
TITLE_PRICES = {
    "EchoFan": 12500,
    "Legend": 25000,
    "Rich": 35000,
    "mastermind": 50000,
    "Content Creator": 0
}

# Призы за места
PRIZES = {
    1: 15000,
    2: 10000, 
    3: 5000
}

# Токены из переменных окружения
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
UNBELIEVABOAT_TOKEN = os.getenv('UNBELIEVABOAT_TOKEN')

def get_guild_config(guild_id: int, guild_name: str = "Unknown Server") -> dict:
    """Получает конфигурацию для сервера, создает новую если не существует"""
    if guild_id not in GUILD_DATA:
        # Создаем новую конфигурацию для сервера
        new_config = DEFAULT_CONFIG.copy()
        new_config['guild_name'] = guild_name
        # ВАЖНО: Не преобразуем множества в списки здесь - это делается только при сохранении
        GUILD_DATA[guild_id] = new_config
        logger.info(f"🆕 Created new configuration for server {guild_name} ({guild_id})")
    return GUILD_DATA[guild_id]

def convert_sets_to_lists(config: dict) -> dict:
    """Конвертирует множества в списки для JSON сериализации"""
    config_copy = config.copy()
    if isinstance(config_copy.get('used_numbers'), set):
        config_copy['used_numbers'] = list(config_copy['used_numbers'])
    if isinstance(config_copy.get('registered_players'), set):
        config_copy['registered_players'] = list(config_copy['registered_players'])
    return config_copy

def convert_lists_to_sets(config: dict) -> dict:
    """Конвертирует списки обратно в множества после загрузки из JSON"""
    config_copy = config.copy()
    if isinstance(config_copy.get('used_numbers'), list):
        config_copy['used_numbers'] = set(config_copy['used_numbers'])
    if isinstance(config_copy.get('registered_players'), list):
        config_copy['registered_players'] = set(config_copy['registered_players'])
    return config_copy

async def send_backup_to_channel(guild_id: int):
    """Отправляет бэкап в указанный канал с указанием сервера"""
    try:
        config = get_guild_config(guild_id)
        lang = config.get('language', 'en')
        backup_channel_id = config.get('backup_channel_id')
        
        if not backup_channel_id:
            logger.warning(f"⚠️ BACKUP_CHANNEL_ID not set for server {config['guild_name']}, skipping backup")
            return False
        
        channel = bot.get_channel(int(backup_channel_id))
        if not channel:
            logger.error(f"❌ Backup channel not found for server {config['guild_name']}")
            return False
        
        # Создаем временный файл для отправки
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"game_backup_{timestamp}.json"
        
        # Создаем бэкап только для этого сервера
        backup_data = {
            'guild_id': guild_id,
            'guild_name': config['guild_name'],
            'backup_timestamp': str(datetime.datetime.now()),
            'config': convert_sets_to_lists(config)
        }
        
        # Сохраняем временный файл
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        # Создаем embed с информацией о бэкапе
        embed = discord.Embed(
            title=tr(lang, 'auto_backup'),
            description=tr(lang, 'auto_backup_desc', server=config['guild_name']),
            color=0x00ff00,
            timestamp=datetime.datetime.now()
        )
        
        reg_status = tr(lang, 'status_open') if config['registration_open'] else tr(lang, 'status_closed')
        game_status = tr(lang, 'game_status_active') if config['game_active'] else tr(lang, 'game_status_completed')
        
        embed.add_field(
            name=tr(lang, 'server_stats'),
            value=tr(lang, 'server_stats_info', 
                    players=len(config['registered_players']),
                    numbers=len(config['used_numbers']),
                    titles=len(config['player_titles']),
                    reg_status=reg_status,
                    game_status=game_status),
            inline=True
        )
        
        embed.add_field(
            name=tr(lang, 'server_settings_info'),
            value=tr(lang, 'server_settings_details',
                    max_players=config['max_players'],
                    reward=config['reward_amount'],
                    min=config['min_number'],
                    max=config['max_number']),
            inline=True
        )
        
        embed.add_field(
            name=tr(lang, 'creation_time'),
            value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            inline=False
        )
        
        embed.set_footer(text=tr(lang, 'auto_backup_system', server=config['guild_name']))
        
        # Отправляем файл
        file = discord.File(backup_filename, filename=backup_filename)
        await channel.send(embed=embed, file=file)
        
        # Удаляем временный файл
        os.remove(backup_filename)
        
        logger.info(f"✅ Backup sent to channel for server {config['guild_name']}")
        return True
            
    except Exception as e:
        logger.error(f"❌ Error sending backup for server {guild_id}: {e}")
        return False

async def save_data_with_backup(guild_id: int):
    """Сохраняет данные и создает резервную копию с отправкой в канал"""
    # Сохраняем данные всех серверов
    if await save_data():
        # Отправляем бэкап только для конкретного сервера
        await send_backup_to_channel(guild_id)
        return True
    return False

async def save_data():
    """Сохраняет данные всех серверов в файл"""
    try:
        save_data = {
            'guilds': {},
            'saved_at': str(datetime.datetime.now()),
            'version': '2.0'
        }
        
        # Конвертируем данные каждого сервера
        for guild_id, config in GUILD_DATA.items():
            save_data['guilds'][str(guild_id)] = convert_sets_to_lists(config)
        
        temp_filename = 'game_data_temp.json'
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        if os.path.exists('game_data.json'):
            os.replace(temp_filename, 'game_data.json')
        else:
            os.rename(temp_filename, 'game_data.json')
            
        logger.info("✅ All server data saved")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving data: {e}")
        try:
            if os.path.exists('game_data_temp.json'):
                os.remove('game_data_temp.json')
        except:
            pass
        return False

async def restore_from_backup(backup_data, guild_id: int):
    """Восстанавливает данные из бэкапа для конкретного сервера"""
    try:
        # Сохраняем текущие данные как резервную копию перед восстановлением
        await save_data_with_backup(guild_id)
        
        config = get_guild_config(guild_id)
        
        # Очищаем текущие данные
        config['used_numbers'].clear()
        config['registered_players'].clear()
        config['player_numbers'].clear()
        config['player_titles'].clear()
        config['registration_order'].clear()
        
        # Восстанавливаем used_numbers
        if 'used_numbers' in backup_data:
            config['used_numbers'] = set(backup_data['used_numbers'])
        
        # Восстанавливаем registered_players
        if 'registered_players' in backup_data:
            config['registered_players'] = set(backup_data['registered_players'])
        
        # Восстанавливаем player_numbers
        if 'player_numbers' in backup_data:
            config['player_numbers'] = {}
            for user_id_str, number_str in backup_data['player_numbers'].items():
                try:
                    user_id = int(user_id_str)
                    config['player_numbers'][user_id] = number_str
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Invalid user_id in backup: {user_id_str}")
                    continue
        
        # Восстанавливаем player_titles
        if 'player_titles' in backup_data:
            config['player_titles'] = {}
            for user_id_str, title_data in backup_data['player_titles'].items():
                try:
                    user_id = int(user_id_str)
                    if isinstance(title_data, str):
                        config['player_titles'][user_id] = {
                            'owned': [title_data],
                            'equipped': title_data
                        }
                    else:
                        config['player_titles'][user_id] = title_data
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Invalid user_id in title backup: {user_id_str}")
                    continue
        
        # Восстанавливаем registration_order
        if 'registration_order' in backup_data:
            config['registration_order'] = backup_data['registration_order']
        else:
            config['registration_order'] = list(config['registered_players'])
        
        # Восстанавливаем лидерборд
        if 'leaderboard_message_id' in backup_data:
            config['leaderboard_message_id'] = backup_data['leaderboard_message_id']
        if 'leaderboard_channel_id' in backup_data:
            config['leaderboard_channel_id'] = backup_data['leaderboard_channel_id']
        
        # Восстанавливаем флаги
        if 'registration_open' in backup_data:
            config['registration_open'] = backup_data['registration_open']
        if 'game_active' in backup_data:
            config['game_active'] = backup_data['game_active']
        if 'prizes_distributed' in backup_data:
            config['prizes_distributed'] = backup_data['prizes_distributed']
        else:
            config['prizes_distributed'] = False
        
        # Восстанавливаем настройки
        if 'max_players' in backup_data:
            config['max_players'] = backup_data['max_players']
        if 'reward_amount' in backup_data:
            config['reward_amount'] = backup_data['reward_amount']
        
        # Сохраняем восстановленные данные
        await save_data()
        
        logger.info(f"✅ Data restored from backup for server {config['guild_name']}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error restoring from backup for server {guild_id}: {e}")
        return False

async def restore_players_from_roles(guild, config: dict):
    """Восстанавливает игроков из ролей для конкретного сервера"""
    try:
        logger.info(f"🔄 Checking players with role '{config['registration_role_name']}' on server {guild.name}...")
        
        role = discord.utils.get(guild.roles, name=config['registration_role_name'])
        if not role:
            logger.info(f"⚠️ Role '{config['registration_role_name']}' not found on server {guild.name}")
            return
        
        restored_count = 0
        for member in role.members:
            if member.id not in config['registered_players']:
                # Игрок есть в роли, но нет в данных - восстанавливаем
                logger.info(f"🔄 Restoring player {member.display_name} ({member.id}) on server {guild.name}")
                
                # Извлекаем номер из ника
                number_match = re.search(r'\((\d{3})\)$', member.display_name)
                if number_match:
                    player_number = int(number_match.group(1))
                    formatted_number = f"{player_number:03d}"
                    
                    # Проверяем, не занят ли номер
                    if player_number in config['used_numbers']:
                        # Генерируем новый номер
                        while True:
                            player_number = random.randint(config['min_number'], config['max_number'])
                            if player_number not in config['used_numbers']:
                                break
                        formatted_number = f"{player_number:03d}"
                    
                    config['used_numbers'].add(player_number)
                    config['registered_players'].add(member.id)
                    config['player_numbers'][member.id] = formatted_number
                    
                    if member.id not in config['registration_order']:
                        config['registration_order'].append(member.id)
                    
                    restored_count += 1
                    logger.info(f"✅ Restored player {member.display_name} with number {formatted_number} on server {guild.name}")
        
        if restored_count > 0:
            logger.info(f"✅ Restored {restored_count} players from roles on server {guild.name}")
            await save_data()
        else:
            logger.info(f"ℹ️ No new players found for restoration on server {guild.name}")
            
    except Exception as e:
        logger.error(f"❌ Error restoring players from roles on server {guild.name}: {e}")

def load_data():
    """Загружает данные всех серверов из файла"""
    try:
        if not os.path.exists('game_data.json'):
            logger.info("ℹ️ Data file not found, starting fresh")
            return True
            
        with open('game_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        GUILD_DATA.clear()
        
        if 'guilds' in data:
            for guild_id_str, config in data['guilds'].items():
                try:
                    guild_id = int(guild_id_str)
                    # Конвертируем списки в множества
                    converted_config = convert_lists_to_sets(config)
                    GUILD_DATA[guild_id] = converted_config
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Invalid guild_id in data: {guild_id_str}")
                    continue
        
        logger.info("✅ Data loaded")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error loading data: {e}")
        GUILD_DATA.clear()
        return False

def remove_number_from_nick(nickname: Optional[str]) -> str:
    """Удаляет номер из ника в формате (123)"""
    if nickname:
        return re.sub(r'\s*\(\d{3}\)\s*$', '', nickname).strip()
    return ""

def add_number_to_nick(nickname: Optional[str], number: str) -> str:
    """Добавляет номер к нику в формате (123)"""
    clean_nick = remove_number_from_nick(nickname)
    new_nick = f"{clean_nick} ({number})"
    return new_nick[:32]

async def add_money_to_user(guild_id: int, user_id: int, amount: int):
    """Добавляет деньги пользователю через UnbelievaBoat"""
    url = f"https://unbelievaboat.com/api/v1/guilds/{guild_id}/users/{user_id}"
    headers = {
        "Authorization": UNBELIEVABOAT_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "cash": amount
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=data) as response:
                if response.status == 200:
                    return True, "Success"
                else:
                    error_text = await response.text()
                    return False, f"Error {response.status}: {error_text}"
    except Exception as e:
        return False, f"Connection error: {e}"

async def get_user_balance(guild_id: int, user_id: int):
    """Получает баланс пользователя через UnbelievaBoat"""
    url = f"https://unbelievaboat.com/api/v1/guilds/{guild_id}/users/{user_id}"
    headers = {
        "Authorization": UNBELIEVABOAT_TOKEN
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return True, data
                else:
                    error_text = await response.text()
                    return False, f"Error {response.status}: {error_text}"
    except Exception as e:
        return False, f"Connection error: {e}"

async def update_leaderboard(guild_id: int):
    """Обновляет сообщение лидерборда для конкретного сервера"""
    config = get_guild_config(guild_id)
    lang = config.get('language', 'en')
    if not config['leaderboard_message_id'] or not config['leaderboard_channel_id']:
        logger.info(f"ℹ️ Leaderboard not set for server {config['guild_name']}, skipping update")
        return
    
    try:
        channel = bot.get_channel(config['leaderboard_channel_id'])
        if not channel:
            logger.warning(f"❌ Leaderboard channel not found for server {config['guild_name']}")
            return
        
        message = await channel.fetch_message(config['leaderboard_message_id'])
        
        embed = await create_leaderboard_embed(guild_id)
        await message.edit(embed=embed)
        logger.info(f"✅ Leaderboard updated for server {config['guild_name']}")
        
    except discord.NotFound:
        logger.warning(f"❌ Leaderboard message not found for server {config['guild_name']}, resetting settings")
        config['leaderboard_message_id'] = None
        config['leaderboard_channel_id'] = None
        await save_data_with_backup(guild_id)
    except Exception as e:
        logger.error(f"❌ Error updating leaderboard for server {config['guild_name']}: {e}")

async def create_leaderboard_embed(guild_id: int, page: int = 1):
    """Создает embed для лидерборда конкретного сервера"""
    config = get_guild_config(guild_id)
    lang = config.get('language', 'en')
    
    if not config['registration_order']:
        return discord.Embed(
            title=tr(lang, 'leaderboard'),
            description=tr(lang, 'no_players'),
            color=0xff0000
        )
    
    total_pages = (len(config['registration_order']) + 9) // 10
    if page < 1 or page > total_pages:
        page = 1
    
    embed = discord.Embed(
        title=tr(lang, 'leaderboard'),
        description=tr(lang, 'players_by_registration', server=config['guild_name']),
        color=0xff0000
    )
    
    start_index = (page - 1) * 10
    end_index = min(start_index + 10, len(config['registration_order']))
    
    leaderboard_text = ""
    
    for i in range(start_index, end_index):
        user_id = config['registration_order'][i]
        user = bot.get_user(user_id)
        player_number = config['player_numbers'].get(user_id, "???")
        
        # Добавляем медальки для первых трех мест
        medal = ""
        if i == 0:  # 1 место
            medal = "🥇"
        elif i == 1:  # 2 место
            medal = "🥈"
        elif i == 2:  # 3 место
            medal = "🥉"
        
        if user:
            equipped_title = None
            if user_id in config['player_titles']:
                equipped_title = config['player_titles'][user_id].get('equipped')
            
            if equipped_title:
                leaderboard_text += f"`#{i+1:2d}` {medal} {user.display_name} **[{equipped_title}]** ({player_number})\n"
            else:
                leaderboard_text += f"`#{i+1:2d}` {medal} {user.display_name} ({player_number})\n"
        else:
            leaderboard_text += f"`#{i+1:2d}` {medal} Unknown User ({player_number})\n"
    
    embed.add_field(
        name=tr(lang, 'players_range', start=start_index + 1, end=end_index),
        value=leaderboard_text or tr(lang, 'no_data'),
        inline=False
    )
    
    # Добавляем информацию о призах для топ-3
    if config['registration_order'] and len(config['registration_order']) >= 3:
        embed.add_field(
            name=tr(lang, 'top3_prizes'),
            value=tr(lang, 'prizes_info', first=PRIZES[1], second=PRIZES[2], third=PRIZES[3]),
            inline=False
        )
    
    embed.set_footer(text=tr(lang, 'page_info', current=page, total=total_pages, server=config['guild_name']))
    embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
    
    return embed

async def safe_send_response(interaction, *args, **kwargs):
    """Безопасная отправка ответа с обработкой ошибок взаимодействий"""
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(*args, **kwargs)
        else:
            await interaction.followup.send(*args, **kwargs)
        return True
    except discord.errors.NotFound:
        logger.warning("⚠️ Interaction not found (possibly timed out)")
        return False
    except discord.errors.HTTPException as e:
        logger.error(f"❌ HTTP error when sending response: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unknown error when sending response: {e}")
        return False

async def safe_edit_response(interaction, *args, **kwargs):
    """Безопасное редактирование ответа"""
    try:
        await interaction.edit_original_response(*args, **kwargs)
        return True
    except Exception as e:
        logger.error(f"❌ Error editing response: {e}")
        return False

async def safe_defer_response(interaction, ephemeral=False):
    """Безопасное откладывание ответа"""
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=ephemeral)
            return True
        return False
    except discord.errors.NotFound:
        logger.warning(f"⚠️ Interaction not found (timed out), skipping deferred response")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Failed to defer response (possibly already processed): {e}")
        return False

async def auto_update_leaderboard(guild_id: int):
    """Автоматически обновляет лидерборд с обработкой ошибок"""
    try:
        await update_leaderboard(guild_id)
        logger.info(f"✅ Leaderboard automatically updated for server {GUILD_DATA[guild_id]['guild_name']}")
    except Exception as e:
        logger.error(f"❌ Error auto-updating leaderboard for server {guild_id}: {e}")

async def distribute_prizes(guild_id: int, config: dict):
    """Распределяет призы за первые три места"""
    lang = config.get('language', 'en')
    
    if not config['registration_order'] or len(config['registration_order']) < 3:
        return [], tr(lang, 'not_enough_players')
    
    if config['prizes_distributed']:
        return [], tr(lang, 'prizes_already_distributed')
    
    prize_results = []
    errors = []
    
    # Распределяем призы для топ-3
    for place in range(1, 4):
        if len(config['registration_order']) >= place:
            user_id = config['registration_order'][place - 1]
            prize_amount = PRIZES[place]
            
            success, message = await add_money_to_user(guild_id, user_id, prize_amount)
            
            user = bot.get_user(user_id)
            username = user.display_name if user else f"ID {user_id}"
            
            if success:
                prize_results.append(f"🥇 {place} place: {username} - {prize_amount:,}$")
                logger.info(f"🏆 Prize given: {username} - {prize_amount}$")
            else:
                errors.append(f"{place} place ({username}): {message}")
                logger.error(f"❌ Error giving prize {place} place: {message}")
    
    config['prizes_distributed'] = True
    await save_data_with_backup(guild_id)
    
    return prize_results, errors

# ==================== КОМАНДА LANGUAGE ====================

@bot.tree.command(name="language", description="Set the language for this server")
@app_commands.choices(language=[
    app_commands.Choice(name="English", value="en"),
    app_commands.Choice(name="Русский", value="ru")
])
@app_commands.default_permissions(administrator=True)
async def set_language(interaction: discord.Interaction, language: str):
    """Sets the language for the server"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content=tr('en', 'command_server_only'))
            return
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        old_language = config.get('language', 'en')
        config['language'] = language
        
        await save_data_with_backup(interaction.guild.id)
        
        embed = discord.Embed(
            title="🌐 LANGUAGE CHANGED",
            description=tr(language, 'language_set'),
            color=0x00ff00
        )
        
        embed.add_field(
            name=tr(language, 'was'),
            value=f"```{old_language.upper()}```",
            inline=True
        )
        
        embed.add_field(
            name=tr(language, 'now'), 
            value=f"```{language.upper()}```",
            inline=True
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in language command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

@bot.tree.command(name="start", description="Open registration for all players (admins only)")
@app_commands.default_permissions(administrator=True)
async def start(interaction: discord.Interaction):
    """Opening registration"""
    try:
        await safe_defer_response(interaction, ephemeral=False)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content=tr('en', 'command_server_only'))
            return
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
            
        if config['registration_open']:
            embed = discord.Embed(
                title=tr(lang, 'registration_already_closed'),
                description=tr(lang, 'game_already_completed'),
                color=0xff0000
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            return
        
        config['registration_open'] = True
        config['game_active'] = True
        config['prizes_distributed'] = False
        
        await save_data_with_backup(interaction.guild.id)
        
        embed = discord.Embed(
            title=tr(lang, 'registration_opened'),
            description=tr(lang, 'players_can_join'),
            color=0xff0000
        )
        embed.add_field(
            name=tr(lang, 'statistics'),
            value=tr(lang, 'available_spots_info', 
                    available=config['max_players'] - len(config['registered_players']),
                    max=config['max_players']) + "\n" +
                  tr(lang, 'number_range', min=config['min_number'], max=config['max_number']),
            inline=False
        )
        embed.add_field(
            name=tr(lang, 'registration_status_label'),
            value="```/register```",
            inline=True
        )
        embed.add_field(
            name=tr(lang, 'check_status'),
            value="```/status```",
            inline=True
        )
        embed.set_footer(text=f"{tr(lang, 'registration_system')} • {interaction.guild.name}")
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in start command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

@bot.tree.command(name="register", description="Register for the game")
async def register(interaction: discord.Interaction):
    """Command to register a player"""
    try:
        # Пытаемся отложить ответ
        deferred = await safe_defer_response(interaction, ephemeral=True)
        if not deferred:
            # Если не удалось отложить, пробуем отправить сразу
            await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)
            return
        
        if not interaction.guild:
            await safe_edit_response(interaction, content=tr('en', 'command_server_only'))
            return
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        
        # ВАЖНО: Проверяем и исправляем типы данных
        if not isinstance(config['used_numbers'], set):
            config['used_numbers'] = set(config.get('used_numbers', []))
        if not isinstance(config['registered_players'], set):
            config['registered_players'] = set(config.get('registered_players', []))
            
        if not config['registration_open']:
            embed = discord.Embed(
                title=tr(lang, 'registration_closed'),
                description=tr(lang, 'wait_for_registration'),
                color=0xff0000
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            return
        
        if len(config['registered_players']) >= config['max_players']:
            embed = discord.Embed(
                title=tr(lang, 'all_spots_taken'),
                description=tr(lang, 'registration_completed', max_players=config['max_players']),
                color=0xff0000
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            return
        
        if interaction.user.id in config['registered_players']:
            embed = discord.Embed(
                title=tr(lang, 'already_registered'),
                description=tr(lang, 'you_are_already_participating'),
                color=0xff0000
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            return
        
        if len(config['used_numbers']) >= (config['max_number'] - config['min_number'] + 1):
            embed = discord.Embed(
                title=tr(lang, 'all_numbers_taken'),
                description=tr(lang, 'all_numbers_taken_description'),
                color=0xff0000
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            return
        
        # Генерируем уникальный номер
        while True:
            player_number = random.randint(config['min_number'], config['max_number'])
            if player_number not in config['used_numbers']:
                config['used_numbers'].add(player_number)
                break
        
        formatted_number = f"{player_number:03d}"
        
        # Регистрируем игрока
        config['registered_players'].add(interaction.user.id)
        config['player_numbers'][interaction.user.id] = formatted_number
        
        # Добавляем в порядок регистрации если еще нет
        if interaction.user.id not in config['registration_order']:
            config['registration_order'].append(interaction.user.id)
        
        await save_data_with_backup(interaction.guild.id)
        
        # АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ЛИДЕРБОРДА ПРИ РЕГИСТРАЦИИ
        asyncio.create_task(auto_update_leaderboard(interaction.guild.id))
        
        # Выдаем роль
        registration_role = discord.utils.get(interaction.guild.roles, name=config['registration_role_name'])
        
        if not registration_role:
            try:
                registration_role = await interaction.guild.create_role(
                    name=config['registration_role_name'],
                    color=0xff0000,
                    reason=tr(lang, 'role_creation_reason')
                )
            except discord.Forbidden:
                embed = discord.Embed(
                    title=tr(lang, 'role_creation_error'),
                    description=tr(lang, 'role_creation_error_desc'),
                    color=0xff0000
                )
                await safe_edit_response(interaction, embed=embed)
                return
        
        member = cast(discord.Member, interaction.user)
        try:
            await member.add_roles(registration_role)
        except discord.Forbidden:
            embed = discord.Embed(
                title=tr(lang, 'role_assignment_error'),
                description=tr(lang, 'role_assignment_error_desc'),
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        # Обновляем ник
        try:
            new_nickname = add_number_to_nick(member.display_name, formatted_number)
            await member.edit(nick=new_nickname)
        except discord.Forbidden:
            pass  # Нет прав на изменение ника - это не критично
        
        embed = discord.Embed(
            title=tr(lang, 'registration_success'),
            description=tr(lang, 'welcome_to_game', number=formatted_number),
            color=0xff0000
        )
        embed.add_field(
            name=tr(lang, 'your_game_number'),
            value=f"```{formatted_number}```",
            inline=False
        )
        embed.add_field(
            name=tr(lang, 'your_spot'),
            value=f"```{len(config['registered_players'])}/{config['max_players']}```",
            inline=True
        )
        embed.add_field(
            name=tr(lang, 'status'),
            value=tr(lang, 'status_registered'),
            inline=True
        )
        embed.add_field(
            name=tr(lang, 'important_info'),
            value=tr(lang, 'number_identifier'),
            inline=False
        )
        embed.set_footer(text=f"{tr(lang, 'registration_system')} • {interaction.guild.name}")
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in register command: {e}")
        try:
            await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)
        except Exception as e2:
            logger.error(f"❌ Failed to send error message: {e2}")

@bot.tree.command(name="status", description="Check registration status")
async def status(interaction: discord.Interaction):
    """Command to check registration status"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content=tr('en', 'command_server_only'))
            return
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        available_spots = config['max_players'] - len(config['registered_players'])
        
        embed = discord.Embed(
            title=tr(lang, 'registration_status'),
            color=0xff0000
        )
        
        # Статус регистрации
        if config['registration_open']:
            reg_status = tr(lang, 'status_open')
            reg_description = tr(lang, 'registration_active')
        else:
            reg_status = tr(lang, 'status_closed')
            reg_description = tr(lang, 'registration_inactive')
        
        # Статус игры
        if config['game_active']:
            game_status = tr(lang, 'game_status_active')
            game_description = tr(lang, 'event_in_progress')
        else:
            game_status = tr(lang, 'game_status_completed')
            game_description = tr(lang, 'event_completed')
        
        embed.add_field(
            name=tr(lang, 'registration_status_label'),
            value=f"```{reg_status}```\n{reg_description}",
            inline=True
        )
        embed.add_field(
            name=tr(lang, 'game_status_label'),
            value=f"```{game_status}```\n{game_description}",
            inline=True
        )
        
        embed.add_field(
            name=tr(lang, 'registered_players'),
            value=f"```{len(config['registered_players'])}/{config['max_players']} {tr(lang, 'players')}```",
            inline=True
        )
        embed.add_field(
            name=tr(lang, 'available_spots'),
            value=f"```{available_spots} {tr(lang, 'spots')}```",
            inline=True
        )
        embed.add_field(
            name=tr(lang, 'used_numbers'),
            value=f"```{len(config['used_numbers'])} {tr(lang, 'out_of')} {config['max_number'] - config['min_number'] + 1}```",
            inline=True
        )
        
        if config['registration_open'] and available_spots > 0:
            embed.add_field(
                name=tr(lang, 'join_now'),
                value=tr(lang, 'use_register_command'),
                inline=False
            )
        
        embed.set_footer(text=f"{tr(lang, 'registration_system')} • {interaction.guild.name}")
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in status command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

@bot.tree.command(name="end", description="Close registration or finish game (admins only)")
@app_commands.default_permissions(administrator=True)
async def end(interaction: discord.Interaction):
    """Closing registration or finishing game"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content=tr('en', 'command_server_only'))
            return
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        
        if not config['game_active']:
            embed = discord.Embed(
                title=tr(lang, 'registration_already_closed'),
                description=tr(lang, 'game_already_completed'),
                color=0xff0000
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            return
        
        if config['registration_open']:
            # Первое использование - закрываем регистрацию
            config['registration_open'] = False
            
            # Сохраняем изменения
            await save_data_with_backup(interaction.guild.id)
            
            embed = discord.Embed(
                title=tr(lang, 'registration_closed_title'),
                description=tr(lang, 'registration_closed_desc'),
                color=0xff0000
            )
            embed.add_field(
                name=tr(lang, 'statistics'),
                value=tr(lang, 'registered_count', players=len(config['registered_players']), max=config['max_players']),
                inline=False
            )
            embed.add_field(
                name=tr(lang, 'next_step'),
                value=tr(lang, 'use_end_again'),
                inline=False
            )
            embed.set_footer(text=f"{tr(lang, 'registration_system')} • {interaction.guild.name}")
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            
        else:
            # Второе использование - завершаем игру полностью
            config['game_active'] = False
            
            if not config['registered_players']:
                embed = discord.Embed(
                    title=tr(lang, 'game_completed'),
                    description=tr(lang, 'no_players_for_broadcast'),
                    color=0xff0000
                )
                embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
                await safe_edit_response(interaction, embed=embed)
                return
            
            registration_role = discord.utils.get(interaction.guild.roles, name=config['registration_role_name'])
            reset_count = 0
            money_sent_count = 0
            money_errors = []
            role_errors = []
            nick_errors = []
            
            # Начисляем деньги и сбрасываем игроков
            processing_embed = discord.Embed(
                title=tr(lang, 'game_completing'),
                description=tr(lang, 'game_completing_desc'),
                color=0xff0000
            )
            processing_embed.add_field(
                name=tr(lang, 'progress'),
                value=f"```{tr(lang, 'processing_players')}```",
                inline=False
            )
            await safe_edit_response(interaction, embed=processing_embed)
            
            # Распределяем призы для топ-3 игроков (если еще не распределены)
            prize_results = []
            prize_errors = []
            if not config['prizes_distributed'] and len(config['registration_order']) >= 3:
                prize_results, prize_errors = await distribute_prizes(interaction.guild.id, config)
            
            # Обрабатываем каждого игрока
            for user_id in list(config['registered_players']):
                try:
                    member = await interaction.guild.fetch_member(user_id)
                    
                    # Начисляем базовые деньги через UnbelievaBoat (используем награду сервера)
                    success, message = await add_money_to_user(interaction.guild.id, user_id, config['reward_amount'])
                    if success:
                        money_sent_count += 1
                    else:
                        money_errors.append(f"{member.display_name}: {message}")
                    
                    # Пытаемся убрать роль
                    try:
                        if registration_role and registration_role in member.roles:
                            await member.remove_roles(registration_role)
                    except discord.Forbidden:
                        role_errors.append(f"{member.display_name}")
                    
                    # Пытаемся вернуть ник
                    try:
                        original_nickname = remove_number_from_nick(member.display_name)
                        if not original_nickname or original_nickname.isspace():
                            original_nickname = member.name
                        await member.edit(nick=original_nickname)
                    except discord.Forbidden:
                        nick_errors.append(f"{member.display_name}")
                    
                    reset_count += 1
                    
                    # Небольшая задержка чтобы не перегружать API
                    await asyncio.sleep(0.5)
                    
                except (discord.NotFound, discord.Forbidden) as e:
                    money_errors.append(f"ID {user_id}: {str(e)}")
                    continue
            
            # Очищаем все данные (кроме титулов)
            total_players = len(config['registered_players'])
            config['used_numbers'].clear()
            config['registered_players'].clear()
            config['player_numbers'].clear()
            config['registration_order'].clear()
            # ТИТУЛЫ НЕ УДАЛЯЕМ - они сохраняются навсегда
            
            # Сохраняем изменения
            await save_data_with_backup(interaction.guild.id)
            
            # Финальное сообщение
            result_embed = discord.Embed(
                title=tr(lang, 'game_completed'),
                description=tr(lang, 'game_completed_desc'),
                color=0xff0000
            )
            result_embed.add_field(
                name=tr(lang, 'completion_results'),
                value=tr(lang, 'successfully_reset', reset=reset_count, total=total_players) + "\n" +
                      tr(lang, 'money_sent', sent=money_sent_count, total=total_players),
                inline=False
            )
            result_embed.add_field(
                name=tr(lang, 'rewards'),
                value=tr(lang, 'each_received', amount=config['reward_amount']),
                inline=False
            )
            
            # Добавляем информацию о призах если они были распределены
            if prize_results:
                result_embed.add_field(
                    name=tr(lang, 'prizes_top3'),
                    value="\n".join(prize_results),
                    inline=False
                )
            
            result_embed.add_field(
                name=tr(lang, 'completed_actions'),
                value=tr(lang, 'actions_list'),
                inline=False
            )
            
            # Показываем ошибки если есть
            if role_errors:
                result_embed.add_field(
                    name=tr(lang, 'role_remove_errors'),
                    value=tr(lang, 'role_remove_failed', count=len(role_errors)),
                    inline=False
                )
            
            if nick_errors:
                result_embed.add_field(
                    name=tr(lang, 'nick_restore_errors'),
                    value=tr(lang, 'nick_restore_failed', count=len(nick_errors)),
                    inline=False
                )
            
            if money_errors:
                error_text = "\n".join(money_errors[:3])
                if len(money_errors) > 3:
                    error_text += f"\n... {tr(lang, 'and_more_errors', count=len(money_errors) - 3)}"
                result_embed.add_field(
                    name=tr(lang, 'money_errors'),
                    value=f"```{error_text}```",
                    inline=False
                )
            
            if prize_errors:
                error_text = "\n".join(prize_errors[:3])
                if len(prize_errors) > 3:
                    error_text += f"\n... {tr(lang, 'and_more_errors', count=len(prize_errors) - 3)}"
                result_embed.add_field(
                    name=tr(lang, 'prize_errors'),
                    value=f"```{error_text}```",
                    inline=False
                )
            
            result_embed.set_footer(text=f"{tr(lang, 'registration_system')} • {interaction.guild.name}")
            result_embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            
            await safe_edit_response(interaction, embed=result_embed)
            
    except Exception as e:
        logger.error(f"❌ Error in end command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

# ==================== НОВЫЕ КОМАНДЫ ====================

@bot.tree.command(name="players", description="Set maximum number of players for this server (admins)")
@app_commands.default_permissions(administrator=True)
async def set_max_players(interaction: discord.Interaction, max_players: int):
    """Sets maximum number of players for the server"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content=tr('en', 'command_server_only'))
            return
        
        if max_players < 1 or max_players > 500:
            await safe_edit_response(interaction, content="❌ Max players must be between 1 and 500")
            return
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        old_max = config['max_players']
        config['max_players'] = max_players
        
        await save_data_with_backup(interaction.guild.id)
        
        embed = discord.Embed(
            title=tr(lang, 'max_players_changed'),
            description=tr(lang, 'new_max_players', server=interaction.guild.name),
            color=0x00ff00
        )
        
        embed.add_field(
            name=tr(lang, 'was'),
            value=f"```{old_max} {tr(lang, 'players')}```",
            inline=True
        )
        
        embed.add_field(
            name=tr(lang, 'now'),
            value=f"```{max_players} {tr(lang, 'players')}```",
            inline=True
        )
        
        embed.add_field(
            name=tr(lang, 'current_stats'),
            value=tr(lang, 'registered_info', current=len(config['registered_players']), max=max_players),
            inline=False
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in players command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

@bot.tree.command(name="reward", description="Set participation reward for this server (admins)")
@app_commands.default_permissions(administrator=True)
async def set_reward(interaction: discord.Interaction, reward: int):
    """Sets participation reward for the server"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content=tr('en', 'command_server_only'))
            return
        
        if reward < 0 or reward > 1000000:
            await safe_edit_response(interaction, content="❌ Reward must be between 0 and 1,000,000")
            return
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        old_reward = config['reward_amount']
        config['reward_amount'] = reward
        
        await save_data_with_backup(interaction.guild.id)
        
        embed = discord.Embed(
            title=tr(lang, 'reward_changed'),
            description=tr(lang, 'new_reward_set', server=interaction.guild.name),
            color=0x00ff00
        )
        
        embed.add_field(
            name=tr(lang, 'was'),
            value=f"```{old_reward:,}$```",
            inline=True
        )
        
        embed.add_field(
            name=tr(lang, 'now'),
            value=f"```{reward:,}$```",
            inline=True
        )
        
        embed.add_field(
            name=tr(lang, 'important_info'),
            value=tr(lang, 'reward_info'),
            inline=False
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in reward command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

@bot.tree.command(name="server_info", description="Show server settings information")
async def server_info(interaction: discord.Interaction):
    """Shows server settings information"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content=tr('en', 'command_server_only'))
            return
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        
        embed = discord.Embed(
            title=tr(lang, 'server_settings'),
            description=tr(lang, 'server_config', server=interaction.guild.name),
            color=0xff0000
        )
        
        reg_status = tr(lang, 'status_open') if config['registration_open'] else tr(lang, 'status_closed')
        game_status = tr(lang, 'game_status_active') if config['game_active'] else tr(lang, 'game_status_completed')
        prizes_status = tr(lang, 'yes') if config['prizes_distributed'] else tr(lang, 'no')
        
        embed.add_field(
            name=tr(lang, 'limits'),
            value=tr(lang, 'limits_info', 
                    max_players=config['max_players'],
                    min=config['min_number'],
                    max=config['max_number'],
                    reward=config['reward_amount']),
            inline=False
        )
        
        embed.add_field(
            name=tr(lang, 'status_info'),
            value=tr(lang, 'status_details',
                    reg_status=reg_status,
                    game_status=game_status,
                    prizes_status=prizes_status),
            inline=False
        )
        
        embed.add_field(
            name=tr(lang, 'statistics_info'),
            value=tr(lang, 'stats_details',
                    registered=len(config['registered_players']),
                    max_players=config['max_players'],
                    used_numbers=len(config['used_numbers']),
                    titles=len(config['player_titles'])),
            inline=False
        )
        
        if interaction.user.guild_permissions.administrator:
            embed.add_field(
                name=tr(lang, 'management'),
                value=tr(lang, 'management_commands'),
                inline=False
            )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in server_info command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

# ==================== КОМАНДЫ ТИТУЛОВ ====================

@bot.tree.command(name="titles", description="Titles shop")
async def titles(interaction: discord.Interaction):
    """Shows available titles for purchase"""
    try:
        await safe_defer_response(interaction, ephemeral=False)
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        user_titles = config['player_titles'].get(interaction.user.id, {'owned': [], 'equipped': None})
        owned_titles = user_titles['owned']
        
        embed = discord.Embed(
            title=tr(lang, 'titles_shop'),
            description=tr(lang, 'titles_desc'),
            color=0xff0000
        )
        
        for title, color in AVAILABLE_TITLES.items():
            price = TITLE_PRICES[title]
            price_text = tr(lang, 'free_reward') if price == 0 else tr(lang, 'price', price=price)
            
            status = tr(lang, 'purchased') if title in owned_titles else tr(lang, 'available')
            
            embed.add_field(
                name=f"**{title}** - {status}",
                value=f"{tr(lang, 'price_label')}: {price_text}",
                inline=True
            )
        
        embed.add_field(
            name=tr(lang, 'how_to_buy'),
            value=tr(lang, 'use_buy_command'),
            inline=False
        )
        
        embed.add_field(
            name=tr(lang, 'inventory'),
            value=tr(lang, 'use_inv_command'),
            inline=False
        )
        
        embed.add_field(
            name=tr(lang, 'equip_title'),
            value=tr(lang, 'use_equip_command'),
            inline=False
        )
        
        embed.set_footer(text=f"{tr(lang, 'titles_shop')} • {interaction.guild.name}")
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in titles command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

@bot.tree.command(name="equip", description="Equip title from inventory")
async def equip(interaction: discord.Interaction, title_name: str):
    """Equips title from inventory"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        user_id = interaction.user.id
        
        if user_id not in config['player_titles']:
            embed = discord.Embed(
                title=tr(lang, 'no_titles'),
                description="",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        user_titles = config['player_titles'][user_id]
        
        if title_name not in user_titles['owned']:
            embed = discord.Embed(
                title=tr(lang, 'dont_have_title'),
                description="",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        user_titles['equipped'] = title_name
        await save_data_with_backup(interaction.guild.id)
        
        # АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ЛИДЕРБОРДА
        asyncio.create_task(auto_update_leaderboard(interaction.guild.id))
        
        embed = discord.Embed(
            title=tr(lang, 'title_equipped'),
            description=tr(lang, 'equipped_success', title=title_name),
            color=0xff0000
        )
        
        embed.add_field(
            name=tr(lang, 'view'),
            value=tr(lang, 'view_in_leaderboard'),
            inline=False
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in equip command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

@bot.tree.command(name="inv", description="Show titles inventory")
async def inv(interaction: discord.Interaction):
    """Shows titles inventory"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        user_id = interaction.user.id
        
        if user_id not in config['player_titles'] or not config['player_titles'][user_id]['owned']:
            embed = discord.Embed(
                title=tr(lang, 'inventory_title'),
                description=tr(lang, 'inventory_empty'),
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        user_titles = config['player_titles'][user_id]
        owned_titles = user_titles['owned']
        equipped_title = user_titles['equipped']
        
        embed = discord.Embed(
            title=tr(lang, 'inventory_title'),
            description=tr(lang, 'total_titles', count=len(owned_titles)),
            color=0xff0000
        )
        
        if equipped_title:
            embed.add_field(
                name=tr(lang, 'equipped_title'),
                value=f"**{equipped_title}**",
                inline=False
            )
        else:
            embed.add_field(
                name=tr(lang, 'equipped_title'),
                value=tr(lang, 'no_equipped'),
                inline=False
            )
        
        titles_text = ""
        for title in owned_titles:
            status = "👑" if title == equipped_title else "✅"
            titles_text += f"{status} **{title}**\n"
        
        embed.add_field(
            name=tr(lang, 'your_titles'),
            value=titles_text or tr(lang, 'no_titles'),
            inline=False
        )
        
        embed.add_field(
            name=tr(lang, 'equip_title'),
            value=tr(lang, 'use_equip_command'),
            inline=False
        )
        
        embed.add_field(
            name=tr(lang, 'unequip_title'),
            value=tr(lang, 'use_unequip_command'),
            inline=False
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in inv command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

@bot.tree.command(name="unequip", description="Unequip current title")
async def unequip(interaction: discord.Interaction):
    """Unequips current title"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        user_id = interaction.user.id
        
        if user_id not in config['player_titles'] or config['player_titles'][user_id]['equipped'] is None:
            embed = discord.Embed(
                title=tr(lang, 'no_equipped_title'),
                description="",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        old_title = config['player_titles'][user_id]['equipped']
        config['player_titles'][user_id]['equipped'] = None
        await save_data_with_backup(interaction.guild.id)
        
        # АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ЛИДЕРБОРДА
        asyncio.create_task(auto_update_leaderboard(interaction.guild.id))
        
        embed = discord.Embed(
            title=tr(lang, 'title_unequipped'),
            description=tr(lang, 'unequipped_success', title=old_title),
            color=0xff0000
        )
        
        embed.add_field(
            name=tr(lang, 'important_info'),
            value=tr(lang, 'not_shown_leaderboard'),
            inline=False
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in unequip command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

@bot.tree.command(name="buy", description="Buy title")
async def buy(interaction: discord.Interaction, title_name: str):
    """Buying title"""
    try:
        await safe_defer_response(interaction, ephemeral=False)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content=tr('en', 'command_server_only'))
            return
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        
        if title_name not in AVAILABLE_TITLES:
            embed = discord.Embed(
                title=tr(lang, 'title_not_exist'),
                description="",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        user_id = interaction.user.id
        if user_id not in config['player_titles']:
            config['player_titles'][user_id] = {'owned': [], 'equipped': None}
        
        user_titles = config['player_titles'][user_id]
        
        if title_name in user_titles['owned']:
            embed = discord.Embed(
                title=tr(lang, 'already_have_title'),
                description="",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        price = TITLE_PRICES[title_name]
        
        success, balance_data = await get_user_balance(interaction.guild.id, user_id)
        
        if not success:
            embed = discord.Embed(
                title=tr(lang, 'balance_check_failed', error=balance_data),
                description="",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        total_balance = balance_data.get('cash', 0) + balance_data.get('bank', 0)
        
        if total_balance < price:
            embed = discord.Embed(
                title=tr(lang, 'insufficient_funds'),
                description=tr(lang, 'you_have_need', have=total_balance, need=price),
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        if price > 0:
            success, message = await add_money_to_user(interaction.guild.id, user_id, -price)
            if not success:
                embed = discord.Embed(
                    title=tr(lang, 'payment_error'),
                    description=tr(lang, 'payment_failed', error=message),
                    color=0xff0000
                )
                await safe_edit_response(interaction, embed=embed)
                return
        
        user_titles['owned'].append(title_name)
        
        if user_titles['equipped'] is None:
            user_titles['equipped'] = title_name
        
        await save_data_with_backup(interaction.guild.id)
        
        # АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ЛИДЕРБОРДА
        asyncio.create_task(auto_update_leaderboard(interaction.guild.id))
        
        embed = discord.Embed(
            title=tr(lang, 'title_purchased'),
            description=tr(lang, 'purchased_success', title=title_name),
            color=0xff0000
        )
        
        if price > 0:
            embed.add_field(
                name=tr(lang, 'cost'),
                value=f"```{price:,}$```",
                inline=True
            )
        
        if user_titles['equipped'] == title_name:
            embed.add_field(
                name=tr(lang, 'status'),
                value=tr(lang, 'auto_equipped'),
                inline=True
            )
        
        embed.add_field(
            name=tr(lang, 'inventory'),
            value=tr(lang, 'now_have_titles', count=len(user_titles['owned'])),
            inline=False
        )
        
        embed.add_field(
            name=tr(lang, 'view'),
            value=tr(lang, 'view_in_lb'),
            inline=False
        )
        
        embed.set_footer(text=f"{tr(lang, 'titles_shop')} • {interaction.guild.name}")
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in buy command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

@bot.tree.command(name="leaderboard", description="Leaderboard by registration order")
async def leaderboard(interaction: discord.Interaction, page: int = 1):
    """Shows leaderboard"""
    try:
        await safe_defer_response(interaction, ephemeral=False)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content=tr('en', 'command_server_only'))
            return
        
        embed = await create_leaderboard_embed(interaction.guild.id, page)
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in leaderboard command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

# ==================== ОСТАЛЬНЫЕ КОМАНДЫ ====================

@bot.tree.command(name="cc", description="Give 'Content Creator' title (admins)")
@app_commands.default_permissions(administrator=True)
async def cc(interaction: discord.Interaction, player: discord.Member):
    """Gives special title Content Creator"""
    try:
        await safe_defer_response(interaction, ephemeral=False)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content=tr('en', 'command_server_only'))
            return
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        user_id = player.id
        
        if user_id not in config['player_titles']:
            config['player_titles'][user_id] = {'owned': [], 'equipped': None}
        
        user_titles = config['player_titles'][user_id]
        
        if "Content Creator" not in user_titles['owned']:
            user_titles['owned'].append("Content Creator")
        
        user_titles['equipped'] = "Content Creator"
        await save_data_with_backup(interaction.guild.id)
        
        # АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ЛИДЕРБОРДА
        asyncio.create_task(auto_update_leaderboard(interaction.guild.id))
        
        embed = discord.Embed(
            title=tr(lang, 'title_given'),
            description=tr(lang, 'title_given_to', user=player.mention),
            color=0xff0000
        )
        
        embed.add_field(
            name=tr(lang, 'view'),
            value=tr(lang, 'view_in_leaderboard'),
            inline=True
        )
        
        embed.set_footer(text=f"{tr(lang, 'special_title')} • {interaction.guild.name}")
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in cc command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

@bot.tree.command(name="set_leaderboard", description="Set leaderboard message (admins)")
@app_commands.default_permissions(administrator=True)
async def set_leaderboard(interaction: discord.Interaction):
    """Sets leaderboard message"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content=tr('en', 'command_server_only'))
            return
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        
        embed = await create_leaderboard_embed(interaction.guild.id)
        message = await interaction.channel.send(embed=embed)
        
        config['leaderboard_message_id'] = message.id
        config['leaderboard_channel_id'] = interaction.channel.id
        await save_data_with_backup(interaction.guild.id)
        
        embed = discord.Embed(
            title=tr(lang, 'leaderboard_set'),
            description=tr(lang, 'leaderboard_set_success'),
            color=0x00ff00
        )
        
        embed.add_field(
            name=tr(lang, 'auto_update'),
            value=tr(lang, 'auto_update_info'),
            inline=False
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in set_leaderboard command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

@bot.tree.command(name="update_leaderboard", description="Update leaderboard manually (admins)")
@app_commands.default_permissions(administrator=True)
async def update_leaderboard_cmd(interaction: discord.Interaction):
    """Updates leaderboard manually"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content=tr('en', 'command_server_only'))
            return
        
        await update_leaderboard(interaction.guild.id)
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        
        embed = discord.Embed(
            title=tr(lang, 'leaderboard_updated'),
            description=tr(lang, 'leaderboard_updated_success'),
            color=0x00ff00
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in update_leaderboard command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

@bot.tree.command(name="mytitle", description="Show your current title")
async def mytitle(interaction: discord.Interaction):
    """Shows player's current title"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content=tr('en', 'command_server_only'))
            return
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name)
        lang = config.get('language', 'en')
        user_id = interaction.user.id
        
        if user_id not in config['player_titles'] or config['player_titles'][user_id]['equipped'] is None:
            embed = discord.Embed(
                title=tr(lang, 'your_title'),
                description=tr(lang, 'no_equipped_yet'),
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        equipped_title = config['player_titles'][user_id]['equipped']
        
        embed = discord.Embed(
            title=tr(lang, 'your_title'),
            description=f"**{equipped_title}**",
            color=0xff0000
        )
        
        embed.add_field(
            name=tr(lang, 'view'),
            value=tr(lang, 'view_in_leaderboard'),
            inline=True
        )
        
        embed.add_field(
            name=tr(lang, 'total_titles_count'),
            value=f"```{len(config['player_titles'][user_id]['owned'])}```",
            inline=True
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in mytitle command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

@bot.tree.command(name="help", description="Show command help")
async def help_cmd(interaction: discord.Interaction):
    """Shows command help"""
    try:
        await safe_send_response(interaction, tr('en', 'processing_command'), ephemeral=True)
        
        config = get_guild_config(interaction.guild.id, interaction.guild.name) if interaction.guild else None
        lang = config.get('language', 'en') if config else 'en'
        
        embed = discord.Embed(
            title=tr(lang, 'help_title'),
            color=0xff0000
        )
        
        # Команды для всех
        embed.add_field(
            name=tr(lang, 'all_players'),
            value=tr(lang, 'all_players_commands'),
            inline=False
        )
        
        # Админ команды
        if interaction.user.guild_permissions.administrator:
            embed.add_field(
                name=tr(lang, 'admin_commands'),
                value=tr(lang, 'admin_commands_list'),
                inline=False
            )
        
        embed.set_footer(text=f"{tr(lang, 'registration_system')} • {interaction.guild.name if interaction.guild else 'Ink Game'}")
        await interaction.edit_original_response(embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in help command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

@bot.tree.command(name="ping", description="Check bot ping")
async def ping(interaction: discord.Interaction):
    """Shows bot latency"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        latency = round(bot.latency * 1000)
        config = get_guild_config(interaction.guild.id, interaction.guild.name) if interaction.guild else None
        lang = config.get('language', 'en') if config else 'en'
        
        embed = discord.Embed(
            title=tr(lang, 'pong'),
            color=0xff0000
        )
        embed.add_field(
            name=tr(lang, 'latency'),
            value=f"```{latency}ms```",
            inline=True
        )
        embed.add_field(
            name=tr(lang, 'status'),
            value=tr(lang, 'online_status'),
            inline=True
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in ping command: {e}")
        await safe_send_response(interaction, tr('en', 'error_occurred'), ephemeral=True)

# ==================== RENDER FIX ====================
app = Flask('')

@app.route('/')
def home():
    return "🤖 Discord Bot is Online! | Status: ✅ Running"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

def keep_alive():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    print(f"🌐 Flask server started for Render compatibility")

# Запускаем Flask сервер
keep_alive()

@bot.event
async def on_ready():
    logger.info(f'✅ Bot {bot.user} started!')
    logger.info(f'🆔 Bot ID: {bot.user.id}')
    
    # Загружаем данные из файла
    load_data()
    
    # Восстанавливаем игроков из ролей на всех серверах
    for guild in bot.guilds:
        logger.info(f"🔍 Checking server: {guild.name} ({guild.id})")
        config = get_guild_config(guild.id, guild.name)
        await restore_players_from_roles(guild, config)
    
    # Статистика по серверам
    for guild_id, config in GUILD_DATA.items():
        status = "open" if config['registration_open'] else "closed"
        logger.info(f"📊 Server {config['guild_name']}: {len(config['registered_players'])}/{config['max_players']} players, registration: {status}")
    
    await asyncio.sleep(2)
    
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ Loaded {len(synced)} commands")
    except Exception as e:
        logger.error(f"❌ Command sync error: {e}")

# Запуск бота
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
