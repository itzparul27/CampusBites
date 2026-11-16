"""Smart College Canteen: simple Flask routes and SQLite queries."""
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'college-canteen-local-demo-key')
app.config['DATABASE'] = str(Path(__file__).with_name('canteen.db'))
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'admin123')
STATUSES = ['Placed', 'Preparing', 'Ready', 'Collected', 'Cancelled']


def get_db():
    connection = sqlite3.connect(app.config['DATABASE'])
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def init_db():
    connection = get_db()
    connection.executescript('''
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price INTEGER NOT NULL CHECK(price > 0),
            available INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            roll_number TEXT NOT NULL,
            pickup_time TEXT NOT NULL,
            total INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Placed',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES orders(id),
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price INTEGER NOT NULL
        );
    ''')
    if connection.execute('SELECT COUNT(*) FROM menu').fetchone()[0] == 0:
        connection.executemany(
            'INSERT INTO menu (name, category, price) VALUES (?, ?, ?)',
            [('Veg Sandwich', 'Snacks', 45), ('Samosa', 'Snacks', 15),
             ('Veg Burger', 'Snacks', 55), ('Masala Dosa', 'Meals', 60),
             ('Veg Fried Rice', 'Meals', 80), ('Mini Thali', 'Meals', 90),
             ('Tea', 'Drinks', 10), ('Cold Coffee', 'Drinks', 40),
             ('Lemon Juice', 'Drinks', 25)])
    connection.commit()
    connection.close()


def read_cart():
    """Read current prices from SQLite; never trust prices from the browser."""
    connection = get_db()
    items = []
    total = 0
    for item_id, quantity in session.get('cart', {}).items():
        row = connection.execute('SELECT * FROM menu WHERE id = ?', (item_id,)).fetchone()
        if row:
            item = dict(row)
            item['quantity'] = quantity
            item['subtotal'] = row['price'] * quantity
            items.append(item)
            total += item['subtotal']
    connection.close()
    return items, total


@app.route('/')
def home():
    connection = get_db()
    menu = connection.execute('SELECT * FROM menu ORDER BY id').fetchall()
    connection.close()
    return render_template('menu.html', menu=menu)


@app.route('/add/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    try:
        quantity = int(request.form.get('quantity', '1'))
    except ValueError:
        quantity = 0
    connection = get_db()
    item = connection.execute('SELECT * FROM menu WHERE id = ?', (item_id,)).fetchone()
    connection.close()
    basket = session.get('cart', {})
    if not item or not item['available']:
        flash('This item is currently unavailable.')
    elif not 1 <= quantity <= 10 or basket.get(str(item_id), 0) + quantity > 10:
        flash('Choose between 1 and 10 of each item.')
    else:
        basket[str(item_id)] = basket.get(str(item_id), 0) + quantity
        session['cart'] = basket
        flash(item['name'] + ' added to your cart.')
    return redirect(url_for('home'))


@app.route('/remove/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    basket = session.get('cart', {})
    basket.pop(str(item_id), None)
    session['cart'] = basket
    return redirect(url_for('cart'))


def checkout_error(items, name, roll, pickup):
    if not items:
        return 'Your cart is empty.'
    if not name or not roll or len(name) > 60 or len(roll) > 30:
        return 'Enter your name (up to 60 characters) and roll number (up to 30 characters).'

    try:
        pickup_date = datetime.strptime(pickup, '%Y-%m-%dT%H:%M')
    except ValueError:
        return 'Enter a valid pickup date and time.'

    now = datetime.now()
    earliest = now + timedelta(minutes=10)
    latest = now + timedelta(days=7)
    if pickup_date < earliest or pickup_date > latest:
        return 'Select a pickup time at least 10 minutes ahead and within 7 days.'
    return ''


def save_order(items, total, name, roll, pickup):
    connection = get_db()
    try:
        # Check availability and save the order in one transaction.
        connection.execute('BEGIN IMMEDIATE')
        for item in items:
            row = connection.execute(
                'SELECT available FROM menu WHERE id = ?', (item['id'],)
            ).fetchone()
            if not row or not row['available']:
                return None

        created_at = datetime.now().strftime('%Y-%m-%d %H:%M')
        result = connection.execute(
            'INSERT INTO orders (student_name, roll_number, pickup_time, total, created_at) '
            'VALUES (?, ?, ?, ?, ?)',
            (name, roll, pickup, total, created_at)
        )
        order_id = result.lastrowid

        for item in items:
            connection.execute(
                'INSERT INTO order_items (order_id, item_name, quantity, price) VALUES (?, ?, ?, ?)',
                (order_id, item['name'], item['quantity'], item['price'])
            )

        connection.commit()
        return order_id
    finally:
        # Closing also rolls back any changes that were not committed.
        connection.close()


@app.route('/cart', methods=['GET', 'POST'])
def cart():
    items, total = read_cart()
    minimum = (datetime.now() + timedelta(minutes=11)).strftime('%Y-%m-%dT%H:%M')
    if request.method == 'GET':
        return render_template('cart.html', items=items, total=total, minimum=minimum)

    name = request.form.get('student_name', '').strip()
    roll = request.form.get('roll_number', '').strip().upper()
    pickup = request.form.get('pickup_time', '')
    error = checkout_error(items, name, roll, pickup)
    if error:
        flash(error)
        return render_template('cart.html', items=items, total=total, minimum=minimum)

    order_id = save_order(items, total, name, roll, pickup)
    if order_id is None:
        flash('An item is unavailable. Remove it from your cart to continue.')
        return render_template('cart.html', items=items, total=total, minimum=minimum)

    session['cart'] = {}
    session['last_order'] = order_id
    flash('Preorder placed! Pay at the canteen when collecting your food.')
    return redirect(url_for('order_detail', order_id=order_id))


@app.route('/track', methods=['GET', 'POST'])
def track():
    if request.method == 'POST':
        connection = get_db()
        order = connection.execute('SELECT id FROM orders WHERE id = ? AND roll_number = ?',
                                   (request.form.get('order_id', ''), request.form.get('roll_number', '').strip().upper())).fetchone()
        connection.close()
        if order:
            session['last_order'] = order['id']
            return redirect(url_for('order_detail', order_id=order['id']))
        flash('No matching order. Check the order number and roll number.')
    return render_template('track.html')


@app.route('/order/<int:order_id>')
def order_detail(order_id):
    if session.get('last_order') != order_id and not session.get('admin'):
        return redirect(url_for('track'))
    connection = get_db()
    order = connection.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    items = connection.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,)).fetchall()
    connection.close()
    if not order:
        abort(404)
    return render_template('order.html', order=order, items=items)


@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == app.config['ADMIN_PASSWORD']:
            session['admin'] = True
            return redirect(url_for('admin'))
        flash('Incorrect admin password.')
    return render_template('login.html')


@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect(url_for('login'))

    connection = get_db()
    orders = connection.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
    menu = connection.execute('SELECT * FROM menu ORDER BY id').fetchall()
    connection.close()
    return render_template('admin.html', orders=orders, menu=menu, statuses=STATUSES)


@app.route('/admin/status/<int:order_id>', methods=['POST'])
def update_status(order_id):
    if not session.get('admin'):
        return redirect(url_for('login'))

    status = request.form.get('status')
    if status in STATUSES:
        connection = get_db()
        connection.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
        connection.commit()
        connection.close()
        flash('Order status updated.')
    return redirect(url_for('admin'))


@app.route('/admin/availability/<int:item_id>', methods=['POST'])
def toggle_availability(item_id):
    if not session.get('admin'):
        return redirect(url_for('login'))

    connection = get_db()
    connection.execute('UPDATE menu SET available = 1 - available WHERE id = ?', (item_id,))
    connection.commit()
    connection.close()
    return redirect(url_for('admin'))


@app.route('/admin/logout', methods=['POST'])
def logout():
    session.pop('admin', None)
    return redirect(url_for('home'))


if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=5000)
