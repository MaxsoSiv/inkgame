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

# Конфигурация
CONFIG = {
    'max_players': 90,
    'min_number': 1,
    'max_number': 456,
    'registration_role_name': 'Зарегистрирован',
    'used_numbers': set(),
    'registered_players': set(),
    'player_numbers': {},
    'registration_open': False,
    'game_active': False,
    'player_titles': {},  # {user_id: {'owned': [title1, title2], 'equipped': title}}
    'registration_order': [],
    'leaderboard_message_id': None,
    'leaderboard_channel_id': None,
    'prizes_distributed': False,  # Флаг для отслеживания выданных призов
    'backup_channel_id': 1438148552756039712  # ID канала для бэкапов
}

# Доступные титулы (цвета убраны)
AVAILABLE_TITLES = {
    "EchoFan": 0x800080,
    "Legend": 0x00FFFF,
    "Rich": 0xFFD700,
    "mastermind": 0xFFFFFF,
    "Контент Креэйтор": 0xFF0000
}

# Цены титулов
TITLE_PRICES = {
    "EchoFan": 12500,
    "Legend": 25000,
    "Rich": 35000,
    "mastermind": 50000,
    "Контент Креэйтор": 0
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
BACKUP_CHANNEL_ID = os.getenv('BACKUP_CHANNEL_ID')  # ID канала для бэкапов

# Проверка токенов при запуске
if not DISCORD_TOKEN:
    logger.error("❌ Ошибка: DISCORD_BOT_TOKEN не найден в .env файле")
    exit(1)

if not UNBELIEVABOAT_TOKEN:
    logger.error("❌ Ошибка: UNBELIEVABOAT_TOKEN не найден в .env файле")
    exit(1)

async def send_backup_to_channel():
    """Отправляет бэкап в указанный канал"""
    try:
        if not BACKUP_CHANNEL_ID:
            logger.warning("⚠️ BACKUP_CHANNEL_ID не установлен, пропускаем отправку бэкапа")
            return False
        
        channel = bot.get_channel(int(BACKUP_CHANNEL_ID))
        if not channel:
            logger.error("❌ Канал для бэкапов не найден")
            return False
        
        # Создаем временный файл для отправки
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"game_backup_{timestamp}.json"
        
        # Копируем текущий game_data.json во временный файл
        if os.path.exists('game_data.json'):
            import shutil
            shutil.copy2('game_data.json', backup_filename)
            
            # Создаем embed с информацией о бэкапе
            embed = discord.Embed(
                title="💾 АВТОМАТИЧЕСКИЙ БЭКАП",
                description="Создан автоматический бэкап данных игры",
                color=0x00ff00,
                timestamp=datetime.datetime.now()
            )
            
            embed.add_field(
                name="📊 Статистика",
                value=(
                    f"• Игроков: {len(CONFIG['registered_players'])}\n"
                    f"• Номеров: {len(CONFIG['used_numbers'])}\n"
                    f"• Титулов: {len(CONFIG['player_titles'])}\n"
                    f"• Регистрация: {'Открыта' if CONFIG['registration_open'] else 'Закрыта'}\n"
                    f"• Игра: {'Активна' if CONFIG['game_active'] else 'Неактивна'}"
                ),
                inline=True
            )
            
            embed.add_field(
                name="🕐 Время создания",
                value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                inline=True
            )
            
            embed.set_footer(text="Автоматическая система бэкапов • Ink Game")
            
            # Отправляем файл
            file = discord.File(backup_filename, filename=backup_filename)
            await channel.send(embed=embed, file=file)
            
            # Удаляем временный файл
            os.remove(backup_filename)
            
            logger.info("✅ Бэкап отправлен в канал")
            return True
        else:
            logger.warning("⚠️ Файл game_data.json не найден для бэкапа")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка отправки бэкапа: {e}")
        return False

async def save_data_with_backup():
    """Сохраняет данные и создает резервную копию с отправкой в канал"""
    if await save_data():
        # Создаем локальную резервную копию
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backups/game_data_backup_{timestamp}.json"
        
        if not os.path.exists('backups'):
            os.makedirs('backups')
        
        import shutil
        shutil.copy2('game_data.json', backup_filename)
        
        # Удаляем старые бэкапы (оставляем только 5 последних)
        backup_files = sorted([f for f in os.listdir('backups') if f.startswith('game_data_backup_')])
        if len(backup_files) > 5:
            for old_backup in backup_files[:-5]:
                os.remove(f"backups/{old_backup}")
        
        # Отправляем бэкап в канал
        await send_backup_to_channel()
        
        return True
    return False

async def save_data():
    """Сохраняет данные в файл (асинхронная версия)"""
    try:
        save_data = {
            'used_numbers': list(CONFIG['used_numbers']),
            'registered_players': list(CONFIG['registered_players']),
            'player_numbers': CONFIG['player_numbers'],
            'registration_open': CONFIG['registration_open'],
            'game_active': CONFIG['game_active'],
            'player_titles': CONFIG['player_titles'],
            'registration_order': CONFIG['registration_order'],
            'leaderboard_message_id': CONFIG['leaderboard_message_id'],
            'leaderboard_channel_id': CONFIG['leaderboard_channel_id'],
            'prizes_distributed': CONFIG['prizes_distributed'],
            'saved_at': str(datetime.datetime.now()),
            'version': '1.3'
        }
        
        temp_filename = 'game_data_temp.json'
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        if os.path.exists('game_data.json'):
            os.replace(temp_filename, 'game_data.json')
        else:
            os.rename(temp_filename, 'game_data.json')
            
        logger.info("✅ Данные сохранены")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения данных: {e}")
        try:
            if os.path.exists('game_data_temp.json'):
                os.remove('game_data_temp.json')
        except:
            pass
        return False

# ==================== СИСТЕМА ВОССТАНОВЛЕНИЯ ИЗ БЭКАПА ====================

async def restore_from_backup(backup_data):
    """Восстанавливает данные из бэкапа (асинхронная версия)"""
    try:
        # Сохраняем текущие данные как резервную копию перед восстановлением
        await save_data_with_backup()
        
        # Очищаем текущие данные
        CONFIG['used_numbers'].clear()
        CONFIG['registered_players'].clear()
        CONFIG['player_numbers'].clear()
        CONFIG['player_titles'].clear()
        CONFIG['registration_order'].clear()
        
        # Восстанавливаем used_numbers
        if 'used_numbers' in backup_data:
            CONFIG['used_numbers'] = set(backup_data['used_numbers'])
        
        # Восстанавливаем registered_players
        if 'registered_players' in backup_data:
            CONFIG['registered_players'] = set(backup_data['registered_players'])
        
        # Восстанавливаем player_numbers
        if 'player_numbers' in backup_data:
            CONFIG['player_numbers'] = {}
            for user_id_str, number_str in backup_data['player_numbers'].items():
                try:
                    user_id = int(user_id_str)
                    CONFIG['player_numbers'][user_id] = number_str
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Неверный user_id в бэкапе: {user_id_str}")
                    continue
        
        # Восстанавливаем player_titles
        if 'player_titles' in backup_data:
            CONFIG['player_titles'] = {}
            for user_id_str, title_data in backup_data['player_titles'].items():
                try:
                    user_id = int(user_id_str)
                    if isinstance(title_data, str):
                        CONFIG['player_titles'][user_id] = {
                            'owned': [title_data],
                            'equipped': title_data
                        }
                    else:
                        CONFIG['player_titles'][user_id] = title_data
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Неверный user_id в бэкапе титулов: {user_id_str}")
                    continue
        
        # Восстанавливаем registration_order
        if 'registration_order' in backup_data:
            CONFIG['registration_order'] = backup_data['registration_order']
        else:
            CONFIG['registration_order'] = list(CONFIG['registered_players'])
        
        # Восстанавливаем лидерборд
        if 'leaderboard_message_id' in backup_data:
            CONFIG['leaderboard_message_id'] = backup_data['leaderboard_message_id']
        if 'leaderboard_channel_id' in backup_data:
            CONFIG['leaderboard_channel_id'] = backup_data['leaderboard_channel_id']
        
        # Восстанавливаем флаги
        if 'registration_open' in backup_data:
            CONFIG['registration_open'] = backup_data['registration_open']
        if 'game_active' in backup_data:
            CONFIG['game_active'] = backup_data['game_active']
        if 'prizes_distributed' in backup_data:
            CONFIG['prizes_distributed'] = backup_data['prizes_distributed']
        else:
            CONFIG['prizes_distributed'] = False
        
        # Сохраняем восстановленные данные
        await save_data()
        
        logger.info("✅ Данные восстановлены из бэкапа")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка восстановления из бэкапа: {e}")
        return False

# ==================== СИСТЕМА ВОССТАНОВЛЕНИЯ ИЗ РОЛЕЙ ====================

async def restore_players_from_roles(guild):
    """Восстанавливает игроков из роли 'Зарегистрирован' при запуске бота"""
    try:
        logger.info("🔄 Проверка игроков с ролью 'Зарегистрирован'...")
        
        role = discord.utils.get(guild.roles, name=CONFIG['registration_role_name'])
        if not role:
            logger.info("⚠️ Роль 'Зарегистрирован' не найдена")
            return
        
        restored_count = 0
        for member in role.members:
            if member.id not in CONFIG['registered_players']:
                # Игрок есть в роли, но нет в данных - восстанавливаем
                logger.info(f"🔄 Восстановление игрока {member.display_name} ({member.id})")
                
                # Извлекаем номер из ника
                number_match = re.search(r'\((\d{3})\)$', member.display_name)
                if number_match:
                    player_number = int(number_match.group(1))
                    formatted_number = f"{player_number:03d}"
                    
                    # Проверяем, не занят ли номер
                    if player_number in CONFIG['used_numbers']:
                        # Генерируем новый номер
                        while True:
                            player_number = random.randint(CONFIG['min_number'], CONFIG['max_number'])
                            if player_number not in CONFIG['used_numbers']:
                                break
                        formatted_number = f"{player_number:03d}"
                    
                    CONFIG['used_numbers'].add(player_number)
                    CONFIG['registered_players'].add(member.id)
                    CONFIG['player_numbers'][member.id] = formatted_number
                    
                    if member.id not in CONFIG['registration_order']:
                        CONFIG['registration_order'].append(member.id)
                    
                    restored_count += 1
                    logger.info(f"✅ Восстановлен игрок {member.display_name} с номером {formatted_number}")
        
        if restored_count > 0:
            logger.info(f"✅ Восстановлено {restored_count} игроков из ролей")
            await save_data()  # Сохраняем восстановленные данные
        else:
            logger.info("ℹ️ Новых игроков для восстановления не найдено")
            
    except Exception as e:
        logger.error(f"❌ Ошибка восстановления игроков из ролей: {e}")

def load_data():
    """Загружает данные из файла"""
    try:
        if not os.path.exists('game_data.json'):
            logger.info("ℹ️ Файл данных не найден, начинаем с чистого листа")
            return True
            
        with open('game_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        CONFIG['used_numbers'].clear()
        CONFIG['registered_players'].clear()
        CONFIG['player_numbers'].clear()
        CONFIG['player_titles'].clear()
        CONFIG['registration_order'].clear()
        
        if 'used_numbers' in data:
            CONFIG['used_numbers'] = set(data['used_numbers'])
        
        if 'registered_players' in data:
            CONFIG['registered_players'] = set(data['registered_players'])
        
        if 'player_numbers' in data:
            CONFIG['player_numbers'] = {}
            for user_id_str, number_str in data['player_numbers'].items():
                try:
                    user_id = int(user_id_str)
                    CONFIG['player_numbers'][user_id] = number_str
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Неверный user_id в данных: {user_id_str}")
                    continue
        
        if 'player_titles' in data:
            CONFIG['player_titles'] = {}
            for user_id_str, title_data in data['player_titles'].items():
                try:
                    user_id = int(user_id_str)
                    if isinstance(title_data, str):
                        CONFIG['player_titles'][user_id] = {
                            'owned': [title_data],
                            'equipped': title_data
                        }
                    else:
                        CONFIG['player_titles'][user_id] = title_data
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Неверный user_id в данных титулов: {user_id_str}")
                    continue
        
        if 'registration_order' in data:
            CONFIG['registration_order'] = data['registration_order']
        else:
            CONFIG['registration_order'] = list(CONFIG['registered_players'])
        
        if 'leaderboard_message_id' in data:
            CONFIG['leaderboard_message_id'] = data['leaderboard_message_id']
        if 'leaderboard_channel_id' in data:
            CONFIG['leaderboard_channel_id'] = data['leaderboard_channel_id']
        
        if 'prizes_distributed' in data:
            CONFIG['prizes_distributed'] = data['prizes_distributed']
        else:
            CONFIG['prizes_distributed'] = False
        
        if 'registration_open' in data:
            CONFIG['registration_open'] = data['registration_open']
        if 'game_active' in data:
            CONFIG['game_active'] = data['game_active']
        
        logger.info("✅ Данные загружены")
        logger.info(f"📊 Загружено игроков: {len(CONFIG['registered_players'])}")
        logger.info(f"🔢 Использовано номеров: {len(CONFIG['used_numbers'])}")
        logger.info(f"🏆 Загружено титулов: {len(CONFIG['player_titles'])}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки данных: {e}")
        CONFIG['used_numbers'].clear()
        CONFIG['registered_players'].clear()
        CONFIG['player_numbers'].clear()
        CONFIG['player_titles'].clear()
        CONFIG['registration_order'].clear()
        CONFIG['leaderboard_message_id'] = None
        CONFIG['leaderboard_channel_id'] = None
        CONFIG['registration_open'] = False
        CONFIG['game_active'] = False
        CONFIG['prizes_distributed'] = False
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
                    return True, "Успешно"
                else:
                    error_text = await response.text()
                    return False, f"Ошибка {response.status}: {error_text}"
    except Exception as e:
        return False, f"Ошибка соединения: {e}"

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
                    return False, f"Ошибка {response.status}: {error_text}"
    except Exception as e:
        return False, f"Ошибка соединения: {e}"

async def update_leaderboard():
    """Обновляет сообщение лидерборда"""
    if not CONFIG['leaderboard_message_id'] or not CONFIG['leaderboard_channel_id']:
        logger.info("ℹ️ Лидерборд не установлен, пропускаем обновление")
        return
    
    try:
        channel = bot.get_channel(CONFIG['leaderboard_channel_id'])
        if not channel:
            logger.warning("❌ Канал лидерборда не найден")
            return
        
        message = await channel.fetch_message(CONFIG['leaderboard_message_id'])
        
        embed = await create_leaderboard_embed()
        await message.edit(embed=embed)
        logger.info("✅ Лидерборд обновлен")
        
    except discord.NotFound:
        logger.warning("❌ Сообщение лидерборда не найдено, сбрасываем настройки")
        CONFIG['leaderboard_message_id'] = None
        CONFIG['leaderboard_channel_id'] = None
        await save_data_with_backup()
    except Exception as e:
        logger.error(f"❌ Ошибка обновления лидерборда: {e}")

async def create_leaderboard_embed(page: int = 1):
    """Создает embed для лидерборда"""
    if not CONFIG['registration_order']:
        return discord.Embed(
            title="📊 ЛИДЕРБОРД",
            description="Пока нет зарегистрированных игроков",
            color=0xff0000
        )
    
    total_pages = (len(CONFIG['registration_order']) + 9) // 10
    if page < 1 or page > total_pages:
        page = 1
    
    embed = discord.Embed(
        title="📊 ЛИДЕРБОРД",
        description="Игроки в порядке регистрации",
        color=0xff0000
    )
    
    start_index = (page - 1) * 10
    end_index = min(start_index + 10, len(CONFIG['registration_order']))
    
    leaderboard_text = ""
    
    for i in range(start_index, end_index):
        user_id = CONFIG['registration_order'][i]
        user = bot.get_user(user_id)
        player_number = CONFIG['player_numbers'].get(user_id, "???")
        
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
            if user_id in CONFIG['player_titles']:
                equipped_title = CONFIG['player_titles'][user_id].get('equipped')
            
            # ИЗМЕНЕНИЕ: титул после ника и медалька перед
            if equipped_title:
                leaderboard_text += f"`#{i+1:2d}` {medal} {user.display_name} **[{equipped_title}]** ({player_number})\n"
            else:
                leaderboard_text += f"`#{i+1:2d}` {medal} {user.display_name} ({player_number})\n"
        else:
            leaderboard_text += f"`#{i+1:2d}` {medal} Unknown User ({player_number})\n"
    
    embed.add_field(
        name=f"🎮 Игроки ({start_index + 1}-{end_index})",
        value=leaderboard_text or "Нет данных",
        inline=False
    )
    
    # Добавляем информацию о призах для топ-3
    if CONFIG['registration_order'] and len(CONFIG['registration_order']) >= 3:
        embed.add_field(
            name="🏆 Призы за первые три места",
            value=(
                f"🥇 1 место: **{PRIZES[1]:,}$**\n"
                f"🥈 2 место: **{PRIZES[2]:,}$**\n" 
                f"🥉 3 место: **{PRIZES[3]:,}$**"
            ),
            inline=False
        )
    
    embed.set_footer(text=f"Страница {page}/{total_pages} • Лидерборд • Ink Game")
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
        logger.warning("⚠️ Взаимодействие не найдено (возможно истекло время)")
        return False
    except discord.errors.HTTPException as e:
        logger.error(f"❌ Ошибка HTTP при отправке ответа: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Неизвестная ошибка при отправке ответа: {e}")
        return False

async def safe_edit_response(interaction, *args, **kwargs):
    """Безопасное редактирование ответа"""
    try:
        await interaction.edit_original_response(*args, **kwargs)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при редактировании ответа: {e}")
        return False

async def safe_defer_response(interaction, ephemeral=False):
    """Безопасное откладывание ответа - УПРОЩЕННАЯ ВЕРСИЯ"""
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=ephemeral)
            return True
        return False
    except Exception as e:
        logger.warning(f"⚠️ Не удалось отложить ответ (возможно уже обработан): {e}")
        return False

# ==================== АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ЛИДЕРБОРДА ====================

async def auto_update_leaderboard():
    """Автоматически обновляет лидерборд с обработкой ошибок"""
    try:
        await update_leaderboard()
        logger.info("✅ Лидерборд автоматически обновлен")
    except Exception as e:
        logger.error(f"❌ Ошибка автоматического обновления лидерборда: {e}")

# ==================== СИСТЕМА ПРИЗОВ ====================

async def distribute_prizes(guild_id: int):
    """Распределяет призы за первые три места"""
    if not CONFIG['registration_order'] or len(CONFIG['registration_order']) < 3:
        return [], "Недостаточно игроков для распределения призов"
    
    if CONFIG['prizes_distributed']:
        return [], "Призы уже были распределены ранее"
    
    prize_results = []
    errors = []
    
    # Распределяем призы для топ-3
    for place in range(1, 4):
        if len(CONFIG['registration_order']) >= place:
            user_id = CONFIG['registration_order'][place - 1]  # -1 потому что индексы с 0
            prize_amount = PRIZES[place]
            
            success, message = await add_money_to_user(guild_id, user_id, prize_amount)
            
            user = bot.get_user(user_id)
            username = user.display_name if user else f"ID {user_id}"
            
            if success:
                prize_results.append(f"🥇 {place} место: {username} - {prize_amount:,}$")
                logger.info(f"🏆 Приз выдан: {username} - {prize_amount}$")
            else:
                errors.append(f"{place} место ({username}): {message}")
                logger.error(f"❌ Ошибка выдачи приза {place} место: {message}")
    
    CONFIG['prizes_distributed'] = True
    await save_data_with_backup()
    
    return prize_results, errors

# ==================== КОМАНДЫ ТИТУЛОВ ====================

@bot.tree.command(name="titles", description="Магазин титулов")
async def titles(interaction: discord.Interaction):
    """Показывает доступные титулы для покупки"""
    try:
        # Упрощенный defer без thinking
        await safe_defer_response(interaction, ephemeral=False)
        
        user_titles = CONFIG['player_titles'].get(interaction.user.id, {'owned': [], 'equipped': None})
        owned_titles = user_titles['owned']
        
        embed = discord.Embed(
            title="🏆 МАГАЗИН ТИТУЛОВ",
            description="Приобретите уникальный титул для отображения в лидерборде!",
            color=0xff0000
        )
        
        for title, color in AVAILABLE_TITLES.items():
            price = TITLE_PRICES[title]
            price_text = "🎁 Бесплатно (выдается админами)" if price == 0 else f"💵 {price:,}$"
            
            status = "✅ Куплен" if title in owned_titles else "🛒 Доступен"
            
            # ИЗМЕНЕНИЕ: убрано упоминание цвета
            embed.add_field(
                name=f"**{title}** - {status}",
                value=f"Цена: {price_text}",
                inline=True
            )
        
        embed.add_field(
            name="🛒 Как купить",
            value="Используйте команду `/buy <название_титула>` для покупки",
            inline=False
        )
        
        embed.add_field(
            name="🎒 Инвентарь",
            value="Используйте `/inv` для просмотра ваших титулов",
            inline=False
        )
        
        embed.add_field(
            name="👑 Надеть титул",
            value="Используйте `/equip <титул>` чтобы надеть титул",
            inline=False
        )
        
        embed.set_footer(text="Магазин титулов • Ink Game")
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде titles: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при выполнении команды", ephemeral=True)

@bot.tree.command(name="equip", description="Надеть титул из инвентаря")
async def equip(interaction: discord.Interaction, название_титула: str):
    """Надевает титул из инвентаря"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        user_id = interaction.user.id
        
        if user_id not in CONFIG['player_titles']:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="У вас нет титулов",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        user_titles = CONFIG['player_titles'][user_id]
        
        if название_титула not in user_titles['owned']:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="У вас нет этого титула",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        user_titles['equipped'] = название_титула
        await save_data_with_backup()
        
        # АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ЛИДЕРБОРДА
        asyncio.create_task(auto_update_leaderboard())
        
        # ИЗМЕНЕНИЕ: убрано упоминание цвета
        embed = discord.Embed(
            title="👑 ТИТУЛ НАДЕТ",
            description=f"Вы надели титул **{название_титула}**!",
            color=0xff0000  # Стандартный цвет вместо цвета титула
        )
        
        embed.add_field(
            name="👀 Просмотр",
            value="Теперь ваш титул отображается в лидерборде",
            inline=False
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде equip: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при надевании титула", ephemeral=True)

@bot.tree.command(name="inv", description="Показать инвентарь титулов")
async def inv(interaction: discord.Interaction):
    """Показывает инвентарь титулов"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        user_id = interaction.user.id
        
        if user_id not in CONFIG['player_titles'] or not CONFIG['player_titles'][user_id]['owned']:
            embed = discord.Embed(
                title="🎒 ИНВЕНТАРЬ ТИТУЛОВ",
                description="У вас пока нет титулов. Используйте `/titles` для покупки.",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        user_titles = CONFIG['player_titles'][user_id]
        owned_titles = user_titles['owned']
        equipped_title = user_titles['equipped']
        
        embed = discord.Embed(
            title="🎒 ИНВЕНТАРЬ ТИТУЛОВ",
            description=f"Всего титулов: {len(owned_titles)}",
            color=0xff0000
        )
        
        if equipped_title:
            embed.add_field(
                name="👑 Надетый титул",
                value=f"**{equipped_title}**",
                inline=False
            )
        else:
            embed.add_field(
                name="👑 Надетый титул",
                value="❌ Нет надетого титула",
                inline=False
            )
        
        titles_text = ""
        for title in owned_titles:
            status = "👑" if title == equipped_title else "✅"
            titles_text += f"{status} **{title}**\n"
        
        embed.add_field(
            name="📜 Ваши титулы",
            value=titles_text or "Нет титулов",
            inline=False
        )
        
        embed.add_field(
            name="👑 Надеть титул",
            value="Используйте `/equip <название_титула>` чтобы надеть титул",
            inline=False
        )
        
        embed.add_field(
            name="❌ Снять титул",
            value="Используйте `/unequip` чтобы снять текущий титул",
            inline=False
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде inv: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при показе инвентаря", ephemeral=True)

@bot.tree.command(name="unequip", description="Снять текущий титул")
async def unequip(interaction: discord.Interaction):
    """Снимает текущий титул"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        user_id = interaction.user.id
        
        if user_id not in CONFIG['player_titles'] or CONFIG['player_titles'][user_id]['equipped'] is None:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="У вас нет надетого титула",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        old_title = CONFIG['player_titles'][user_id]['equipped']
        CONFIG['player_titles'][user_id]['equipped'] = None
        await save_data_with_backup()
        
        # АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ЛИДЕРБОРДА
        asyncio.create_task(auto_update_leaderboard())
        
        embed = discord.Embed(
            title="❌ ТИТУЛ СНЯТ",
            description=f"Вы сняли титул **{old_title}**",
            color=0xff0000
        )
        
        embed.add_field(
            name="💡 Информация",
            value="Теперь в лидерборде ваш титул не отображается",
            inline=False
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде unequip: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при снятии титула", ephemeral=True)

@bot.tree.command(name="buy", description="Купить титул")
async def buy(interaction: discord.Interaction, название_титула: str):
    """Покупка титула"""
    try:
        await safe_defer_response(interaction, ephemeral=False)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content="❌ Эта команда работает только на сервере")
            return
        
        if название_титула not in AVAILABLE_TITLES:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Такого титула не существует. Используйте `/titles` для просмотра доступных титулов.",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        user_id = interaction.user.id
        if user_id not in CONFIG['player_titles']:
            CONFIG['player_titles'][user_id] = {'owned': [], 'equipped': None}
        
        user_titles = CONFIG['player_titles'][user_id]
        
        if название_титула in user_titles['owned']:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="У вас уже есть этот титул!",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        price = TITLE_PRICES[название_титула]
        
        success, balance_data = await get_user_balance(interaction.guild.id, user_id)
        
        if not success:
            embed = discord.Embed(
                title="❌ Ошибка",
                description=f"Не удалось проверить баланс: {balance_data}",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        total_balance = balance_data.get('cash', 0) + balance_data.get('bank', 0)
        
        if total_balance < price:
            embed = discord.Embed(
                title="❌ Недостаточно средств",
                description=f"У вас {total_balance:,}$, а нужно {price:,}$",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        if price > 0:
            success, message = await add_money_to_user(interaction.guild.id, user_id, -price)
            if not success:
                embed = discord.Embed(
                    title="❌ Ошибка оплаты",
                    description=f"Не удалось списать средства: {message}",
                    color=0xff0000
                )
                await safe_edit_response(interaction, embed=embed)
                return
        
        user_titles['owned'].append(название_титула)
        
        if user_titles['equipped'] is None:
            user_titles['equipped'] = название_титула
        
        await save_data_with_backup()
        
        # АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ЛИДЕРБОРДА
        asyncio.create_task(auto_update_leaderboard())
        
        # ИЗМЕНЕНИЕ: убрано упоминание цвета
        embed = discord.Embed(
            title="✅ ТИТУЛ ПРИОБРЕТЕН",
            description=f"Вы успешно приобрели титул **{название_титула}**!",
            color=0xff0000  # Стандартный цвет вместо цвета титула
        )
        
        if price > 0:
            embed.add_field(
                name="💵 Стоимость",
                value=f"```{price:,}$```",
                inline=True
            )
        
        # ИЗМЕНЕНИЕ: убрано поле с цветом
        
        if user_titles['equipped'] == название_титула:
            embed.add_field(
                name="👑 Статус",
                value="Титул автоматически надет",
                inline=True
            )
        
        embed.add_field(
            name="🎒 Инвентарь",
            value=f"Теперь у вас {len(user_titles['owned'])} титулов",
            inline=False
        )
        
        embed.add_field(
            name="👀 Просмотр",
            value="Ваш титул теперь отображается в лидерборде",
            inline=False
        )
        
        embed.set_footer(text="Магазин титулов • Ink Game")
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде buy: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при покупке титула", ephemeral=True)

@bot.tree.command(name="leaderboard", description="Таблица лидеров по порядку регистрации")
async def leaderboard(interaction: discord.Interaction, страница: int = 1):
    """Показывает таблицу лидеров"""
    try:
        await safe_defer_response(interaction, ephemeral=False)
        
        embed = await create_leaderboard_embed(страница)
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде leaderboard: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при показе лидерборда", ephemeral=True)

@bot.tree.command(name="cc", description="Выдать титул 'Контент Креэйтор' (админы)")
@app_commands.default_permissions(administrator=True)
async def cc(interaction: discord.Interaction, игрок: discord.Member):
    """Выдает специальный титул Контент Креэйтор"""
    try:
        await safe_defer_response(interaction, ephemeral=False)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content="❌ Эта команда работает только на сервере")
            return
        
        user_id = игрок.id
        
        if user_id not in CONFIG['player_titles']:
            CONFIG['player_titles'][user_id] = {'owned': [], 'equipped': None}
        
        user_titles = CONFIG['player_titles'][user_id]
        
        if "Контент Креэйтор" not in user_titles['owned']:
            user_titles['owned'].append("Контент Креэйтор")
        
        user_titles['equipped'] = "Контент Креэйтор"
        await save_data_with_backup()
        
        # АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ЛИДЕРБОРДА
        asyncio.create_task(auto_update_leaderboard())
        
        # ИЗМЕНЕНИЕ: убрано упоминание цвета
        embed = discord.Embed(
            title="🎁 ТИТУЛ ВЫДАН",
            description=f"Игрок {игрок.mention} получил титул **Контент Креэйтор**!",
            color=0xff0000
        )
        
        # ИЗМЕНЕНИЕ: убрано поле с цветом титула
        
        embed.add_field(
            name="👀 Просмотр",
            value="Титул отображается в лидерборде",
            inline=True
        )
        
        embed.set_footer(text="Специальный титул • Ink Game")
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде cc: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при выдаче титула", ephemeral=True)

@bot.tree.command(name="set_leaderboard", description="Установить сообщение лидерборда (админы)")
@app_commands.default_permissions(administrator=True)
async def set_leaderboard(interaction: discord.Interaction):
    """Устанавливает сообщение лидерборда"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        embed = await create_leaderboard_embed()
        message = await interaction.channel.send(embed=embed)
        
        CONFIG['leaderboard_message_id'] = message.id
        CONFIG['leaderboard_channel_id'] = interaction.channel.id
        await save_data_with_backup()
        
        embed = discord.Embed(
            title="✅ ЛИДЕРБОРД УСТАНОВЛЕН",
            description="Сообщение лидерборда успешно установлено!",
            color=0x00ff00
        )
        
        embed.add_field(
            name="📊 Автообновление",
            value="Лидерборд будет автоматически обновляться при:\n• Регистрации новых игроков\n• Покупке титулов\n• Смене титулов\n• Снятии титулов\n• Выдаче титулов админами",
            inline=False
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде set_leaderboard: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при установке лидерборда", ephemeral=True)

@bot.tree.command(name="update_leaderboard", description="Обновить лидерборд вручную (админы)")
@app_commands.default_permissions(administrator=True)
async def update_leaderboard_cmd(interaction: discord.Interaction):
    """Обновляет лидерборд вручную"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        await update_leaderboard()
        
        embed = discord.Embed(
            title="✅ ЛИДЕРБОРД ОБНОВЛЕН",
            description="Лидерборд успешно обновлен!",
            color=0x00ff00
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде update_leaderboard: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при обновлении лидерборда", ephemeral=True)

@bot.tree.command(name="mytitle", description="Показать ваш текущий титул")
async def mytitle(interaction: discord.Interaction):
    """Показывает текущий титул игрока"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        user_id = interaction.user.id
        
        if user_id not in CONFIG['player_titles'] or CONFIG['player_titles'][user_id]['equipped'] is None:
            embed = discord.Embed(
                title="🏆 ВАШ ТИТУЛ",
                description="У вас пока нет надетого титула. Используйте `/titles` для покупки и `/equip` для надевания.",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        equipped_title = CONFIG['player_titles'][user_id]['equipped']
        
        embed = discord.Embed(
            title="🏆 ВАШ ТИТУЛ",
            description=f"**{equipped_title}**",
            color=0xff0000  # Стандартный цвет вместо цвета титула
        )
        
        # ИЗМЕНЕНИЕ: убрано поле с цветом
        
        embed.add_field(
            name="👀 Просмотр",
            value="Ваш титул отображается в лидерборде",
            inline=True
        )
        
        embed.add_field(
            name="🎒 Всего титулов",
            value=f"```{len(CONFIG['player_titles'][user_id]['owned'])}```",
            inline=True
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде mytitle: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при показе титула", ephemeral=True)

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

@bot.tree.command(name="start", description="Открыть регистрацию для всех игроков (только для админов)")
@app_commands.default_permissions(administrator=True)
async def start(interaction: discord.Interaction):
    """Открытие регистрации"""
    try:
        await safe_defer_response(interaction, ephemeral=False)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content="❌ Эта команда работает только на сервере")
            return
            
        if CONFIG['registration_open']:
            embed = discord.Embed(
                title="🚫 Ошибка",
                description="Регистрация уже открыта!",
                color=0xff0000
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            return
        
        CONFIG['registration_open'] = True
        CONFIG['game_active'] = True
        CONFIG['prizes_distributed'] = False  # Сбрасываем флаг призов при новом старте
        
        await save_data_with_backup()
        
        embed = discord.Embed(
            title="🎮 РЕГИСТРАЦИЯ ОТКРЫТА",
            description="Игроки теперь могут присоединиться к событию",
            color=0xff0000
        )
        embed.add_field(
            name="📊 Статистика",
            value=f"```Доступно мест: {CONFIG['max_players'] - len(CONFIG['registered_players'])}/{CONFIG['max_players']}\nДиапазон номеров: {CONFIG['min_number']:03d}-{CONFIG['max_number']:03d}```",
            inline=False
        )
        embed.add_field(
            name="🎯 Команда для регистрации",
            value="```/reg```",
            inline=True
        )
        embed.add_field(
            name="📋 Проверить статус",
            value="```/status```",
            inline=True
        )
        embed.set_footer(text="Система регистрации • Ink Game")
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде start: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при открытии регистрации", ephemeral=True)

@bot.tree.command(name="reg", description="Зарегистрироваться в игре")
async def reg(interaction: discord.Interaction):
    """Команда для регистрации игрока"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content="❌ Эта команда работает только на сервере")
            return
        
        if not CONFIG['registration_open']:
            embed = discord.Embed(
                title="🚫 Регистрация закрыта",
                description="Ожидайте открытия регистрации администратором",
                color=0xff0000
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            return
        
        if len(CONFIG['registered_players']) >= CONFIG['max_players']:
            embed = discord.Embed(
                title="🎯 Все места заняты",
                description="Регистрация завершена, все 60 мест распределены",
                color=0xff0000
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            return
        
        if interaction.user.id in CONFIG['registered_players']:
            embed = discord.Embed(
                title="⚠️ Уже зарегистрирован",
                description="Вы уже участвуете в событии",
                color=0xff0000
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            return
        
        if len(CONFIG['used_numbers']) >= (CONFIG['max_number'] - CONFIG['min_number'] + 1):
            embed = discord.Embed(
                title="❌ Ошибка системы",
                description="Все номера распределены",
                color=0xff0000
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            return
        
        while True:
            player_number = random.randint(CONFIG['min_number'], CONFIG['max_number'])
            if player_number not in CONFIG['used_numbers']:
                CONFIG['used_numbers'].add(player_number)
                break
        
        formatted_number = f"{player_number:03d}"
        
        CONFIG['registered_players'].add(interaction.user.id)
        CONFIG['player_numbers'][interaction.user.id] = formatted_number
        if interaction.user.id not in CONFIG['registration_order']:
            CONFIG['registration_order'].append(interaction.user.id)
        
        await save_data_with_backup()
        
        # АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ЛИДЕРБОРДА ПРИ РЕГИСТРАЦИИ
        asyncio.create_task(auto_update_leaderboard())
        
        registration_role = discord.utils.get(interaction.guild.roles, name=CONFIG['registration_role_name'])
        
        if not registration_role:
            try:
                registration_role = await interaction.guild.create_role(
                    name=CONFIG['registration_role_name'],
                    color=0xff0000,
                    reason="Роль для зарегистрированных игроков"
                )
            except discord.Forbidden:
                embed = discord.Embed(
                    title="❌ Ошибка прав доступа",
                    description="Не удалось создать роль",
                    color=0xff0000
                )
                await safe_edit_response(interaction, embed=embed)
                return
        
        member = cast(discord.Member, interaction.user)
        try:
            await member.add_roles(registration_role)
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Ошибка прав доступа",
                description="Не удалось выдать роль",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        try:
            new_nickname = add_number_to_nick(member.display_name, formatted_number)
            await member.edit(nick=new_nickname)
        except discord.Forbidden:
            pass
        
        embed = discord.Embed(
            title="✅ РЕГИСТРАЦИЯ УСПЕШНА",
            description=(
                f"Добро пожаловать в игру...\n\n"
                f"Ожидайте начало игры...\n"
                f"**Номер {formatted_number}**"
            ),
            color=0xff0000
        )
        embed.add_field(
            name="🎫 Ваш игровой номер",
            value=f"```{formatted_number}```",
            inline=False
        )
        embed.add_field(
            name="📊 Ваше место в списке",
            value=f"```{len(CONFIG['registered_players'])}/{CONFIG['max_players']}```",
            inline=True
        )
        embed.add_field(
            name="🎯 Статус",
            value="```Зарегистрирован```",
            inline=True
        )
        embed.add_field(
            name="💡 Важная информация",
            value="Во время события ваш номер будет вашим идентификатором",
            inline=False
        )
        embed.set_footer(text="Система регистрации • Ink Game")
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде reg: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при регистрации", ephemeral=True)

@bot.tree.command(name="status", description="Проверить статус регистрации")
async def status(interaction: discord.Interaction):
    """Команда для проверки статуса регистрации"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        available_spots = CONFIG['max_players'] - len(CONFIG['registered_players'])
        
        embed = discord.Embed(
            title="📊 СТАТУС РЕГИСТРАЦИИ",
            color=0xff0000
        )
        
        # Статус регистрации
        if CONFIG['registration_open']:
            reg_status = "🟢 ОТКРЫТА"
            reg_description = "Регистрация активна, можно присоединиться"
        else:
            reg_status = "🔴 ЗАКРЫТА"
            reg_description = "Регистрация неактивна"
        
        # Статус игры
        if CONFIG['game_active']:
            game_status = "🟢 АКТИВНА"
            game_description = "Событие в процессе"
        else:
            game_status = "🔴 ЗАВЕРШЕНА"
            game_description = "Событие завершено"
        
        embed.add_field(
            name="🎯 Статус регистрации",
            value=f"```{reg_status}```\n{reg_description}",
            inline=True
        )
        embed.add_field(
            name="🎮 Статус игры",
            value=f"```{game_status}```\n{game_description}",
            inline=True
        )
        
        embed.add_field(
            name="👥 Зарегистрировано",
            value=f"```{len(CONFIG['registered_players'])}/{CONFIG['max_players']} игроков```",
            inline=True
        )
        embed.add_field(
            name="🎫 Свободных мест",
            value=f"```{available_spots} мест```",
            inline=True
        )
        embed.add_field(
            name="🔢 Использовано номеров",
            value=f"```{len(CONFIG['used_numbers'])} из {CONFIG['max_number'] - CONFIG['min_number'] + 1}```",
            inline=True
        )
        
        if CONFIG['registration_open'] and available_spots > 0:
            embed.add_field(
                name="🎮 Присоединиться",
                value="Используйте команду `/reg` для регистрации",
                inline=False
            )
        
        embed.set_footer(text="Система регистрации • Ink Game")
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде status: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при проверке статуса", ephemeral=True)

@bot.tree.command(name="end", description="Закрыть регистрацию или завершить игру (только для админов)")
@app_commands.default_permissions(administrator=True)
async def end(interaction: discord.Interaction):
    """Закрытие регистрации или завершение игры"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content="❌ Эта команда работает только на сервере")
            return
        
        if not CONFIG['game_active']:
            embed = discord.Embed(
                title="🎮 ИГРА УЖЕ ЗАВЕРШЕНА",
                description="Событие уже было завершено ранее",
                color=0xff0000
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            return
        
        if CONFIG['registration_open']:
            # Первое использование - закрываем регистрацию
            CONFIG['registration_open'] = False
            
            # Сохраняем изменения
            await save_data_with_backup()
            
            embed = discord.Embed(
                title="🔒 РЕГИСТРАЦИЯ ЗАКРЫТА",
                description="Новые игроки не могут присоединиться. Игра продолжается для зарегистрированных участников.",
                color=0xff0000
            )
            embed.add_field(
                name="📊 Статистика",
                value=f"```Зарегистрировано игроков: {len(CONFIG['registered_players'])}/{CONFIG['max_players']}```",
                inline=False
            )
            embed.add_field(
                name="💡 Следующий шаг",
                value="Для полного завершения события используйте команду `/end` еще раз",
                inline=False
            )
            embed.set_footer(text="Система регистрации • Ink Game")
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            
        else:
            # Второе использование - завершаем игру полностью
            CONFIG['game_active'] = False
            
            if not CONFIG['registered_players']:
                embed = discord.Embed(
                    title="🎮 ИГРА ЗАВЕРШЕНА",
                    description="Нет активных игроков для завершения",
                    color=0xff0000
                )
                embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
                await safe_edit_response(interaction, embed=embed)
                return
            
            registration_role = discord.utils.get(interaction.guild.roles, name=CONFIG['registration_role_name'])
            reset_count = 0
            money_sent_count = 0
            money_errors = []
            role_errors = []
            nick_errors = []
            
            # Начисляем деньги и сбрасываем игроков
            processing_embed = discord.Embed(
                title="⏳ ЗАВЕРШЕНИЕ ИГРЫ",
                description="Идет процесс завершения... Начисление денег и сброс данных",
                color=0xff0000
            )
            processing_embed.add_field(
                name="📊 Прогресс",
                value="```Обработка игроков...```",
                inline=False
            )
            await safe_edit_response(interaction, embed=processing_embed)
            
            # Распределяем призы для топ-3 игроков (если еще не распределены)
            prize_results = []
            prize_errors = []
            if not CONFIG['prizes_distributed'] and len(CONFIG['registration_order']) >= 3:
                prize_results, prize_errors = await distribute_prizes(interaction.guild.id)
            
            # Обрабатываем каждого игрока
            for user_id in list(CONFIG['registered_players']):
                try:
                    member = await interaction.guild.fetch_member(user_id)
                    
                    # Начисляем базовые деньги через UnbelievaBoat (25000 каждому)
                    success, message = await add_money_to_user(interaction.guild.id, user_id, 25000)
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
            total_players = len(CONFIG['registered_players'])
            CONFIG['used_numbers'].clear()
            CONFIG['registered_players'].clear()
            CONFIG['player_numbers'].clear()
            CONFIG['registration_order'].clear()
            # ТИТУЛЫ НЕ УДАЛЯЕМ - они сохраняются навсегда
            
            # Сохраняем изменения
            await save_data_with_backup()
            
            # Финальное сообщение
            result_embed = discord.Embed(
                title="🎮 ИГРА ЗАВЕРШЕНА",
                description="Событие полностью завершено, все данные сброшены",
                color=0xff0000
            )
            result_embed.add_field(
                name="📊 Результаты завершения",
                value=f"```Успешно сброшено: {reset_count}/{total_players} игроков\nДеньги начислены: {money_sent_count}/{total_players}```",
                inline=False
            )
            result_embed.add_field(
                name="💰 Награды",
                value="Каждый участник получил **25,000$**",
                inline=False
            )
            
            # Добавляем информацию о призах если они были распределены
            if prize_results:
                result_embed.add_field(
                    name="🏆 Призы за первые три места",
                    value="\n".join(prize_results),
                    inline=False
                )
            
            result_embed.add_field(
                name="🔄 Выполненные действия",
                value="• Регистрация закрыта\n• Игра завершена\n• Роли удалены\n• Ники восстановлены\n• Данные очищены\n• Деньги начислены\n• 🏆 Титулы сохранены",
                inline=False
            )
            
            # Показываем ошибки если есть
            if role_errors:
                result_embed.add_field(
                    name="⚠️ Ошибки удаления ролей",
                    value=f"Не удалось убрать роль у {len(role_errors)} игроков",
                    inline=False
                )
            
            if nick_errors:
                result_embed.add_field(
                    name="⚠️ Ошибки восстановления ников",
                    value=f"Не удалось восстановить ники у {len(nick_errors)} игроков",
                    inline=False
                )
            
            if money_errors:
                error_text = "\n".join(money_errors[:3])  # Показываем первые 3 ошибки
                if len(money_errors) > 3:
                    error_text += f"\n... и еще {len(money_errors) - 3} ошибок"
                result_embed.add_field(
                    name="⚠️ Ошибки начисления денег",
                    value=f"```{error_text}```",
                    inline=False
                )
            
            if prize_errors:
                error_text = "\n".join(prize_errors[:3])
                if len(prize_errors) > 3:
                    error_text += f"\n... и еще {len(prize_errors) - 3} ошибок"
                result_embed.add_field(
                    name="⚠️ Ошибки распределения призов",
                    value=f"```{error_text}```",
                    inline=False
                )
            
            result_embed.set_footer(text="Система регистрации • Ink Game")
            result_embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            
            await safe_edit_response(interaction, embed=result_embed)
            
    except Exception as e:
        logger.error(f"❌ Ошибка в команде end: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при завершении игры", ephemeral=True)

# ==================== ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ ====================

@bot.tree.command(name="help", description="Показать справку по командам")
async def help_cmd(interaction: discord.Interaction):
    """Показывает справку по командам"""
    try:
        await safe_send_response(interaction, "🔄 Загрузка справки...", ephemeral=True)
        
        embed = discord.Embed(
            title="📚 СПРАВКА ПО КОМАНДАМ",
            color=0xff0000
        )
        
        # Команды для всех
        embed.add_field(
            name="🎮 Для всех игроков",
            value=(
                "`/reg` - Зарегистрироваться\n"
                "`/status` - Статус регистрации\n"
                "`/mynumber` - Мой номер\n"
                "`/players` - Список участников\n"
                "`/ping` - Проверить пинг\n"
                "`/titles` - Магазин титулов\n"
                "`/buy` - Купить титул\n"
                "`/mytitle` - Мой титул\n"
                "`/leaderboard` - Таблица лидеров"
            ),
            inline=False
        )
        
        # Админ команды
        if interaction.user.guild_permissions.administrator:
            embed.add_field(
                name="⚙️ Для администраторов",
                value=(
                    "`/start` - Открыть регистрацию\n"
                    "`/end` - Завершить игру\n"
                    "`/list` - Список игроков\n"
                    "`/reset` - Сбросить игрока\n"
                    "`/broadcast` - Рассылка\n"
                    "`/changenumber` - Изменить номер\n"
                    "`/freenumbers` - Свободные номера\n"
                    "`/save` - Сохранить данные\n"
                    "`/load` - Загрузить данные\n"
                    "`/cc` - Выдать титул Контент Креэйтор\n"
                    "`/backup` - Создать резервную копию\n"
                    "`/restore` - Восстановить из копии"
                ),
                inline=False
            )
        
        embed.set_footer(text="Система регистрации • Ink Game")
        await interaction.edit_original_response(embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде help: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при показе справки", ephemeral=True)

@bot.tree.command(name="ping", description="Проверить пинг бота")
async def ping(interaction: discord.Interaction):
    """Показывает задержку бота"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        latency = round(bot.latency * 1000)
        
        embed = discord.Embed(
            title="🏓 PONG!",
            color=0xff0000
        )
        embed.add_field(
            name="📶 Задержка",
            value=f"```{latency}мс```",
            inline=True
        )
        embed.add_field(
            name="🟢 Статус",
            value="```Онлайн```",
            inline=True
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде ping: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при проверке пинга", ephemeral=True)

@bot.tree.command(name="freenumbers", description="Показать свободные номера (админы)")
@app_commands.default_permissions(administrator=True)
async def freenumbers(interaction: discord.Interaction):
    """Показывает свободные номера"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        all_numbers = set(range(CONFIG['min_number'], CONFIG['max_number'] + 1))
        free_numbers = all_numbers - CONFIG['used_numbers']
        
        if not free_numbers:
            await safe_edit_response(interaction, content="❌ Свободных номеров нет")
            return
        
        free_numbers_list = sorted(list(free_numbers))
        
        embed = discord.Embed(
            title="🎫 СВОБОДНЫЕ НОМЕРА",
            color=0xff0000
        )
        
        # Показываем первые 20 свободных номеров
        display_numbers = [f"{num:03d}" for num in free_numbers_list[:20]]
        embed.add_field(
            name=f"Доступно: {len(free_numbers)}",
            value=", ".join(display_numbers),
            inline=False
        )
        
        if len(free_numbers) > 20:
            embed.add_field(
                name="ℹ️ Показаны первые 20",
                value=f"Всего свободно: {len(free_numbers)} номеров",
                inline=False
            )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде freenumbers: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при показе свободных номеров", ephemeral=True)

@bot.tree.command(name="changenumber", description="Изменить номер игрока (админы)")
@app_commands.default_permissions(administrator=True)
async def changenumber(interaction: discord.Interaction, игрок: discord.Member, новый_номер: int):
    """Изменяет номер игрока"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if игрок.id not in CONFIG['registered_players']:
            await safe_edit_response(interaction, content="❌ Игрок не зарегистрирован")
            return
        
        if новый_номер < CONFIG['min_number'] or новый_номер > CONFIG['max_number']:
            await safe_edit_response(interaction, content=f"❌ Номер должен быть от {CONFIG['min_number']} до {CONFIG['max_number']}")
            return
        
        formatted_number = f"{новый_номер:03d}"
        
        # Удаляем старый номер
        old_number = CONFIG['player_numbers'].get(игрок.id)
        if old_number:
            old_number_int = int(old_number)
            if old_number_int in CONFIG['used_numbers']:
                CONFIG['used_numbers'].remove(old_number_int)
        
        # Добавляем новый номер
        CONFIG['used_numbers'].add(новый_номер)
        CONFIG['player_numbers'][игрок.id] = formatted_number
        
        await save_data_with_backup()
        
        # Обновляем ник
        try:
            new_nickname = add_number_to_nick(игрок.display_name, formatted_number)
            await игрок.edit(nick=new_nickname)
        except discord.Forbidden:
            pass
        
        embed = discord.Embed(
            title="🔢 НОМЕР ИЗМЕНЕН",
            description=f"Игроку {игрок.mention} установлен новый номер",
            color=0xff0000
        )
        embed.add_field(
            name="🎫 Новый номер",
            value=f"```{formatted_number}```",
            inline=True
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде changenumber: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при изменении номера", ephemeral=True)

@bot.tree.command(name="backup", description="Создать резервную копию данных (админы)")
@app_commands.default_permissions(administrator=True)
async def backup(interaction: discord.Interaction):
    """Создает и отправляет файл с резервной копией данных"""
    try:
        await safe_send_response(interaction, "🔄 Создаю резервную копию...", ephemeral=True)
        
        # Создаем файл бэкапа
        success = await send_backup_to_channel()
        
        if success:
            embed = discord.Embed(
                title="💾 РУЧНОЙ БЭКАП СОЗДАН",
                description="Бэкап данных успешно отправлен в канал",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ ОШИБКА БЭКАПА",
                description="Не удалось создать бэкап. Проверьте настройки канала.",
                color=0xff0000
            )
        
        await interaction.edit_original_response(embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде backup: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при создании бэкапа", ephemeral=True)

@bot.tree.command(name="set_backup_channel", description="Установить канал для автоматических бэкапов (админы)")
@app_commands.default_permissions(administrator=True)
async def set_backup_channel(interaction: discord.Interaction):
    """Устанавливает канал для автоматических бэкапов"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        CONFIG['backup_channel_id'] = interaction.channel.id
        await save_data_with_backup()
        
        embed = discord.Embed(
            title="✅ КАНАЛ ДЛЯ БЭКАПОВ УСТАНОВЛЕН",
            description="Этот канал будет использоваться для автоматических бэкапов данных",
            color=0x00ff00
        )
        
        embed.add_field(
            name="💾 Автоматические бэкапы",
            value="Бэкапы будут отправляться при:\n• Регистрации игроков\n• Покупке титулов\n• Изменении титулов\n• Завершении игры\n• Любых других изменениях данных",
            inline=False
        )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде set_backup_channel: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при установке канала для бэкапов", ephemeral=True)

@bot.tree.command(name="restore", description="Восстановить данные из резервной копии (админы)")
@app_commands.default_permissions(administrator=True)
async def restore(interaction: discord.Interaction, файл: discord.Attachment):
    """Восстанавливает данные из файла резервной копии"""
    try:
        await safe_send_response(interaction, "🔄 Проверяю файл...", ephemeral=True)
        
        # Проверяем что файл JSON
        if not файл.filename.endswith('.json'):
            embed = discord.Embed(
                title="❌ ОШИБКА ФОРМАТА",
                description="Пожалуйста, загрузите файл в формате JSON",
                color=0xff0000
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        # Скачиваем файл
        file_data = await файл.read()
        
        try:
            backup_data = json.loads(file_data.decode('utf-8'))
        except json.JSONDecodeError:
            embed = discord.Embed(
                title="❌ ОШИБКА ЧТЕНИЯ",
                description="Не удалось прочитать файл. Убедитесь, что это валидный JSON файл.",
                color=0xff0000
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        # Проверяем структуру данных
        required_fields = ['used_numbers', 'registered_players', 'player_numbers', 'player_titles']
        missing_fields = [field for field in required_fields if field not in backup_data]
        
        if missing_fields:
            embed = discord.Embed(
                title="❌ НЕВЕРНЫЙ ФОРМАТ",
                description=f"В файле отсутствуют обязательные поля: {', '.join(missing_fields)}",
                color=0xff0000
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        # Предупреждение о перезаписи
        warning_embed = discord.Embed(
            title="⚠️ ПРЕДУПРЕЖДЕНИЕ",
            description=(
                "Вы собираетесь восстановить данные из резервной копии.\n\n"
                "**ВСЕ ТЕКУЩИЕ ДАННЫЕ БУДУТ ПЕРЕЗАПИСАНЫ!**\n\n"
                "Это действие нельзя отменить.\n"
                "Пожалуйста, подтвердите восстановление."
            ),
            color=0xffa500
        )
        
        warning_embed.add_field(
            name="📊 Данные для восстановления",
            value=(
                f"• Игроков: {len(backup_data.get('registered_players', []))}\n"
                f"• Номеров: {len(backup_data.get('used_numbers', []))}\n"
                f"• Титулов: {len(backup_data.get('player_titles', {}))}\n"
                f"• Версия: {backup_data.get('version', 'Неизвестно')}"
            ),
            inline=False
        )
        
        warning_embed.add_field(
            name="🔄 Действие",
            value="Нажмите кнопку ниже для подтверждения восстановления",
            inline=False
        )
        
        # Создаем кнопки подтверждения
        class RestoreConfirmView(discord.ui.View):
            def __init__(self, backup_data):
                super().__init__(timeout=60)
                self.backup_data = backup_data
                self.confirmed = False
            
            @discord.ui.button(label="✅ Подтвердить восстановление", style=discord.ButtonStyle.danger)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.confirmed = True
                await self.perform_restore(interaction)
                self.stop()
            
            @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                embed = discord.Embed(
                    title="❌ ВОССТАНОВЛЕНИЕ ОТМЕНЕНО",
                    description="Действие отменено пользователем",
                    color=0xff0000
                )
                await interaction.response.edit_message(embed=embed, view=None)
                self.stop()
            
            async def perform_restore(self, interaction: discord.Interaction):
                try:
                    # Обновляем сообщение о начале восстановления
                    restoring_embed = discord.Embed(
                        title="🔄 ВОССТАНОВЛЕНИЕ ДАННЫХ",
                        description="Идет процесс восстановления...",
                        color=0xffa500
                    )
                    await interaction.response.edit_message(embed=restoring_embed, view=None)
                    
                    # Восстанавливаем данные с использованием асинхронной функции
                    success = await restore_from_backup(self.backup_data)
                    
                    if success:
                        # Обновляем лидерборд
                        asyncio.create_task(auto_update_leaderboard())
                        
                        # Сообщение об успехе
                        success_embed = discord.Embed(
                            title="✅ ДАННЫЕ ВОССТАНОВЛЕНЫ",
                            description="Все данные успешно восстановлены из резервной копии!",
                            color=0x00ff00
                        )
                        
                        success_embed.add_field(
                            name="📊 Восстановленные данные",
                            value=(
                                f"• Игроков: {len(CONFIG['registered_players'])}\n"
                                f"• Номеров: {len(CONFIG['used_numbers'])}\n"
                                f"• Титулов: {len(CONFIG['player_titles'])}\n"
                                f"• Регистрация: {'Открыта' if CONFIG['registration_open'] else 'Закрыта'}\n"
                                f"• Игра: {'Активна' if CONFIG['game_active'] else 'Неактивна'}"
                            ),
                            inline=False
                        )
                        
                        success_embed.add_field(
                            name="💡 Следующие шаги",
                            value=(
                                "• Проверьте корректность данных\n"
                                "• Убедитесь, что лидерборд отображается правильно\n"
                                "• При необходимости используйте `/update_leaderboard`"
                            ),
                            inline=False
                        )
                        
                        success_embed.set_footer(text=f"Восстановлено • {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        await interaction.edit_original_response(embed=success_embed)
                        
                        logger.info(f"✅ Данные восстановлены пользователем {interaction.user.display_name}")
                    else:
                        error_embed = discord.Embed(
                            title="❌ ОШИБКА ВОССТАНОВЛЕНИЯ",
                            description="Не удалось восстановить данные из файла",
                            color=0xff0000
                        )
                        await interaction.edit_original_response(embed=error_embed)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка при восстановлении данных: {e}")
                    error_embed = discord.Embed(
                        title="❌ ОШИБКА ВОССТАНОВЛЕНИЯ",
                        description=f"Произошла ошибка при восстановлении: {str(e)}",
                        color=0xff0000
                    )
                    await interaction.edit_original_response(embed=error_embed)
        
        # Отправляем предупреждение с кнопками
        view = RestoreConfirmView(backup_data)
        await interaction.edit_original_response(embed=warning_embed, view=view)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде restore: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при обработке файла", ephemeral=True)
@bot.tree.command(name="broadcast", description="Сделать объявление для всех игроков (админы)")
@app_commands.default_permissions(administrator=True)
async def broadcast(interaction: discord.Interaction, сообщение: str):
    """Отправляет сообщение всем зарегистрированным игрокам"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if not CONFIG['registered_players']:
            await safe_edit_response(interaction, content="❌ Нет игроков для рассылки")
            return
        
        embed = discord.Embed(
            title="📢 ОБЪЯВЛЕНИЕ",
            description=сообщение,
            color=0xff0000
        )
        embed.set_footer(text=f"От администратора • {interaction.user.display_name}")
        
        sent_count = 0
        error_count = 0
        
        await safe_edit_response(interaction, content=f"📤 Начинаю рассылку для {len(CONFIG['registered_players'])} игроков...")
        
        for user_id in CONFIG['registered_players']:
            try:
                user = await bot.fetch_user(user_id)
                await user.send(embed=embed)
                sent_count += 1
                await asyncio.sleep(0.5)  # Задержка чтобы не превысить лимиты Discord
            except:
                error_count += 1
        
        # Результат рассылки
        result_embed = discord.Embed(
            title="📊 РЕЗУЛЬТАТ РАССЫЛКИ",
            color=0xff0000
        )
        result_embed.add_field(
            name="✅ Успешно отправлено",
            value=f"```{sent_count} игрокам```",
            inline=True
        )
        result_embed.add_field(
            name="❌ Ошибки",
            value=f"```{error_count}```",
            inline=True
        )
        
        await interaction.followup.send(embed=result_embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде broadcast: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при рассылке", ephemeral=True)

@bot.tree.command(name="players", description="Показать список участников")
async def players(interaction: discord.Interaction):
    """Показывает количество участников"""
    try:
        await safe_defer_response(interaction, ephemeral=False)
        
        total_players = len(CONFIG['registered_players'])
        available_spots = CONFIG['max_players'] - total_players
        
        embed = discord.Embed(
            title="👥 УЧАСТНИКИ",
            color=0xff0000
        )
        embed.add_field(
            name="🎯 Зарегистрировано",
            value=f"```{total_players}/{CONFIG['max_players']} игроков```",
            inline=True
        )
        embed.add_field(
            name="🎫 Свободно мест",
            value=f"```{available_spots}```",
            inline=True
        )
        
        if total_players > 0:
            # Показываем только первые 10 игроков
            players_list = []
            count = 0
            for user_id in list(CONFIG['registered_players'])[:10]:
                user = bot.get_user(user_id)
                player_number = CONFIG['player_numbers'].get(user_id, "???")
                if user:
                    players_list.append(f"• {user.display_name} ({player_number})")
                    count += 1
            
            if players_list:
                embed.add_field(
                    name=f"🎮 Игроки (первые {count})",
                    value="\n".join(players_list),
                    inline=False
                )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде players: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при показе участников", ephemeral=True)

@bot.tree.command(name="mynumber", description="Показать ваш игровой номер")
async def mynumber(interaction: discord.Interaction):
    """Показывает номер игрока"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if interaction.user.id not in CONFIG['registered_players']:
            embed = discord.Embed(
                title="❌ Не зарегистрирован",
                description="Вы не зарегистрированы в игре",
                color=0xff0000
            )
            await safe_edit_response(interaction, embed=embed)
            return
        
        player_number = CONFIG['player_numbers'].get(interaction.user.id, "???")
        embed = discord.Embed(
            title="🎫 ВАШ НОМЕР",
            description=f"**Ваш игровой номер:** `{player_number}`",
            color=0xff0000
        )
        embed.add_field(
            name="💡 Информация",
            value="Этот номер будет вашим идентификатором во время события",
            inline=False
        )
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде mynumber: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при показе номера", ephemeral=True)

@bot.tree.command(name="reset", description="Сбросить регистрацию конкретного игрока (только для админов)")
@app_commands.default_permissions(administrator=True)
async def reset(interaction: discord.Interaction, игрок: discord.Member):
    """Сброс регистрации конкретного игрока"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if not interaction.guild:
            await safe_edit_response(interaction, content="❌ Эта команда работает только на сервере")
            return
            
        if игрок.id not in CONFIG['registered_players']:
            embed = discord.Embed(
                title="❌ Ошибка",
                description=f"{игрок.mention} не зарегистрирован в системе",
                color=0xff0000
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            return
        
        # Удаляем номер из использованных
        player_number = CONFIG['player_numbers'].get(игрок.id)
        if player_number:
            number_int = int(player_number)
            if number_int in CONFIG['used_numbers']:
                CONFIG['used_numbers'].remove(number_int)
        
        # Удаляем игрока из зарегистрированных
        CONFIG['registered_players'].discard(игрок.id)
        CONFIG['player_numbers'].pop(игрок.id, None)
        # УДАЛЯЕМ ИЗ ПОРЯДКА РЕГИСТРАЦИИ
        if игрок.id in CONFIG['registration_order']:
            CONFIG['registration_order'].remove(игрок.id)
        
        # Сохраняем изменения
        await save_data_with_backup()
        
        # АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ЛИДЕРБОРДА ПРИ УДАЛЕНИИ ИГРОКА
        asyncio.create_task(auto_update_leaderboard())
        
        # Убираем роль
        registration_role = discord.utils.get(interaction.guild.roles, name=CONFIG['registration_role_name'])
        if registration_role and registration_role in игрок.roles:
            try:
                await игрок.remove_roles(registration_role)
            except discord.Forbidden:
                embed = discord.Embed(
                    title="❌ Ошибка прав доступа",
                    description="Не удалось убрать роль",
                    color=0xff0000
                )
                await safe_edit_response(interaction, embed=embed)
                return
        
        # Возвращаем оригинальный ник
        try:
            original_nickname = remove_number_from_nick(игрок.display_name)
            if not original_nickname or original_nickname.isspace():
                original_nickname = игрок.name
            await игрок.edit(nick=original_nickname)
        except discord.Forbidden:
            pass  # Нет прав на изменение ника
        
        embed = discord.Embed(
            title="🔄 РЕГИСТРАЦИЯ СБРОШЕНА",
            description=f"Регистрация игрока {игрок.mention} была успешно отменена",
            color=0xff0000
        )
        embed.add_field(
            name="📊 Текущая статистика",
            value=f"```Зарегистрировано: {len(CONFIG['registered_players'])}/{CONFIG['max_players']}```",
            inline=False
        )
        embed.set_footer(text="Система регистрации • Ink Game")
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде reset: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при сбросе регистрации", ephemeral=True)

@bot.tree.command(name="list", description="Показать список зарегистрированных (только для админы)")
@app_commands.default_permissions(administrator=True)
async def list_cmd(interaction: discord.Interaction):
    """Список зарегистрированных"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if not CONFIG['registered_players']:
            embed = discord.Embed(
                title="📝 СПИСОК ИГРОКОВ",
                description="На данный момент нет зарегистрированных игроков",
                color=0xff0000
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
            await safe_edit_response(interaction, embed=embed)
            return
        
        embed = discord.Embed(
            title="📋 ЗАРЕГИСТРИРОВАННЫЕ ИГРОКИ",
            color=0xff0000
        )
        
        players_list = []
        for user_id in CONFIG['registered_players']:
            user = bot.get_user(user_id)
            player_number = CONFIG['player_numbers'].get(user_id, "???")
            if user:
                players_list.append(f"• {user.display_name} ({player_number})")
            else:
                # Если пользователь не найден в кэше, пробуем получить его
                try:
                    user = await bot.fetch_user(user_id)
                    players_list.append(f"• {user.display_name} ({player_number})")
                except:
                    players_list.append(f"• Unknown User ({user_id}) ({player_number})")
        
        # Разбиваем на части если список длинный
        if players_list:
            chunk_size = 15
            for i in range(0, len(players_list), chunk_size):
                chunk = players_list[i:i + chunk_size]
                embed.add_field(
                    name=f"🎯 Игроки {i+1}-{min(i+chunk_size, len(players_list))}",
                    value="\n".join(chunk),
                    inline=False
                )
        
        embed.add_field(
            name="📊 Общая статистика",
            value=f"```Всего игроков: {len(players_list)}/{CONFIG['max_players']}\nСтатус регистрации: {'🟢 ОТКРЫТА' if CONFIG['registration_open'] else '🔴 ЗАКРЫТА'}\nСтатус игры: {'🟢 АКТИВНА' if CONFIG['game_active'] else '🔴 ЗАВЕРШЕНА'}```",
            inline=False
        )
        embed.set_footer(text="Система регистрации • Ink Game")
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде list: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при показе списка игроков", ephemeral=True)

@bot.tree.command(name="save", description="Принудительно сохранить данные игры (админы)")
@app_commands.default_permissions(administrator=True)
async def save_cmd(interaction: discord.Interaction):
    """Принудительное сохранение данных"""
    try:
        await safe_defer_response(interaction, ephemeral=False)
        
        if await save_data_with_backup():
            embed = discord.Embed(
                title="💾 ДАННЫЕ СОХРАНЕНЫ",
                description="Все данные игры успешно сохранены",
                color=0x00ff00
            )
            embed.add_field(
                name="📊 Статистика",
                value=f"```Игроков: {len(CONFIG['registered_players'])}\nНомеров: {len(CONFIG['used_numbers'])}\nТитулов: {len(CONFIG['player_titles'])}```",
                inline=True
            )
            embed.add_field(
                name="👤 Сохранил",
                value=f"```{interaction.user.display_name}```",
                inline=True
            )
        else:
            embed = discord.Embed(
                title="❌ ОШИБКА СОХРАНЕНИЯ",
                description="Не удалось сохранить данные",
                color=0xff0000
            )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде save: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при сохранении данных", ephemeral=True)

@bot.tree.command(name="load", description="Принудительно загрузить данные игры (админы)")
@app_commands.default_permissions(administrator=True)
async def load_cmd(interaction: discord.Interaction):
    """Принудительная загрузка данных"""
    try:
        await safe_defer_response(interaction, ephemeral=True)
        
        if load_data():
            embed = discord.Embed(
                title="📂 ДАННЫЕ ЗАГРУЖЕНЫ",
                description="Данные игры успешно загружены",
                color=0x00ff00
            )
            embed.add_field(
                name="📊 Статистика",
                value=f"```Игроков: {len(CONFIG['registered_players'])}\nНомеров: {len(CONFIG['used_numbers'])}\nТитулов: {len(CONFIG['player_titles'])}```",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="❌ ОШИБКА ЗАГРУЗКИ",
                description="Не удалось загрузить данные",
                color=0xff0000
            )
        
        await safe_edit_response(interaction, embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде load: {e}")
        await safe_send_response(interaction, "❌ Произошла ошибка при загрузке данных", ephemeral=True)

# Обычная команда для синхронизации (на случай если команды не появляются)
@bot.command()
@commands.is_owner()
async def sync(ctx):
    """Синхронизировать команды (только для владельца бота)"""
    try:
        synced = await bot.tree.sync()
        embed = discord.Embed(
            title="✅ СИНХРОНИЗАЦИЯ УСПЕШНА",
            description=f"Загружено {len(synced)} команд",
            color=0xff0000
        )
        await ctx.send(embed=embed, ephemeral=True)
    except Exception as e:
        embed = discord.Embed(
            title="❌ ОШИБКА СИНХРОНИЗАЦИИ",
            description=f"Ошибка: {e}",
            color=0xff0000
        )
        await ctx.send(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    logger.info(f'✅ Бот {bot.user} запущен!')
    logger.info(f'🆔 ID бота: {bot.user.id}')
    
    # Загружаем данные из файла
    load_data()
    
    # Восстанавливаем игроков из ролей на всех серверах
    for guild in bot.guilds:
        logger.info(f"🔍 Проверка сервера: {guild.name}")
        await restore_players_from_roles(guild)
    
    logger.info(f'📊 Статус регистрации: {"Открыта" if CONFIG["registration_open"] else "Закрыта"}')
    logger.info(f'🎫 Свободных мест: {CONFIG["max_players"] - len(CONFIG["registered_players"])}')
    
    await asyncio.sleep(2)
    
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ Загружено {len(synced)} команд")
        for command in synced:
            logger.info(f" - {command.name}")
    except Exception as e:
        logger.error(f"❌ Ошибка синхронизации команд: {e}")

# ==================== RENDER FIX ====================
# Простой веб-сервер для Render (чтобы избежать ошибки портов)
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
# ==================== END RENDER FIX ====================

# Запуск бота
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)



