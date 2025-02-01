# /app/main.py

import sqlite3
import os
from datetime import datetime

# Путь к папке с файлами заказов
ORDERS_FOLDER = './Orders'

# Создание базы данных
def create_database():
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()

    # Таблица заказов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commande TEXT NOT NULL,
            date TEXT NOT NULL,
            payment_method TEXT NOT NULL
        )
    ''')

    # Таблица продуктов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT NOT NULL,
            name TEXT NOT NULL,
            unit_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            order_id INTEGER NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    ''')

    # Таблица итогов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS totals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            products_total REAL NOT NULL,
            discount REAL NOT NULL,
            gift_wrap REAL NOT NULL,
            delivery REAL NOT NULL,
            vat REAL NOT NULL,
            total_paid REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    ''')

    conn.commit()
    conn.close()

# Обработчик парсинга данных
def parse_order(data):
    lines = data.strip().split('\n')
    print(f"Всего строк: {len(lines)}")  # Отладка
    commande_info = lines[1].split(' ')
    commande = commande_info[2]
    date = f"{commande_info[4]} {commande_info[5]}"
    payment_method = lines[3].strip()

    order_products = []
    totals = {}

    is_product_section = False
    is_totals_section = False
    product_buffer = []  # Буфер для строк продукта

    for i, line in enumerate(lines):
        line = line.strip()  # Убираем пробелы
        print(f"Обработка строки {i}: '{line}'")  # Отладка

        # Начало секции продуктов
        if 'Référence' in line and 'produit' in line:
            is_product_section = True
            print("Начало секции продуктов")  # Отладка
            continue

        # Сбор строк продукта
        if is_product_section:
            # Прекращаем обработку продуктов, если встречаем строку итогов
            if 'produits' in line or 'Total payé' in line:
                is_product_section = False
                is_totals_section = True
                print("Конец секции продуктов, начало итогов")  # Отладка
                continue

            # Если строка пустая, пропускаем её
            if not line:
                continue

            # Добавляем строку в буфер
            product_buffer.append(line)

            # Обрабатываем продукт после 5 строк
            if len(product_buffer) == 5:
                try:
                    reference = product_buffer[0]
                    name = product_buffer[1]
                    unit_price = float(product_buffer[2].replace('€', '').replace(',', '.'))
                    quantity = int(product_buffer[3])
                    total_price = float(product_buffer[4].replace('€', '').replace(',', '.'))

                    # Добавляем продукт
                    order_products.append({
                        'reference': reference,
                        'name': name,
                        'unit_price': unit_price,
                        'quantity': quantity,
                        'total_price': total_price,
                    })
                    print(f"Добавлен продукт: {reference}, {name}, {unit_price}, {quantity}, {total_price}")  # Отладка
                except Exception as e:
                    print(f"Ошибка обработки продукта: {product_buffer}, Ошибка: {e}")
                finally:
                    product_buffer = []  # Очищаем буфер для следующего продукта

        # Парсинг итогов
        if is_totals_section:
            try:
                if 'produits' in line:
                    totals['products_total'] = extract_float_from_next_line(lines, i)
                elif 'Réductions' in line:
                    totals['discount'] = extract_float_from_next_line(lines, i)
                elif 'TVA totale payée' in line:
                    totals['vat'] = extract_float_from_next_line(lines, i)
                elif 'Total payé' in line:
                    totals['total_paid'] = extract_float_from_next_line(lines, i)
            except ValueError as e:
                print(f"Ошибка обработки итогов: {line}, Ошибка: {e}")
                continue

    print(f"Распознанные продукты: {order_products}")  # Отладка
    print(f"Распознанные итоги: {totals}")  # Отладка

    return {
        'commande': commande,
        'date': date,
        'payment_method': payment_method,
        'products': order_products,
        'totals': totals
    }



# Вспомогательная функция для извлечения числового значения из следующей строки
def extract_float_from_next_line(lines, current_index):
    """Извлекает числовое значение из строки, находящейся после текущей."""
    if current_index + 1 < len(lines):  # Проверяем, есть ли следующая строка
        next_line = lines[current_index + 1].strip()
        print(f"Проверка строки: '{next_line}'")  # Отладка: выводим следующую строку
        import re
        match = re.search(r'[-+]?\d*,?\d+\s?€?', next_line)
        if match:
            # Если совпадение найдено, преобразуем его в число
            print(f"Найдено значение: {match.group(0)}")  # Отладка: выводим найденное значение
            return float(match.group(0).replace('€', '').replace(',', '.').strip())
        else:
            print(f"Не найдено числовое значение в строке: '{next_line}'")  # Отладка: строка не содержит числа
    raise ValueError(f"Не удалось найти числовое значение в строке: {lines[current_index]} или следующей строке.")



# Сохранение данных в базу
def save_to_database(order_data):
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()

    # Проверяем, существует ли уже заказ с таким номером
    cursor.execute('SELECT id FROM orders WHERE commande = ?', (order_data['commande'],))
    existing_order = cursor.fetchone()

    if existing_order:
        print(f"Заказ {order_data['commande']} уже существует в базе данных. Пропуск.")
        conn.close()
        return  # Выход из функции, если заказ уже есть

    # Сохраняем заказ
    cursor.execute('INSERT INTO orders (commande, date, payment_method) VALUES (?, ?, ?)', 
                   (order_data['commande'], order_data['date'], order_data['payment_method']))
    order_id = cursor.lastrowid

    # Сохраняем продукты
    for product in order_data['products']:
        print(f"Inserting product into DB: {product}")  # Отладка
        cursor.execute('''
            INSERT INTO products (reference, name, unit_price, quantity, total_price, order_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (product['reference'], product['name'], product['unit_price'], product['quantity'], product['total_price'], order_id))

    # Сохраняем итоги
    totals = order_data['totals']
    cursor.execute('''
        INSERT INTO totals (order_id, products_total, discount, gift_wrap, delivery, vat, total_paid)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (order_id, totals.get('products_total', 0), totals.get('discount', 0), totals.get('gift_wrap', 0), 
          totals.get('delivery', 0), totals.get('vat', 0), totals.get('total_paid', 0)))

    conn.commit()
    conn.close()


# Обработка всех файлов из папки
def process_orders_from_folder():
    for file_name in os.listdir(ORDERS_FOLDER):
        file_path = os.path.join(ORDERS_FOLDER, file_name)
        if os.path.isfile(file_path) and file_name.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as file:
                data = file.read()
                try:
                    parsed_data = parse_order(data)
                    save_to_database(parsed_data)
                    print(f"Order from {file_name} saved successfully.")
                except Exception as e:
                    print(f"Error processing {file_name}: {e}")

# Тестирование
if __name__ == "__main__":
    create_database()
    process_orders_from_folder()
