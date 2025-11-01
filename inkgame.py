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
    'max_players': 60,
    'min_number': 1,
    'max_number': 456,
    'registration_role_name': 'Зарегистрирован',
    'used_numbers': set(),
    'registered_players': set(),
    'player_numbers': {},
    'registration_open': False,
    'game_active': False
}

# Токены из переменных окружения
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
UNBELIEVABOAT_TOKEN = os.getenv('UNBELIEVABOAT_TOKEN')

# Проверка токенов при запуске
if not DISCORD_TOKEN:
    logger.error("❌ Ошибка: DISCORD_BOT_TOKEN не найден в .env файле")
    exit(1)

if not UNBELIEVABOAT_TOKEN:
    logger.error("❌ Ошибка: UNBELIEVABOAT_TOKEN не найден в .env файле")
    exit(1)

def save_data_with_backup():
    """Сохраняет данные и создает резервную копию"""
    if save_data():
        # Создаем резервную копию с timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backups/game_data_backup_{timestamp}.json"
        
        # Создаем папку backups если нет
        import os
        if not os.path.exists('backups'):
            os.makedirs('backups')
        
        # Копируем файл
        import shutil
        shutil.copy2('game_data.json', backup_filename)
        
        # Удаляем старые бэкапы (оставляем последние 5)
        backup_files = sorted([f for f in os.listdir('backups') if f.startswith('game_data_backup_')])
        if len(backup_files) > 5:
            for old_backup in backup_files[:-5]:
                os.remove(f"backups/{old_backup}")
        
        return True
    return False

# Функции для сохранения и загрузки данных
def save_data():
    """Сохраняет данные в файл"""
    data = {
        'used_numbers': list(CONFIG['used_numbers']),
        'registered_players': list(CONFIG['registered_players']),
        'player_numbers': {str(k): v for k, v in CONFIG['player_numbers'].items()},
        'registration_open': CONFIG['registration_open'],
        'game_active': CONFIG['game_active']
    }
    try:
        with open('game_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("✅ Данные сохранены")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения данных: {e}")
        return False

def load_data():
    """Загружает данные из файла"""
    try:
        with open('game_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        CONFIG['used_numbers'] = set(data['used_numbers'])
        CONFIG['registered_players'] = set(data['registered_players'])
        # Преобразуем строковые ключи обратно в целые числа
        CONFIG['player_numbers'] = {int(k): v for k, v in data['player_numbers'].items()}
        CONFIG['registration_open'] = data['registration_open']
        CONFIG['game_active'] = data['game_active']
        
        logger.info("✅ Данные загружены")
        logger.info(f"📊 Загружено игроков: {len(CONFIG['registered_players'])}")
        logger.info(f"🔢 Использовано номеров: {len(CONFIG['used_numbers'])}")
        return True
    except FileNotFoundError:
        logger.info("ℹ️ Файл данных не найден, начинаем с чистого листа")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки данных: {e}")
        return False

@bot.event
async def on_ready():
    logger.info(f'✅ Бот {bot.user} запущен!')
    logger.info(f'🆔 ID бота: {bot.user.id}')
    
    # Загружаем данные при запуске
    load_data()
    
    logger.info(f'📊 Статус регистрации: {"Открыта" if CONFIG["registration_open"] else "Закрыта"}')
    logger.info(f'🎫 Свободных мест: {CONFIG["max_players"] - len(CONFIG["registered_players"])}')
    
    # Синхронизация команд с задержкой
    await asyncio.sleep(2)
    
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ Загружено {len(synced)} команд")
        for command in synced:
            logger.info(f" - {command.name}")
    except Exception as e:
        logger.error(f"❌ Ошибка синхронизации команд: {e}")

def remove_number_from_nick(nickname: Optional[str]) -> str:
    """Удаляет номер из ника в формате (123)"""
    if nickname:
        return re.sub(r'\s*\(\d{3}\)\s*$', '', nickname).strip()
    return ""

def add_number_to_nick(nickname: Optional[str], number: str) -> str:
    """Добавляет номер к нику в формаte (123)"""
    clean_nick = remove_number_from_nick(nickname)
    new_nick = f"{clean_nick} ({number})"
    return new_nick[:32]  # Ограничение Discord

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

# Слеш-команда открытия регистрации (только для админов)
@bot.tree.command(name="start", description="Открыть регистрацию для всех игроков (только для админов)")
@app_commands.default_permissions(administrator=True)
async def start(interaction: discord.Interaction):
    """Открытие регистрации"""
    if not interaction.guild:
        await interaction.response.send_message("❌ Эта команда работает только на сервере", ephemeral=True)
        return
        
    if CONFIG['registration_open']:
        embed = discord.Embed(
            title="🚫 Ошибка",
            description="Регистрация уже открыта!",
            color=0xff0000
        )
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    CONFIG['registration_open'] = True
    CONFIG['game_active'] = True
    
    # Сохраняем изменения
    save_data()
    
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
    await interaction.response.send_message(embed=embed)

# Слеш-команда регистрации
@bot.tree.command(name="reg", description="Зарегистрироваться в игре")
async def reg(interaction: discord.Interaction):
    """Команда для регистрации игрока"""
    
    if not interaction.guild:
        await interaction.response.send_message("❌ Эта команда работает только на сервере", ephemeral=True)
        return
    
    # Проверка открыта ли регистрация
    if not CONFIG['registration_open']:
        embed = discord.Embed(
            title="🚫 Регистрация закрыта",
            description="Ожидайте открытия регистрации администратором",
            color=0xff0000
        )
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Проверка на лимит регистраций
    if len(CONFIG['registered_players']) >= CONFIG['max_players']:
        embed = discord.Embed(
            title="🎯 Все места заняты",
            description="Регистрация завершена, все 60 мест распределены",
            color=0xff0000
        )
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Проверка, не зарегистрирован ли уже игрок
    if interaction.user.id in CONFIG['registered_players']:
        embed = discord.Embed(
            title="⚠️ Уже зарегистрирован",
            description="Вы уже участвуете в событии",
            color=0xff0000
        )
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Генерация уникального номера
    if len(CONFIG['used_numbers']) >= (CONFIG['max_number'] - CONFIG['min_number'] + 1):
        embed = discord.Embed(
            title="❌ Ошибка системы",
            description="Все номера распределены",
            color=0xff0000
        )
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    while True:
        player_number = random.randint(CONFIG['min_number'], CONFIG['max_number'])
        if player_number not in CONFIG['used_numbers']:
            CONFIG['used_numbers'].add(player_number)
            break
    
    # Форматирование номера с ведущими нулями
    formatted_number = f"{player_number:03d}"
    
    # Добавление игрока в зарегистрированные
    CONFIG['registered_players'].add(interaction.user.id)
    CONFIG['player_numbers'][interaction.user.id] = formatted_number
    
    # Сохраняем изменения
    save_data()
    
    # Поиск роли
    registration_role = discord.utils.get(interaction.guild.roles, name=CONFIG['registration_role_name'])
    
    if not registration_role:
        # Создание роли, если она не существует
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
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    # Выдача роли игроку - приводим к Member для доступа к add_roles
    member = cast(discord.Member, interaction.user)
    try:
        await member.add_roles(registration_role)
    except discord.Forbidden:
        embed = discord.Embed(
            title="❌ Ошибка прав доступа",
            description="Не удалось выдать роль",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Изменение ника игрока
    try:
        new_nickname = add_number_to_nick(member.display_name, formatted_number)
        await member.edit(nick=new_nickname)
    except discord.Forbidden:
        pass  # Нет прав на изменение ника
    
    # Сообщение о регистрации
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
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Слеш-команда статуса

@bot.tree.command(name="help", description="Показать справку по командам")
async def help_cmd(interaction: discord.Interaction):
    """Показывает справку по командам"""
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
            "`/ping` - Проверить пинг"
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
                "`/load` - Загрузить данные"
            ),
            inline=False
        )
    
    embed.set_footer(text="Система регистрации • Ink Game")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ping", description="Проверить пинг бота")
async def ping(interaction: discord.Interaction):
    """Показывает задержку бота"""
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
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="freenumbers", description="Показать свободные номера (админы)")
@app_commands.default_permissions(administrator=True)
async def freenumbers(interaction: discord.Interaction):
    """Показывает свободные номера"""
    all_numbers = set(range(CONFIG['min_number'], CONFIG['max_number'] + 1))
    free_numbers = all_numbers - CONFIG['used_numbers']
    
    if not free_numbers:
        await interaction.response.send_message("❌ Свободных номеров нет", ephemeral=True)
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
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="changenumber", description="Изменить номер игрока (админы)")
@app_commands.default_permissions(administrator=True)
async def changenumber(interaction: discord.Interaction, игрок: discord.Member, новый_номер: int):
    """Изменяет номер игрока"""
    if игрок.id not in CONFIG['registered_players']:
        await interaction.response.send_message("❌ Игрок не зарегистрирован", ephemeral=True)
        return
    
    if новый_номер < CONFIG['min_number'] or новый_номер > CONFIG['max_number']:
        await interaction.response.send_message(
            f"❌ Номер должен быть от {CONFIG['min_number']} до {CONFIG['max_number']}", 
            ephemeral=True
        )
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
    
    save_data()
    
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
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="broadcast", description="Сделать объявление для всех игроков (админы)")
@app_commands.default_permissions(administrator=True)
async def broadcast(interaction: discord.Interaction, сообщение: str):
    """Отправляет сообщение всем зарегистрированным игрокам"""
    if not CONFIG['registered_players']:
        await interaction.response.send_message("❌ Нет игроков для рассылки", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📢 ОБЪЯВЛЕНИЕ",
        description=сообщение,
        color=0xff0000
    )
    embed.set_footer(text=f"От администратора • {interaction.user.display_name}")
    
    sent_count = 0
    error_count = 0
    
    # Отправляем сообщение о начале рассылки
    await interaction.response.send_message(
        f"📤 Начинаю рассылку для {len(CONFIG['registered_players'])} игроков...", 
        ephemeral=True
    )
    
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

@bot.tree.command(name="players", description="Показать список участников")
async def players(interaction: discord.Interaction):
    """Показывает количество участников"""
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
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mynumber", description="Показать ваш игровой номер")
async def mynumber(interaction: discord.Interaction):
    """Показывает номер игрока"""
    if interaction.user.id not in CONFIG['registered_players']:
        embed = discord.Embed(
            title="❌ Не зарегистрирован",
            description="Вы не зарегистрированы в игре",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
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
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="status", description="Проверить статус регистрации")
async def status(interaction: discord.Interaction):
    """Команда для проверки статуса регистрации"""
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
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Слеш-команда сброса (только для админов)

@bot.tree.command(name="restore", description="Восстановить данные из файла (админы)")
@app_commands.default_permissions(administrator=True)
async def restore(interaction: discord.Interaction):
    """Восстанавливает данные из файла"""
    # Эта команда требует загрузки файла через Discord
    await interaction.response.send_message(
        "📁 Отправьте файл `game_backup.json` в следующем сообщении", 
        ephemeral=True
    )
    
    def check(message):
        return (message.author == interaction.user and 
                message.channel == interaction.channel and
                message.attachments and
                message.attachments[0].filename.endswith('.json'))
    
    try:
        msg = await bot.wait_for('message', timeout=60.0, check=check)
        attachment = msg.attachments[0]
        
        # Скачиваем и сохраняем файл
        await attachment.save('game_data.json')
        
        # Перезагружаем данные
        if load_data():
            embed = discord.Embed(
                title="🔄 ДАННЫЕ ВОССТАНОВЛЕНЫ",
                description=f"Успешно восстановлено {len(CONFIG['registered_players'])} игроков",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ ОШИБКА ВОССТАНОВЛЕНИЯ",
                description="Не удалось загрузить данные из файла",
                color=0xff0000
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except asyncio.TimeoutError:
        await interaction.followup.send("❌ Время ожидания файла истекло", ephemeral=True)

@bot.tree.command(name="backup", description="Создать резервную копию данных (админы)")
@app_commands.default_permissions(administrator=True)
async def backup(interaction: discord.Interaction):
    """Создает резервную копию данных"""
    if save_data():
        # Создаем файл для отправки
        filename = f"backup_{interaction.id}.json"
        with open('game_data.json', 'r', encoding='utf-8') as f:
            backup_data = f.read()
        
        # Сохраняем временный файл
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(backup_data)
        
        file = discord.File(filename, filename="game_backup.json")
        
        embed = discord.Embed(
            title="💾 РЕЗЕРВНАЯ КОПИЯ СОЗДАНА",
            description=f"Сохранено {len(CONFIG['registered_players'])} игроков",
            color=0x00ff00
        )
        
        await interaction.response.send_message(embed=embed, file=file, ephemeral=True)
        
        # Удаляем временный файл
        import os
        os.remove(filename)
    else:
        await interaction.response.send_message("❌ Ошибка создания бэкапа", ephemeral=True)

@bot.tree.command(name="reset", description="Сбросить регистрацию конкретного игрока (только для админов)")
@app_commands.default_permissions(administrator=True)
async def reset(interaction: discord.Interaction, игрок: discord.Member):
    """Сброс регистрации конкретного игрока"""
    if not interaction.guild:
        await interaction.response.send_message("❌ Эта команда работает только на сервере", ephemeral=True)
        return
        
    if игрок.id not in CONFIG['registered_players']:
        embed = discord.Embed(
            title="❌ Ошибка",
            description=f"{игрок.mention} не зарегистрирован в системе",
            color=0xff0000
        )
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        await interaction.response.send_message(embed=embed, ephemeral=True)
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
    
    # Сохраняем изменения
    save_data()
    
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
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Слеш-команда завершения игры (только для админов)
@bot.tree.command(name="end", description="Закрыть регистрацию или завершить игру (только для админов)")
@app_commands.default_permissions(administrator=True)
async def end(interaction: discord.Interaction):
    """Закрытие регистрации или завершение игры"""
    
    if not interaction.guild:
        await interaction.response.send_message("❌ Эта команда работает только на сервере", ephemeral=True)
        return
    
    if not CONFIG['game_active']:
        embed = discord.Embed(
            title="🎮 ИГРА УЖЕ ЗАВЕРШЕНА",
            description="Событие уже было завершено ранее",
            color=0xff0000
        )
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if CONFIG['registration_open']:
        # Первое использование - закрываем регистрацию
        CONFIG['registration_open'] = False
        
        # Сохраняем изменения
        save_data()
        
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
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
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
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
        await interaction.response.send_message(embed=processing_embed, ephemeral=True)
        
        # Обрабатываем каждого игрока
        for user_id in list(CONFIG['registered_players']):
            try:
                member = await interaction.guild.fetch_member(user_id)
                
                # Начисляем деньги через UnbelievaBoat
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
        
        # Очищаем все данные
        total_players = len(CONFIG['registered_players'])
        CONFIG['used_numbers'].clear()
        CONFIG['registered_players'].clear()
        CONFIG['player_numbers'].clear()
        
        # Сохраняем изменения
        save_data()
        
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
        result_embed.add_field(
            name="🔄 Выполненные действия",
            value="• Регистрация закрыта\n• Игра завершена\n• Роли удалены\n• Ники восстановлены\n• Данные очищены\n• Деньги начислены",
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
        
        result_embed.set_footer(text="Система регистрации • Ink Game")
        result_embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        
        # Редактируем первоначальное сообщение
        await interaction.edit_original_response(embed=result_embed)

# Слеш-команда списка (только для админов)
@bot.tree.command(name="list", description="Показать список зарегистрированных (только для админов)")
@app_commands.default_permissions(administrator=True)
async def list_cmd(interaction: discord.Interaction):
    """Список зарегистрированных"""
    if not CONFIG['registered_players']:
        embed = discord.Embed(
            title="📝 СПИСОК ИГРОКОВ",
            description="На данный момент нет зарегистрированных игроков",
            color=0xff0000
        )
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1420114175895666759/1433470801197404160/download-Photoroom.png?ex=6904cf37&is=69037db7&hm=e1efd6926b779844a323f067c700d584a49945758839a19b4c6e8c0a34f2b44e&=&format=webp&quality=lossless")
        await interaction.response.send_message(embed=embed, ephemeral=True)
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
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Слеш-команда для сохранения данных (админы)
@bot.tree.command(name="save", description="Принудительно сохранить данные игры (админы)")
@app_commands.default_permissions(administrator=True)
async def save_cmd(interaction: discord.Interaction):
    """Принудительное сохранение данных"""
    if save_data():
        embed = discord.Embed(
            title="💾 ДАННЫЕ СОХРАНЕНЫ",
            description="Все данные игры успешно сохранены",
            color=0x00ff00
        )
        embed.add_field(
            name="📊 Статистика",
            value=f"```Игроков: {len(CONFIG['registered_players'])}\nНомеров: {len(CONFIG['used_numbers'])}```",
            inline=False
        )
    else:
        embed = discord.Embed(
            title="❌ ОШИБКА СОХРАНЕНИЯ",
            description="Не удалось сохранить данные",
            color=0xff0000
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Слеш-команда для загрузки данных (админы)
@bot.tree.command(name="load", description="Принудительно загрузить данные игры (админы)")
@app_commands.default_permissions(administrator=True)
async def load_cmd(interaction: discord.Interaction):
    """Принудительная загрузка данных"""
    if load_data():
        embed = discord.Embed(
            title="📂 ДАННЫЕ ЗАГРУЖЕНЫ",
            description="Данные игры успешно загружены",
            color=0x00ff00
        )
        embed.add_field(
            name="📊 Статистика",
            value=f"```Игроков: {len(CONFIG['registered_players'])}\nНомеров: {len(CONFIG['used_numbers'])}```",
            inline=False
        )
    else:
        embed = discord.Embed(
            title="❌ ОШИБКА ЗАГРУЗКИ",
            description="Не удалось загрузить данные",
            color=0xff0000
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

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


