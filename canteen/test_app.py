"""Functional tests using Flask's test browser and a temporary database."""
import os
import tempfile
import unittest
from datetime import datetime, timedelta

from app import app, init_db, get_db


class CanteenTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        app.config.update(TESTING=True, DATABASE=os.path.join(self.folder.name, 'test.db'))
        init_db()
        self.client = app.test_client()

    def tearDown(self):
        self.folder.cleanup()

    def checkout(self):
        return self.client.post('/cart', data={
            'student_name': 'Demo Student', 'roll_number': 'cs101',
            'pickup_time': (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
        }, follow_redirects=True)

    def test_student_admin_tracking_and_persistence(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.client.post('/add/2', data={'quantity': '2'})
        self.client.post('/add/7', data={'quantity': '1'})
        response = self.checkout()
        self.assertIn(b'Order #1', response.data)
        connection = get_db()
        order = connection.execute('SELECT * FROM orders').fetchone()
        self.assertEqual(order['total'], 40)
        self.assertEqual(order['roll_number'], 'CS101')
        self.assertEqual(connection.execute('SELECT COUNT(*) FROM order_items').fetchone()[0], 2)
        connection.close()
        self.assertIn(b'Your cart is empty', self.client.get('/cart').data)
        stranger = app.test_client()
        self.assertEqual(stranger.get('/order/1').status_code, 302)
        self.assertIn(b'No matching order', stranger.post('/track', data={'order_id': '1', 'roll_number': 'wrong'}, follow_redirects=True).data)
        self.assertEqual(stranger.post('/admin/status/1', data={'status': 'Ready'}).status_code, 302)
        self.assertIn(b'Incorrect', stranger.post('/admin/login', data={'password': 'wrong'}, follow_redirects=True).data)
        self.client.post('/admin/login', data={'password': app.config['ADMIN_PASSWORD']})
        self.assertEqual(self.client.get('/admin').status_code, 200)
        self.client.post('/admin/status/1', data={'status': 'Ready'})
        tracked = stranger.post('/track', data={'order_id': '1', 'roll_number': 'cs101'}, follow_redirects=True)
        self.assertIn(b'Ready', tracked.data)
        init_db()  # Startup does not erase existing orders or duplicate the menu.
        connection = get_db()
        self.assertEqual(connection.execute('SELECT COUNT(*) FROM menu').fetchone()[0], 9)
        self.assertEqual(connection.execute('SELECT status FROM orders').fetchone()[0], 'Ready')
        connection.close()
        self.client.post('/admin/logout')
        self.assertEqual(self.client.get('/admin').status_code, 302)

    def test_validation_and_remove(self):
        for value in ['0', '-1', '11', 'abc']:
            self.client.post('/add/1', data={'quantity': value})
        with self.client.session_transaction() as data:
            self.assertEqual(data.get('cart', {}), {})
        self.client.post('/add/1', data={'quantity': '10'})
        self.client.post('/add/1', data={'quantity': '1'})
        with self.client.session_transaction() as data:
            self.assertEqual(data['cart']['1'], 10)
        response = self.client.post('/cart', data={'student_name': 'A', 'roll_number': 'B', 'pickup_time': '2000-01-01T10:00'}, follow_redirects=True)
        self.assertIn(b'at least 10 minutes', response.data)
        response = self.client.post('/cart', data={'pickup_time': 'not a date'}, follow_redirects=True)
        self.assertIn(b'Enter your name', response.data)
        self.client.post('/remove/1')
        self.assertIn(b'Your cart is empty', self.client.get('/cart').data)
        self.checkout()
        connection = get_db()
        self.assertEqual(connection.execute('SELECT COUNT(*) FROM orders').fetchone()[0], 0)
        connection.close()

    def test_unavailable_item_at_checkout(self):
        self.client.post('/add/1', data={'quantity': '1'})
        self.client.post('/admin/login', data={'password': app.config['ADMIN_PASSWORD']})
        self.client.post('/admin/availability/1')
        self.assertIn(b'An item is unavailable', self.checkout().data)
        self.client.post('/remove/1')
        self.client.post('/add/1', data={'quantity': '1'})
        with self.client.session_transaction() as data:
            self.assertEqual(data['cart'], {})
        self.client.post('/admin/availability/1')
        self.client.post('/add/1', data={'quantity': '1'})
        self.assertIn(b'Order #1', self.checkout().data)
        self.client.post('/admin/status/1', data={'status': 'invalid'})
        connection = get_db()
        self.assertEqual(connection.execute('SELECT status FROM orders').fetchone()[0], 'Placed')
        connection.close()


if __name__ == '__main__':
    unittest.main()
