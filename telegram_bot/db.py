import asyncio
from datetime import datetime
import re
import string
import json
import random
import time
from uuid import uuid4

import aiosqlite

from telegram_bot.env import bot

def generate_promocode():
    return "DL" + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))

async def get_users(user_id: int = None, promocode: str = None, level: int = None, multiple: bool = True):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.cursor()
        
        conditions = []

        if user_id:
            multiple = False
            conditions.append(f"user_id = {user_id}")
        if promocode:
            multiple = False
            conditions.append(f"promocode = '{promocode}'")
        if level:
            conditions.append(f"level = {level}")

        query = "SELECT * FROM users"
        if conditions:
            query += " WHERE " + " OR ".join(conditions)

        await cursor.execute(query)

        if multiple:
            return await cursor.fetchall()
        return await cursor.fetchone()

async def get_partners(partner_id: int = None, category_id: int = None, owner_id: int = None):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row
        
        cursor = await conn.cursor()
        conditions = []
        
        query = "SELECT * FROM partners"
        
        if category_id is not None:
            conditions.append(f"partner_category = {category_id}")

        if partner_id is not None:
            conditions.append(f"partner_id = {partner_id}")

        if owner_id is not None:
            conditions.append(f"owner_user_id = {owner_id}")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        await cursor.execute(query)
        
        if partner_id is not None:
            try:
                data = dict(await cursor.fetchone())
            except TypeError:
                return None
            category = await get_categories(data["partner_category"])
            user = await get_users(data["owner_user_id"], multiple=False)
            data["category"] = category
            data["owner"] = user
            return data
        return await cursor.fetchall()

async def get_categories(category_id: int = None, category_enabled: bool = None):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row
        
        cursor = await conn.cursor()
        
        conditions = []
        if category_id:
            conditions.append(f"category_id == {category_id}")
        if category_enabled is not None:
            conditions.append(f"category_enabled == {1 if category_enabled else 0}")
        condition = " AND ".join(conditions)
        await cursor.execute(f"SELECT * FROM categories" + (f" WHERE " + condition if condition else ""))
        
        if category_id:
            return await cursor.fetchone()
        return await cursor.fetchall()

async def get_subscriptions(user_id: int = None, partner_id: int = None, start_ts: int | float = 0, end_ts: int | float = 16**16):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row
        
        cursor = await conn.cursor()
        
        conditions = []
        if end_ts:
            conditions.append(f"end_date < {end_ts}")
        if user_id:
            conditions.append(f"user_id == {user_id}")
        elif partner_id:
            conditions.append(f"partner_id == {partner_id}")
        if conditions:
            conditions.append(" ")
            
        condition = " WHERE " + " AND ".join(conditions) + f"start_date >= {start_ts} AND end_date <= {end_ts}"
        
        await cursor.execute(f"SELECT * FROM subscriptions" + condition)

        return await cursor.fetchall() or None

async def get_redeemed_promo(promocode: str = None, restart_old_ones: bool = False):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.cursor()
        
        conditions = []
        if promocode is not None:
            conditions.append(f"promocode == '{promocode}'")
            
        condition = " AND ".join(conditions)
        
        if restart_old_ones:
            olds = await cursor.execute(f"SELECT * FROM redeemed_promocodes WHERE (redeem_date + (31 * 86400)) < {time.time()}")
            olds = await olds.fetchall()
            for old in olds:
                partner = await get_partners(old["partner_id"])
                if not partner:
                    return ()
                await cursor.execute(f"DELETE FROM redeemed_promocodes WHERE partner_id == {partner["partner_id"]} AND promocode = '{old["promocode"]}'")
                await conn.commit()
                await bot.send_message(old["user_id"], f"🔋 <b>Теперь вы снова можете использовать промокод у партнёра <code>{partner["partner_name"]}</code>!</b>", parse_mode="html")
        
        else:
            await cursor.execute("SELECT * FROM redeemed_promocodes" + (f" WHERE " + condition if condition else ""))
            return await cursor.fetchall()

async def redeem_promo(user_id: int, promocode: str, partner_id: int):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.cursor()
        
        await cursor.execute(f"INSERT INTO redeemed_promocodes (user_id, promocode, partner_id, redeem_date) VALUES (?, ?, ?, ?)", (user_id, promocode, partner_id, time.time()))
        await conn.commit()

async def add_user(user_id: int, username: str, name: str, last_name: str | None):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row
        
        cursor = await conn.cursor()
        
        await cursor.execute(
            f"INSERT INTO users (user_id, username, full_name, promocode) VALUES (?, ?, ?, ?)", 
            (user_id, username, (name + " " + (last_name or "")).rstrip(" "), generate_promocode(),)
        )
        await cursor.execute(
            f"INSERT INTO user_profile (user_id) VALUES (?)",
            (user_id,)
        )
        await conn.commit()

async def add_partner(user_id: int, partner_name: int, partner_category: int):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row
        
        cursor = await conn.cursor()
        
        await cursor.execute(
            f"INSERT INTO partners (owner_user_id, partner_name, partner_category) VALUES (?, ?, ?)", 
            (user_id, partner_name, partner_category,)
        )
        await conn.commit()

async def add_category(name: str):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row
        
        cursor = await conn.cursor()
        
        await cursor.execute(f"INSERT INTO categories (category_name) VALUES (?)", (name))
        await conn.commit()

async def add_subscription(user_id: int, price: int, length: int, partner_id: int | None = None):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.cursor()
        
        start_ts = time.time()
        end_ts = start_ts + 86400 * length
        uuid = str(uuid4())
        
        await cursor.execute(f"INSERT INTO subscriptions VALUES(?, ?, ?, ?, ?, ?)", (user_id, start_ts, end_ts, price, partner_id, uuid,))
        await conn.commit()

async def get_user_profile(user_id: int):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row

        cursor = await conn.cursor()

        await cursor.execute(f"SELECT full_name, birth_date, phone_number FROM user_profile WHERE user_id = {user_id}")
        data = await cursor.fetchone()
        
        if data:
            data = dict(data)
            
        if data:
            data = dict(data)
            data["pets"] = await get_pets(user_id)

        return data

async def get_pets(user_id: int = None, pet_id: int = None):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row
        
        cursor = await conn.cursor()
        condition = ""
        
        if user_id:
            condition = f"user_id == {user_id}"
        elif pet_id:
            condition = f"pet_id == {pet_id}"
            
        await cursor.execute(f"SELECT * FROM pets{" WHERE " + condition if condition else ""}")
        
        if pet_id:
            return await cursor.fetchone()
        else:
            return await cursor.fetchall()
    
async def add_pet(user_id: int, approx_weight: int | float, name: str, birth_date: int | float, gender: str, pet_type: str, pet_breed: str):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row

        cursor = await conn.cursor()

        gender = 1 if gender == "male" else 0

        await cursor.execute("INSERT INTO pets (user_id, approx_weight, name, birth_date, gender, type, breed) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, approx_weight, name, birth_date, gender, pet_type, pet_breed,))
        await conn.commit()
        
async def update_user_profile(user_id: int, **kwargs):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row
        
        cursor = await conn.cursor()
        
        updations = ", ".join([f"{key} = {f'"{value}"' if isinstance(value, str) else value}" for key, value in kwargs.items()])
        
        await cursor.execute(f"UPDATE user_profile SET {updations} WHERE user_id == {user_id}")
        await conn.commit()

async def update_user(user_id: int, **kwargs):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.cursor()
        
        updations = ", ".join([f"{key} = {f'"{value}"' if isinstance(value, str) else value}" for key, value in kwargs.items()])
        
        await cursor.execute(f"UPDATE users SET {updations} WHERE user_id == {user_id}")
        await conn.commit()

async def update_partner(partner_id: int, **kwargs):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        conn.row_factory = aiosqlite.Row
        
        cursor = await conn.cursor()
        
        updations = ", ".join([f"{key} = {f'"{value}"' if isinstance(value, str) else value}" for key, value in kwargs.items()])
        
        await cursor.execute(f"UPDATE partners SET {updations} WHERE partner_id == {partner_id}")
        await conn.commit()

async def checker_cycle():
    while True:
        subscriptions = await get_subscriptions(end_ts=time.time())
        if subscriptions:
            for subscription in subscriptions:
                await bot.send_message(subscription["user_id"], "🪫 <b>Ваша подписка закончилась!</b>", parse_mode="html")
                await remove_subscription(subscription["user_id"])
                await asyncio.sleep(0.03)

        await get_redeemed_promo(restart_old_ones=True)
        await asyncio.sleep(1)

async def validate_user_form_data(web_app_data: str, user_id: int):
    if not web_app_data or (await get_users(user_id))["level"] < 0:
        return False
    
    def validate_full_name(full_name):
        pattern = r'^([А-Я][а-я]{1,15}\s){2}[А-Я][а-я]{1,15}$'
        return re.match(pattern, full_name) is not None

    def validate_phone_number(phone_number):
        pattern = r'^\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}$'
        return re.match(pattern, phone_number) is not None

    def validate_birth_date(birth_date):
        try:
            date_obj = datetime.strptime(birth_date, '%Y-%m-%d')
            return date_obj < datetime.now()
        except ValueError:
            return False

    def validate_breed(breed):
        return bool(re.match(r'^[^\d]+$', breed))

    def validate_pet(pet):
        if not isinstance(pet['name'], str) or not pet['name']:
            return False
        if not isinstance(pet['weight'], (int, float)) or not (0 <= pet['weight'] <= 100):
            return False
        if not validate_birth_date(pet['birth_date']):
            return False
        if pet['gender'] not in ['male', 'female']:
            return False
        if pet['type'] not in ['dog', 'cat']:
            return False
        if not validate_breed(pet['breed']):
            return False
        return True

    try:
        data = json.loads(web_app_data)
    except json.JSONDecodeError:
        return False

    human = data.get('human', {})
    if not validate_full_name(human.get('full_name', '')):
        return False
    if not validate_phone_number(human.get('phone_number', '')):
        return False
    if not validate_birth_date(human.get('birth_date', '')):
        return False

    pets = data.get('pets', [])
    if not pets or len(pets) < 1:
        return False

    for pet in pets:
        if not validate_pet(pet):
            return False

    return data

async def remove_subscription(user_id: int):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        cursor = await conn.cursor()
        await cursor.execute(f"DELETE FROM subscriptions WHERE rowid = (SELECT rowid FROM subscriptions WHERE user_id = {user_id} ORDER BY start_date DESC LIMIT 1)")
        await conn.commit()

async def delete_partner(partner_id: int):
    async with aiosqlite.connect("database.db", check_same_thread=False) as conn:
        cursor = await conn.cursor()
        await cursor.execute(f"DELETE FROM partners WHERE partner_id = {partner_id}")
        await conn.commit()
