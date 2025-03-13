# /app/app.py

from flask import Flask, jsonify, render_template, request
import sqlite3

app = Flask(__name__)

# Функция для подключения к базе данных
def get_db_connection():
    conn = sqlite3.connect('orders.db')
    conn.row_factory = sqlite3.Row
    return conn

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# API для получения списка заказов
@app.route('/api/orders', methods=['GET'])
def get_orders():
    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM orders').fetchall()
    conn.close()
    return jsonify([dict(order) for order in orders])

# API для получения продуктов по ID заказа
@app.route('/api/orders/<int:order_id>/products', methods=['GET'])
def get_order_products(order_id):
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products WHERE order_id = ?', (order_id,)).fetchall()
    conn.close()
    return jsonify([dict(product) for product in products])

if __name__ == "__main__":
    app.run(debug=True)
