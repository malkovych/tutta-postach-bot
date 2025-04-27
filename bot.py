#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Імпортуємо модуль для роботи з MySQL
import db_mysql as db

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота Telegram (замініть на свій)
import os
TOKEN = os.environ.get("BOT_TOKEN", "7973829035:AAHylWqTFczrGNkqhpOQcGUK1BqjhV3ogeM")

# Додаткові стани для реєстрації
(
    MAIN_MENU, SELECTING_ORDER_TYPE, SELECTING_CATEGORY, 
    SELECTING_PRODUCT, VIEWING_ORDER, CONFIRMING_ORDER,
    REGISTRATION_ROLE, SUPPLIER_CATEGORIES, SUPPLIER_PHONE
) = range(9)

# Початок роботи з ботом та реєстрація
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    user_id = str(user.id)
    
    # Перевіряємо, чи користувач вже зареєстрований
    user_data = db.get_user(user_id)
    
    if user_data:
        return await show_main_menu(update, context)
    else:
        # Пропонуємо обрати роль
        keyboard = [
            [InlineKeyboardButton("👨‍🍳 Tutta Team (працівник кухні)", callback_data="role_kitchen")],
            [InlineKeyboardButton("🚚 Постачальник", callback_data="role_supplier")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Вітаю, {user.first_name}! Для початку роботи оберіть вашу роль:",
            reply_markup=reply_markup
        )
        
        return REGISTRATION_ROLE

# Обробка вибору ролі
async def register_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = str(user.id)
    data = query.data
    
    role = "kitchen" if data == "role_kitchen" else "supplier"
    
    # Створюємо нового користувача
    db.create_user(user_id, user.first_name, user.username, role)
    
    if role == "supplier":
        # Для постачальника пропонуємо обрати категорії
        await query.edit_message_text(
            f"Ви зареєстровані як постачальник!\n\n"
            f"Тепер оберіть категорії продуктів, які ви постачаєте:"
        )
        return await show_supplier_categories(update, context)
    else:
        # Для працівника кухні показуємо головне меню
        db.update_user(user_id, {"is_registered": True})
        
        await query.edit_message_text(
            f"Ви успішно зареєстровані як працівник кухні (Tutta Team)!\n\n"
            f"Тепер ви можете створювати замовлення на продукти."
        )
        
        # Відправляємо нове повідомлення з меню
        return await show_main_menu(update, context, new_message=True)

# Показ категорій для постачальника
async def show_supplier_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = str(query.from_user.id)
    
    # Перевірка наявності даних користувача
    user_data = db.get_user(user_id)
    if not user_data:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Помилка: користувач не знайдений. Почніть знову з /start"
        )
        return ConversationHandler.END
    
    # Отримуємо всі категорії
    categories = db.get_categories()
    if not categories:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Помилка: не вдалося отримати категорії. Спробуйте пізніше."
        )
        return ConversationHandler.END
    
    # Отримуємо обрані категорії постачальника
    supplier_id = f"supplier_{user_id}"
    selected_categories = db.get_supplier_categories(supplier_id)
    
    keyboard = []
    
    # Створюємо кнопки для кожної категорії
    for category in categories.keys():
        # Визначаємо, чи обрана категорія
        is_selected = category in selected_categories
        button_text = f"✅ {category}" if is_selected else f"⬜ {category}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"supplier_cat_{category}")])
    
    # Додаємо кнопку для завершення вибору
    keyboard.append([InlineKeyboardButton("✅ Завершити вибір", callback_data="supplier_categories_done")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="Оберіть категорії продуктів, які ви постачаєте (можна обрати декілька):",
        reply_markup=reply_markup
    )
    
    return SUPPLIER_CATEGORIES

# Обробка вибору категорій постачальником
async def process_supplier_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = query.data
    supplier_id = f"supplier_{user_id}"
    
    if data == "supplier_categories_done":
        # Завершення вибору категорій
        selected_categories = db.get_supplier_categories(supplier_id)
        
        if not selected_categories:
            # Якщо не обрано жодної категорії
            await query.edit_message_text(
                "Ви не обрали жодної категорії. Будь ласка, оберіть хоча б одну категорію продуктів."
            )
            return await show_supplier_categories(update, context)
        
        # Запитуємо номер телефону
        keyboard = [
            [KeyboardButton("📱 Поділитися номером телефону", request_contact=True)]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await query.edit_message_text(
            "Чудово! Тепер, будь ласка, надайте ваш номер телефону для зв'язку."
        )
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Ви можете натиснути кнопку нижче або просто надіслати свій номер у форматі +380XXXXXXXX:",
            reply_markup=reply_markup
        )
        
        return SUPPLIER_PHONE
    
    else:
        # Обробка вибору категорії
        category = data.replace("supplier_cat_", "")
        category_id = db.get_category_id_by_name(category)
        
        if not category_id:
            await query.edit_message_text(
                f"Помилка: категорія '{category}' не знайдена."
            )
            return await show_supplier_categories(update, context)
        
        # Перевіряємо, чи вже обрана категорія
        selected_categories = db.get_supplier_categories(supplier_id)
        
        if category in selected_categories:
            # Видаляємо категорію
            db.remove_supplier_category(supplier_id, category_id)
        else:
            # Додаємо категорію
            db.add_supplier_category(supplier_id, category_id)
        
        # Оновлюємо повідомлення з категоріями
        return await show_supplier_categories(update, context)

# Обробка номера телефону постачальника
async def process_supplier_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    
    # Отримуємо номер телефону
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()
    
    # Зберігаємо номер телефону
    db.update_user(user_id, {"phone": phone, "is_registered": True})
    
    # Додаємо користувача до списку постачальників
    supplier_id = f"supplier_{user_id}"
    user_data = db.get_user(user_id)
    
    # Створюємо постачальника
    db.create_supplier(supplier_id, user_id, user_data["name"], phone)
    
    # Отримуємо обрані категорії
    selected_categories = db.get_supplier_categories(supplier_id)
    
    # Повідомляємо про успішну реєстрацію
    await update.message.reply_text(
        f"Дякуємо! Ви успішно зареєстровані як постачальник.\n\n"
        f"Ви будете отримувати замовлення для категорій:\n"
        f"{', '.join(selected_categories)}\n\n"
        f"Ваш контактний номер: {phone}",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Показуємо меню постачальника
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Головне меню постачальника:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Активні замовлення", callback_data="supplier_active_orders")],
            [InlineKeyboardButton("⚙️ Налаштування", callback_data="supplier_settings")]
        ])
    )
    
    return MAIN_MENU

# Показ головного меню
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, new_message=False) -> int:
    user_id = str(update.effective_user.id)
    
    # Перевіряємо, чи зареєстрований користувач
    user_data = db.get_user(user_id)
    
    if not user_data or not user_data.get("is_registered", False):
        if hasattr(update, "message"):
            await update.message.reply_text(
                "Ви не зареєстровані. Будь ласка, почніть з команди /start"
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Ви не зареєстровані. Будь ласка, почніть з команди /start"
            )
        return ConversationHandler.END
    
    # Визначаємо роль користувача
    user_role = user_data.get("role", "kitchen")
    
    if user_role == "kitchen":
        # Меню для працівника кухні
        keyboard = [
            [InlineKeyboardButton("🗓 Планове (тижневе)", callback_data="new_order_planned")],
            [InlineKeyboardButton("⚡ Термінове", callback_data="new_order_urgent")],
            [InlineKeyboardButton("📋 Мої замовлення", callback_data="my_orders")]
        ]
        
        message_text = "Головне меню:\n\nОберіть тип замовлення:"
    else:
        # Меню для постачальника
        keyboard = [
            [InlineKeyboardButton("📋 Активні замовлення", callback_data="supplier_active_orders")],
            [InlineKeyboardButton("⚙️ Налаштування", callback_data="supplier_settings")]
        ]
        
        message_text = "Головне меню постачальника:"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if new_message:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message_text,
            reply_markup=reply_markup
        )
    else:
        if hasattr(update, "callback_query"):
            await update.callback_query.edit_message_text(
                text=message_text,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=message_text,
                reply_markup=reply_markup
            )
    
    return MAIN_MENU

# Обробка вибору типу замовлення
async def new_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = query.data
    
    if data == "new_order_planned" or data == "new_order_urgent":
        order_type = "planned" if data == "new_order_planned" else "urgent"
        
        # Отримати дані користувача
        user_data = db.get_user(user_id)
        
        # Створення нового замовлення
        order_id = f"{datetime.now().timestamp()}"
        db.create_order(order_id, order_type, user_id, user_data["name"])
        
        # Оновлюємо поточне замовлення користувача
        db.update_user(user_id, {"current_order": order_id})
        
        return await show_categories(update, context)
    
    elif data == "my_orders":
        return await view_my_orders(update, context)
    
    # Обробка меню постачальника
    elif data == "supplier_active_orders":
        return await show_supplier_orders(update, context)
    
    elif data == "supplier_settings":
        return await show_supplier_settings(update, context)
    
    return MAIN_MENU

# Показ активних замовлень для постачальника
async def show_supplier_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    # Перевіряємо, чи користувач є постачальником
    user_data = db.get_user(user_id)
    if not user_data or user_data.get("role") != "supplier":
        await query.edit_message_text(
            "У вас немає доступу до цього розділу."
        )
        return MAIN_MENU
    
    # Отримуємо замовлення для постачальника
    relevant_orders = db.get_relevant_orders_for_supplier(user_id)
    
    if not relevant_orders:
        await query.edit_message_text(
            "Наразі для вас немає активних замовлень.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 На головну", callback_data="home")]])
        )
        return MAIN_MENU
    
    # Відображаємо замовлення
    message = "*📋 Активні замовлення для вас:*\n\n"
    
    for idx, order in enumerate(relevant_orders[:5]):  # Обмежуємо кількість відображених замовлень
        message += f"*Замовлення #{idx+1}*\n"
        message += f"Тип: {'🗓 Планове' if order['type'] == 'planned' else '⚡ Термінове'}\n"
        
        order_date = datetime.fromisoformat(order["date"])
        message += f"Дата: {order_date.strftime('%d.%m.%Y %H:%M')}\n"
        
        message += f"Статус: {get_status_text(order['status'])}\n"
        message += f"Від: {order['user_name']}\n\n"
        
        message += "*Продукти для вас:*\n"
        
        # Відображаємо тільки категорії, які стосуються постачальника
        for category, products in order["items"].items():
            message += f"*{category}:*\n"
            for item in products:
                message += f"- {item}\n"
            message += "\n"
        
        message += "------------\n\n"
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 На головну", callback_data="home")]]),
        parse_mode="Markdown"
    )
    
    return MAIN_MENU

# Показ налаштувань постачальника
async def show_supplier_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    # Перевіряємо, чи користувач є постачальником
    user_data = db.get_user(user_id)
    if not user_data or user_data.get("role") != "supplier":
        await query.edit_message_text(
            "У вас немає доступу до цього розділу."
        )
        return MAIN_MENU
    
    # Отримуємо категорії постачальника
    supplier_id = f"supplier_{user_id}"
    categories = db.get_supplier_categories(supplier_id)
    
    message = "*⚙️ Налаштування постачальника*\n\n"
    message += f"Ім'я: {user_data.get('name')}\n"
    message += f"Телефон: {user_data.get('phone')}\n"
    message += f"Категорії: {', '.join(categories)}\n"
    
    keyboard = [
        [InlineKeyboardButton("📋 Змінити категорії", callback_data="change_categories")],
        [InlineKeyboardButton("📱 Змінити телефон", callback_data="change_phone")],
        [InlineKeyboardButton("🏠 На головну", callback_data="home")]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    
    return MAIN_MENU

# Показ категорій продуктів
async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        chat_id = query.message.chat_id
    else:
        chat_id = update.effective_chat.id
    
    # Отримуємо категорії
    categories = db.get_categories()
    
    keyboard = []
    
    # Створення кнопок для кожної категорії
    for category in categories.keys():
        keyboard.append([InlineKeyboardButton(category, callback_data=f"category_{category}")])
    
    keyboard.append([InlineKeyboardButton("📝 Переглянути поточне замовлення", callback_data="view_current_order")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(
            text="Оберіть категорію продуктів:",
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Оберіть категорію продуктів:",
            reply_markup=reply_markup
        )
    
    return SELECTING_CATEGORY

# Показ продуктів у категорії
async def show_products_in_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    category = query.data.replace("category_", "")
    context.user_data["current_category"] = category
    
    # Отримуємо продукти категорії
    categories = db.get_categories()
    products = categories.get(category, [])
    
    keyboard = []
    
    # Створення кнопок для кожного продукту
    for idx, product in enumerate(products):
        keyboard.append([InlineKeyboardButton(product, callback_data=f"add_{idx}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад до категорій", callback_data="back_to_categories")])
    keyboard.append([InlineKeyboardButton("📝 Переглянути поточне замовлення", callback_data="view_current_order")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"Оберіть продукти з категорії \"{category}\":",
        reply_markup=reply_markup
    )
    
    return SELECTING_PRODUCT

# Додавання продукту до замовлення
async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    product_idx = int(query.data.replace("add_", ""))
    category = context.user_data.get("current_category")
    
    if not category:
        await query.edit_message_text(
            "Помилка: категорія не вибрана. Спробуйте заново.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 На головну", callback_data="home")]])
        )
        return MAIN_MENU
    
    # Отримуємо поточне замовлення користувача
    user_data = db.get_user(user_id)
    order_id = user_data.get("current_order")
    
    if not order_id:
        await query.edit_message_text(
            "Помилка: Немає активного замовлення. Створіть нове замовлення.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 На головну", callback_data="home")]])
        )
        return MAIN_MENU
    
    # Отримуємо продукт за індексом
    categories = db.get_categories()
    products = categories.get(category, [])
    
    if product_idx >= len(products):
        await query.edit_message_text(
            "Помилка: Продукт не знайдено.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 На головну", callback_data="home")]])
        )
        return MAIN_MENU
    
    product = products[product_idx]
    
    # Перевіряємо замовлення
    order = db.get_order(order_id)
    if not order:
        await query.edit_message_text(
            "Помилка: Замовлення не знайдено.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 На головну", callback_data="home")]])
        )
        return MAIN_MENU
    
    # Перевіряємо, чи вже є такий продукт у замовленні
    is_product_in_order = False
    if category in order["items"] and product in order["items"][category]:
        is_product_in_order = True
    
    if not is_product_in_order:
        # Додаємо продукт до замовлення
        db.add_order_item(order_id, category, product)
        
        keyboard = [
            [InlineKeyboardButton("➕ Додати ще з цієї категорії", callback_data=f"category_{category}")],
            [InlineKeyboardButton("📋 Обрати іншу категорію", callback_data="back_to_categories")],
            [InlineKeyboardButton("📝 Переглянути поточне замовлення", callback_data="view_current_order")]
        ]
        
        await query.edit_message_text(
            f"✅ Додано \"{product}\" до замовлення.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        keyboard = [
            [InlineKeyboardButton("➕ Додати інший товар з цієї категорії", callback_data=f"category_{category}")],
            [InlineKeyboardButton("📋 Обрати іншу категорію", callback_data="back_to_categories")],
            [InlineKeyboardButton("📝 Переглянути поточне замовлення", callback_data="view_current_order")]
        ]
        
        await query.edit_message_text(
            f"❗ \"{product}\" вже є у вашому замовленні.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return SELECTING_CATEGORY

# Повернення назад до категорій
async def back_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    return await show_categories(update, context)

# Перегляд поточного замовлення
async def view_current_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    # Отримуємо поточне замовлення користувача
    user_data = db.get_user(user_id)
    order_id = user_data.get("current_order")
    
    if not order_id:
        await query.edit_message_text(
            "У вас немає активного замовлення. Створіть нове через головне меню.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 На головну", callback_data="home")]])
        )
        return MAIN_MENU
    
    # Отримуємо замовлення
    order = db.get_order(order_id)
    if not order:
        await query.edit_message_text(
            "Помилка: Замовлення не знайдено.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 На головну", callback_data="home")]])
        )
        return MAIN_MENU
    
    message = f"📋 *Ваше поточне замовлення*\n"
    message += f"Тип: {'🗓 Планове' if order['type'] == 'planned' else '⚡ Термінове'}\n"
    message += f"Статус: {get_status_emoji(order['status'])} {get_status_text(order['status'])}\n\n"
    
    has_items = False
    for category, products in order["items"].items():
        if products:
            has_items = True
            message += f"*{category}*:\n"
            
            for idx, item in enumerate(products):
                message += f"{idx + 1}. {item} (/remove_{category}_{idx})\n"
            
            message += "\n"
    
    if not has_items:
        message += "Замовлення порожнє. Додайте продукти з категорій.\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Додати ще продуктів", callback_data="back_to_categories")]
    ]
    
    # Додаємо кнопку підтвердження лише для чернеток
    if order["status"] == "draft" and has_items:
        keyboard.append([InlineKeyboardButton("✅ Підтвердити замовлення", callback_data="confirm_order")])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    
    return VIEWING_ORDER

# Видалення продукту з замовлення
async def remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = update.message.text
    user_id = str(update.effective_user.id)
    
    # Парсимо команду /remove_category_idx
    parts = message_text.split('_')
    if len(parts) != 3:
        await update.message.reply_text("Неправильний формат команди видалення.")
        return
    
    category = parts[1]
    try:
        product_idx = int(parts[2])
    except ValueError:
        await update.message.reply_text("Неправильний індекс продукту.")
        return
    
    # Отримуємо поточне замовлення користувача
    user_data = db.get_user(user_id)
    order_id = user_data.get("current_order")
    
    if not order_id:
        await update.message.reply_text("Помилка: Немає активного замовлення.")
        return
    
    # Видаляємо продукт із замовлення
    removed_item = db.remove_order_item(order_id, category, product_idx)
    
   if removed_item:
        keyboard = [
            [InlineKeyboardButton("📝 Переглянути оновлене замовлення", callback_data="view_current_order")],
            [InlineKeyboardButton("➕ Додати інші продукти", callback_data="back_to_categories")]
        ]
        
        await update.message.reply_text(
            f"❌ Видалено \"{removed_item}\" з замовлення.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("Помилка: Продукт не знайдено у замовленні.")

# Підтвердження замовлення
async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    # Отримуємо поточне замовлення користувача
    user_data = db.get_user(user_id)
    order_id = user_data.get("current_order")
    
    if not order_id:
        await query.edit_message_text(
            "Помилка: Немає активного замовлення.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 На головну", callback_data="home")]])
        )
        return MAIN_MENU
    
    # Отримуємо замовлення
    order = db.get_order(order_id)
    if not order:
        await query.edit_message_text(
            "Помилка: Замовлення не знайдено.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 На головну", callback_data="home")]])
        )
        return MAIN_MENU
    
    # Перевіряємо, чи не порожнє замовлення
    has_items = any(products for products in order["items"].values())
    
    if not has_items:
        await query.edit_message_text(
            "Неможливо підтвердити порожнє замовлення. Додайте хоча б один продукт.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Додати продукти", callback_data="back_to_categories")]])
        )
        return SELECTING_CATEGORY
    
    # Змінюємо статус замовлення
    db.update_order_status(order_id, "confirmed")
    
    # Видаляємо прив'язку до поточного замовлення користувача
    db.update_user(user_id, {"current_order": None})
    
    # Отримуємо всіх постачальників
    suppliers = []
    for supplier_id, supplier_data in db.get_suppliers():
        supplier_categories = db.get_supplier_categories(supplier_id)
        
        # Перевіряємо, чи постачальник постачає будь-яку з категорій у замовленні
        relevant_categories = [cat for cat in supplier_categories if cat in order["items"]]
        
        if relevant_categories:
            suppliers.append({
                "user_id": supplier_data["user_id"],
                "name": supplier_data["name"],
                "categories": relevant_categories
            })
    
    # Надсилаємо повідомлення кожному постачальнику, який постачає категорії з замовлення
    for supplier in suppliers:
        # Формуємо повідомлення для постачальника
        supplier_message = f"📋 *НОВЕ ЗАМОВЛЕННЯ*\n"
        supplier_message += f"Тип: {'🗓 Планове' if order['type'] == 'planned' else '⚡ Термінове'}\n"
        supplier_message += f"ID: {order['id']}\n"
        supplier_message += f"Від: {order['user_name']}\n"
        supplier_message += f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        
        supplier_message += "*Продукти для постачання:*\n"
        
        for category in supplier["categories"]:
            if category in order["items"] and order["items"][category]:
                supplier_message += f"*{category}:*\n"
                for item in order["items"][category]:
                    supplier_message += f"- {item}\n"
                supplier_message += "\n"
        
        # Надсилаємо повідомлення постачальнику
        try:
            await context.bot.send_message(
                chat_id=supplier["user_id"],
                text=supplier_message,
                parse_mode="Markdown"
            )
            
            logger.info(f"Надіслано повідомлення постачальнику {supplier['name']} (ID: {supplier['user_id']})")
        except Exception as e:
            logger.error(f"Помилка при надсиланні повідомлення постачальнику {supplier['name']}: {e}")
    
    await query.edit_message_text(
        "✅ Ваше замовлення успішно підтверджено та надіслано постачальникам!\n\n"
        "Ви можете створити нове замовлення або переглянути історію через головне меню",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 На головну", callback_data="home")],
            [InlineKeyboardButton("📋 Мої замовлення", callback_data="my_orders")]
        ])
    )
    
    return MAIN_MENU

# Перегляд замовлень користувача
async def view_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    # Отримуємо замовлення користувача
    user_orders = db.get_user_orders(user_id)
    
    if not user_orders:
        await query.edit_message_text(
            "У вас ще немає жодного замовлення.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 На головну", callback_data="home")]])
        )
        return MAIN_MENU
    
    message = "*📋 Ваші замовлення:*\n\n"
    
    for idx, order in enumerate(user_orders[:5]):  # Показуємо лише 5 останніх замовлень для простоти
        message += f"{get_status_emoji(order['status'])} *Замовлення #{idx + 1}*\n"
        message += f"Тип: {'🗓 Планове' if order['type'] == 'planned' else '⚡ Термінове'}\n"
        
        # Перетворюємо ISO дату у більш читабельний формат
        order_date = datetime.fromisoformat(order["date"])
        message += f"Дата: {order_date.strftime('%d.%m.%Y %H:%M')}\n"
        
        message += f"Статус: {get_status_text(order['status'])}\n"
        
        # Підрахунок позицій
        item_count = sum(len(products) for products in order["items"].values())
        message += f"Кількість найменувань: {item_count}\n\n"
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 На головну", callback_data="home")]]),
        parse_mode="Markdown"
    )
    
    return MAIN_MENU

# Обробка натискання кнопки "На головну"
async def go_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    return await show_main_menu(update, context)

# Допоміжні функції
def get_status_text(status: str) -> str:
    status_texts = {
        "draft": "Чернетка",
        "confirmed": "Підтверджено",
        "processing": "В обробці",
        "delivered": "Доставлено",
        "cancelled": "Скасовано"
    }
    return status_texts.get(status, status)

def get_status_emoji(status: str) -> str:
    status_emojis = {
        "draft": "📝",
        "confirmed": "✅",
        "processing": "⏳",
        "delivered": "🚚",
        "cancelled": "❌"
    }
    return status_emojis.get(status, "❓")

# Команда "допомога"
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "*Бот для замовлення продуктів на кухню*\n\n"
        "Команди:\n"
        "/start - Почати роботу з ботом\n"
        "/help - Отримати довідку\n\n"
        "Типи замовлень:\n"
        "🗓 *Планове* - тижневі замовлення, які збираються по суботах\n"
        "⚡ *Термінове* - для негайних потреб\n\n"
        "Якщо у вас виникли питання, зверніться до адміністратора.",
        parse_mode="Markdown"
    )

# Обробка невідомих повідомлень
async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Я розумію лише команди. Використовуйте кнопки або введіть /help для допомоги."
    )

# Головна функція
def main() -> None:
    # Створюємо застосунок і передаємо йому токен нашого бота
    application = Application.builder().token(TOKEN).build()
    
    # Перевіряємо підключення до бази даних
    if hasattr(db, 'test_connection'):
        if db.test_connection():
            logger.info("Підключення до бази даних успішне")
        else:
            logger.error("Не вдалося підключитися до бази даних")
    
    # Створюємо ConversationHandler для управління розмовою
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTRATION_ROLE: [
                CallbackQueryHandler(register_role, pattern="^role_")
            ],
            SUPPLIER_CATEGORIES: [
                CallbackQueryHandler(process_supplier_category, pattern="^supplier_cat_|^supplier_categories_done$")
            ],
            SUPPLIER_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_supplier_phone),
                MessageHandler(filters.CONTACT, process_supplier_phone)
            ],
            MAIN_MENU: [
                CallbackQueryHandler(new_order, pattern="^new_order_|^supplier_"),
                CallbackQueryHandler(view_my_orders, pattern="^my_orders$"),
                CallbackQueryHandler(go_home, pattern="^home$")
            ],
            SELECTING_CATEGORY: [
                CallbackQueryHandler(show_products_in_category, pattern="^category_"),
                CallbackQueryHandler(view_current_order, pattern="^view_current_order$"),
                CallbackQueryHandler(go_home, pattern="^home$")
            ],
            SELECTING_PRODUCT: [
                CallbackQueryHandler(add_product, pattern="^add_"),
                CallbackQueryHandler(back_to_categories, pattern="^back_to_categories$"),
                CallbackQueryHandler(view_current_order, pattern="^view_current_order$")
            ],
            VIEWING_ORDER: [
                CallbackQueryHandler(back_to_categories, pattern="^back_to_categories$"),
                CallbackQueryHandler(confirm_order, pattern="^confirm_order$")
            ],
            CONFIRMING_ORDER: [
                CallbackQueryHandler(go_home, pattern="^home$"),
                CallbackQueryHandler(view_my_orders, pattern="^my_orders$")
            ],
        },
        fallbacks=[
            CommandHandler("help", help_command),
            CommandHandler("start", start)
        ],
    )
    
    # Додаємо обробники
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.COMMAND & filters.Regex("^/remove_"), remove_product))
    application.add_handler(CallbackQueryHandler(go_home, pattern="^home$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))
    
    # Запускаємо бота
    print("Бот запущено!")
    application.run_polling()
    
if __name__ == "__main__":
    main()
