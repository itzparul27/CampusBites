# Smart College Canteen Preordering System

A beginner-friendly mini project with a Python backend, HTML/CSS frontend,
and an SQLite database. The interface is called **Campus Bites**.

## Requirements

- Python 3.10 or later
- Flask (installed using the command below)
- A web browser

## Run the project

1. Extract the ZIP, then open a terminal in the `canteen_viva` folder.
2. Install Flask:

   ```text
   python -m pip install -r requirements.txt
   ```

3. Start the program:

   ```text
   python app.py
   ```

4. Open **http://127.0.0.1:5000** in your browser. Keep the terminal open.
5. Stop the program with **Ctrl+C**.

If Windows uses `py` instead of `python`, use `py` in both commands.
If you use Thonny, install Flask through **Tools → Manage packages**, open
`app.py`, click Run, and open the address above in your browser.

The database `canteen.db` and sample menu are created on the first run.
Orders remain saved after restarting the app. Internet is needed for the
initial Flask installation; the running project uses no external assets.

## Features

- Nine sample menu items with prices in rupees
- Cart with quantities from 1 to 10 per item and a remove option
- Student name, roll number, and pickup date/time
- Preorders from 10 minutes ahead up to 7 days ahead
- Confirmation with order number, item details, total, and status
- Tracking using order number AND roll number
- Admin login, order details, status updates, and sold-out controls
- Responsive layout for phone and desktop screens
- Saved orders and order item details in SQLite

## Admin login

Open **Admin** in the navigation bar.

**Default local demonstration password: `admin123`**

The admin can select Placed, Preparing, Ready, Collected, or Cancelled.
Refresh the student's order page to see the latest status.
The dashboard allows manual corrections between these statuses.

## A five-minute demonstration

1. Add two Samosas and one Tea: total **₹40**.
2. Open Cart and enter a student name and roll number.
3. Choose a pickup time at least 11 minutes from now and place the order.
4. Note the order number on the confirmation page.
5. Open Admin in another browser tab, log in, and mark the order Preparing.
6. Open Track order and enter the order number and roll number.
7. Show that the status changed, then mark it Ready in Admin.
8. Mark an item sold out and show that students cannot order it.
9. Restart the app and show that the saved order still exists.

## Files

```text
canteen_viva/
  app.py                Python routes, validation, and database queries
  requirements.txt      Flask dependency
  README.md             Installation and demonstration guide
  VIVA_NOTES.md         Explanation, database design, and viva questions
  test_app.py           Automated functional checks
  templates/            HTML pages with small Jinja loops/conditions
  static/style.css      Plain CSS styling
  canteen.db            Created automatically when running app.py
```

## How it works

The browser requests a page. A Flask route runs a Python function. The
function reads or writes SQLite records and returns an HTML template.
The cart is kept in Flask's signed session cookie. A placed order is saved
in two tables: `orders` for the overall order and `order_items` for its food.
No JavaScript, ORM, classes for business logic, or frontend framework is used.

Change sample items and prices in `init_db()` before the first run. Once a
database exists, editing the seed list does not replace its saved records.

## Run the tests

```text
python -m unittest -v test_app
```

Tests use a temporary database and do not change your saved canteen data.

## Scope

This is a **local educational demonstration**. It uses a simple shared admin
password, a fixed fallback session key, and basic roll-number-based tracking.
It does not include online payment, student accounts, stock counts, kitchen
capacity limits, opening-hour rules, automatic notifications, or CSRF tokens.
Payment is at pickup; times use the computer's local clock. Cancelled orders
remain in the database for record keeping. Use sample student details for demos.

Before a real deployment, add proper accounts, password hashing, CSRF protection,
login rate limiting, HTTPS, and a production server. Set a private `SECRET_KEY`
and `ADMIN_PASSWORD` using environment variables. The development server binds
only to this computer at `127.0.0.1`.

