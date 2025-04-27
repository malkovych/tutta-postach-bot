import os
import logging
import mysql.connector
from datetime import datetime
from mysql.connector import Error

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Налаштування з'єднання з базою даних
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'rav4.cityhost.com.ua'),
    'database': os.environ.get('DB_NAME', 'chf1f5f332_tutta-postach'),
    'user': os.environ.get('DB_USER', 'chf1f5f332_tutta-postach'),
    'password': os.environ.get('DB_PASSWORD', 'WYwum33Tma'),
    'charset': 'utf8mb4',
    'use_unicode': True
}

# Функція для з'єднання з базою даних
def get_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        logger.error(f"Помилка з'єднання з базою даних: {e}")
        return None

# Перевірити підключення до бази даних
def test_connection():
    conn = get_connection()
    if conn and conn.is_connected():
        logger.info("З'єднання з базою даних успішне")
        conn.close()
        return True
    else:
        logger.error("Не вдалося з'єднатися з базою даних")
        return False

# Функції для роботи з користувачами
def get_user(user_id):
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (str(user_id),))
        user = cursor.fetchone()
        return user
    except Error as e:
        logger.error(f"Помилка отримання користувача: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def create_user(user_id, name, username, role):
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        query = """
        INSERT INTO users (user_id, name, username, role, registration_date)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (str(user_id), name, username, role, datetime.now().isoformat()))
        conn.commit()
        return True
    except Error as e:
        logger.error(f"Помилка створення користувача: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def update_user(user_id, data):
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        query_parts = []
        params = []
        
        for key, value in data.items():
            query_parts.append(f"{key} = %s")
            params.append(value)
        
        params.append(str(user_id))
        query = f"UPDATE users SET {', '.join(query_parts)} WHERE user_id = %s"
        
        cursor.execute(query, params)
        conn.commit()
        return True
    except Error as e:
        logger.error(f"Помилка оновлення користувача: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# Функції для роботи з постачальниками
def create_supplier(supplier_id, user_id, name, phone):
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        query = """
        INSERT INTO suppliers (id, user_id, name, phone, registration_date, active)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (supplier_id, str(user_id), name, phone, datetime.now().isoformat(), True))
        conn.commit()
        return True
    except Error as e:
        logger.error(f"Помилка створення постачальника: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def add_supplier_category(supplier_id, category_id):
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT IGNORE INTO supplier_categories (supplier_id, category_id) VALUES (%s, %s)",
            (supplier_id, category_id)
        )
        conn.commit()
        return True
    except Error as e:
        logger.error(f"Помилка додавання категорії постачальника: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def remove_supplier_category(supplier_id, category_id):
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM supplier_categories WHERE supplier_id = %s AND category_id = %s",
            (supplier_id, category_id)
        )
        conn.commit()
        return True
    except Error as e:
        logger.error(f"Помилка видалення категорії постачальника: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_supplier_categories(supplier_id):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.name FROM supplier_categories sc
            JOIN categories c ON sc.category_id = c.id
            WHERE sc.supplier_id = %s
        """, (supplier_id,))
        categories = [row['name'] for row in cursor.fetchall()]
        return categories
    except Error as e:
        logger.error(f"Помилка отримання категорій постачальника: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_all_suppliers():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.id, s.user_id, s.name, s.phone 
            FROM suppliers s
            WHERE s.active = TRUE
        """)
        
        suppliers = cursor.fetchall()
        
        # Отримуємо категорії для кожного постачальника
        for supplier in suppliers:
            supplier['categories'] = get_supplier_categories(supplier['id'])
        
        return suppliers
    except Error as e:
        logger.error(f"Помилка отримання списку постачальників: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_suppliers():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, user_id, name, phone FROM suppliers WHERE active = TRUE")
        return cursor.fetchall()
    except Error as e:
        logger.error(f"Помилка отримання постачальників: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# Функції для роботи з категоріями і продуктами
def get_categories():
    conn = get_connection()
    if not conn:
        return {}
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name FROM categories")
        categories = {row['name']: [] for row in cursor.fetchall()}
        
        for category_name in categories:
            cursor.execute("""
                SELECT p.name FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE c.name = %s
            """, (category_name,))
            products = [row['name'] for row in cursor.fetchall()]
            categories[category_name] = products
        
        return categories
    except Error as e:
        logger.error(f"Помилка отримання категорій: {e}")
        return {}
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_category_id_by_name(category_name):
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM categories WHERE name = %s", (category_name,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Error as e:
        logger.error(f"Помилка отримання ID категорії: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_product_id(product_name, category_id):
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM products WHERE name = %s AND category_id = %s",
            (product_name, category_id)
        )
        result = cursor.fetchone()
        return result[0] if result else None
    except Error as e:
        logger.error(f"Помилка отримання ID продукту: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# Функції для роботи з замовленнями
def create_order(order_id, order_type, user_id, user_name):
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        query = """
        INSERT INTO orders (id, type, user_id, user_name, date, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            order_id, 
            order_type, 
            str(user_id), 
            user_name, 
            datetime.now().isoformat(), 
            'draft'
        ))
        conn.commit()
        return True
    except Error as e:
        logger.error(f"Помилка створення замовлення: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def update_order_status(order_id, status):
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        if status == 'confirmed':
            query = "UPDATE orders SET status = %s, confirmation_date = %s WHERE id = %s"
            cursor.execute(query, (status, datetime.now().isoformat(), order_id))
        else:
            query = "UPDATE orders SET status = %s WHERE id = %s"
            cursor.execute(query, (status, order_id))
        
        conn.commit()
        return True
    except Error as e:
        logger.error(f"Помилка оновлення статусу замовлення: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def add_order_item(order_id, category_name, product_name):
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Отримати ID категорії
        category_id = get_category_id_by_name(category_name)
        if not category_id:
            logger.error(f"Категорія не знайдена: {category_name}")
            return False
        
        # Отримати ID продукту
        product_id = get_product_id(product_name, category_id)
        if not product_id:
            logger.error(f"Продукт не знайдений: {product_name} в категорії {category_name}")
            return False
        
        # Додати позицію до замовлення
        cursor.execute(
            "INSERT INTO order_items (order_id, product_id) VALUES (%s, %s)",
            (order_id, product_id)
        )
        
        conn.commit()
        return True
    except Error as e:
        logger.error(f"Помилка додавання позиції до замовлення: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def remove_order_item(order_id, category_name, product_index):
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Отримати ID категорії
        category_id = get_category_id_by_name(category_name)
        if not category_id:
            logger.error(f"Категорія не знайдена: {category_name}")
            return None
        
        # Отримати всі продукти для даної категорії в замовленні
        cursor.execute("""
            SELECT oi.id, p.name FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s AND p.category_id = %s
            ORDER BY oi.id
        """, (order_id, category_id))
        
        items = cursor.fetchall()
        
        if product_index >= len(items):
            logger.error(f"Індекс продукту поза межами: {product_index}")
            return None
        
        # Отримати ID позиції та назву продукту
        item_id = items[product_index]['id']
        product_name = items[product_index]['name']
        
        # Видалити позицію з замовлення
        cursor.execute("DELETE FROM order_items WHERE id = %s", (item_id,))
        
        conn.commit()
        return product_name
    except Error as e:
        logger.error(f"Помилка видалення позиції з замовлення: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_order(order_id):
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Отримати інформацію про замовлення
        cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
        order = cursor.fetchone()
        
        if not order:
            return None
        
        # Отримати позиції замовлення з категоріями
        cursor.execute("""
            SELECT c.name as category, p.name as product
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            WHERE oi.order_id = %s
            ORDER BY c.name, p.name
        """, (order_id,))
        
        items = cursor.fetchall()
        
        # Згрупувати позиції за категоріями
        order_items = {}
        for item in items:
            category = item['category']
            product = item['product']
            
            if category not in order_items:
                order_items[category] = []
            
            order_items[category].append(product)
        
        order['items'] = order_items
        
        return order
    except Error as e:
        logger.error(f"Помилка отримання замовлення: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_user_orders(user_id):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Отримати замовлення користувача
        cursor.execute("""
            SELECT id, type, date, confirmation_date, status
            FROM orders
            WHERE user_id = %s
            ORDER BY date DESC
        """, (str(user_id),))
        
        orders = cursor.fetchall()
        
        # Для кожного замовлення отримати позиції
        for order in orders:
            order_id = order['id']
            
            cursor.execute("""
                SELECT c.name as category, p.name as product
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN categories c ON p.category_id = c.id
                WHERE oi.order_id = %s
            """, (order_id,))
            
            items = cursor.fetchall()
            
            # Згрупувати позиції за категоріями
            order_items = {}
            for item in items:
                category = item['category']
                product = item['product']
                
                if category not in order_items:
                    order_items[category] = []
                
                order_items[category].append(product)
            
            order['items'] = order_items
        
        return orders
    except Error as e:
        logger.error(f"Помилка отримання замовлень користувача: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_relevant_orders_for_supplier(user_id):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Отримати категорії, які постачає постачальник
        supplier_id = f"supplier_{user_id}"
        cursor.execute("""
            SELECT c.name FROM supplier_categories sc
            JOIN categories c ON sc.category_id = c.id
            JOIN suppliers s ON sc.supplier_id = s.id
            WHERE s.user_id = %s
        """, (str(user_id),))
        
        categories = [row['name'] for row in cursor.fetchall()]
        
        if not categories:
            return []
        
        # Знайти замовлення зі статусом 'confirmed', які містять товари з категорій постачальника
        placeholders = ', '.join(['%s'] * len(categories))
        query = f"""
            SELECT DISTINCT o.id, o.type, o.user_id, o.user_name, o.date, o.confirmation_date, o.status
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            WHERE o.status = 'confirmed' AND c.name IN ({placeholders})
        """
        
        cursor.execute(query, categories)
        orders = cursor.fetchall()
        
        # Для кожного замовлення отримати тільки товари з категорій постачальника
        for order in orders:
            order_id = order['id']
            
            placeholders = ', '.join(['%s'] * (len(categories) + 1))
            query = f"""
                SELECT c.name as category, p.name as product
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN categories c ON p.category_id = c.id
                WHERE oi.order_id = %s AND c.name IN ({placeholders})
            """
            
            params = [order_id] + categories
            cursor.execute(query, params)
            
            items = cursor.fetchall()
            
            # Згрупувати позиції за категоріями
            order_items = {}
            for item in items:
                category = item['category']
                product = item['product']
                
                if category not in order_items:
                    order_items[category] = []
                
                order_items[category].append(product)
            
            order['items'] = order_items
        
        return orders
    except Error as e:
        logger.error(f"Помилка отримання замовлень для постачальника: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
