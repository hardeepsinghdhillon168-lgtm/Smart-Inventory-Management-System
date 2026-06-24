from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Database Connection
def get_db_connection():
    return mysql.connector.connect(
        host="sql12.freesqldatabase.com",
        user="sql12831458",
        password="mham3m9v5v",
        database="sql12831458",
        port=3306
    )
# 1. Login Route with Database Check
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if email == 'admin@system.com' and password == 'admin123':
            session['loggedin'] = True
            session['role'] = 'SuperAdmin'
            session['name'] = 'Super Admin'
            return redirect('/dashboard')
            
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['loggedin'] = True
            session['role'] = user['role']
            session['name'] = user['name']
            return redirect('/dashboard')
        else:
            flash('Invalid email or password', 'danger')
            
    return render_template('login.html')

# 2. Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session:
        return redirect('/')
        
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT COUNT(*) as total FROM products")
    total_products = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total_sales FROM sales")
    total_sales = cursor.fetchone()['total_sales']
    
    cursor.execute("SELECT COUNT(*) as low_stock FROM products WHERE current_stock <= min_stock_level")
    low_stock = cursor.fetchone()['low_stock']
    
    return render_template('dashboard.html', total_products=total_products, total_sales=total_sales, low_stock=low_stock, role=session['role'])

# 3. Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# 4. View Products Route
@app.route('/products')
def products():
    if 'loggedin' not in session:
        return redirect('/')
        
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products ORDER BY id DESC")
    all_products = cursor.fetchall()
    
    return render_template('products.html', products=all_products, role=session['role'])

# 5. Add Product Route (API)
@app.route('/add_product', methods=['POST'])
def add_product():
    if 'loggedin' not in session:
        return redirect('/')
        
    name = request.form['name']
    price = request.form['price']
    stock = request.form['stock']
    min_stock = request.form['min_stock']
    max_stock = request.form['max_stock']
    
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO products (name, price, current_stock, min_stock_level, max_stock_level) VALUES (%s, %s, %s, %s, %s)",
        (name, price, stock, min_stock, max_stock)
    )
    db.commit()
    flash("Product added successfully!", "success")
    return redirect('/products')

# 6. View Sales Route
@app.route('/sales')
def sales():
    if 'loggedin' not in session:
        return redirect('/')
        
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT sales.id, products.name, sales.quantity, sales.sale_date, (sales.quantity * products.price) as total_value
        FROM sales
        JOIN products ON sales.product_id = products.id
        ORDER BY sales.id DESC
    """)
    sales_data = cursor.fetchall()
    
    cursor.execute("SELECT id, name, current_stock FROM products WHERE current_stock > 0")
    available_products = cursor.fetchall()
    
    return render_template('sales.html', sales=sales_data, products=available_products, role=session['role'])

# 7. Add Sale Route (API)
@app.route('/add_sale', methods=['POST'])
def add_sale():
    if 'loggedin' not in session:
        return redirect('/')
        
    product_id = request.form['product_id']
    quantity = int(request.form['quantity'])
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT current_stock FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    
    if product and product['current_stock'] >= quantity:
        # Record the sale
        cursor.execute("INSERT INTO sales (product_id, quantity) VALUES (%s, %s)", (product_id, quantity))
        # Deduct the stock from inventory
        cursor.execute("UPDATE products SET current_stock = current_stock - %s WHERE id = %s", (quantity, product_id))
        db.commit()
    else:
        flash("Not enough stock available for this sale!")
        
    return redirect('/sales')

# 8. Machine Learning Analytics Route
@app.route('/analytics')
def analytics():
    if 'loggedin' not in session:
        return redirect('/')
        
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT DATE(sale_date) as date, SUM(quantity) as total_sold 
        FROM sales 
        GROUP BY DATE(sale_date) 
        ORDER BY date ASC
    """)
    sales_data = cursor.fetchall()
    
    prediction_msg = "Not enough data to predict."
    next_week_demand = 0
    chart_labels = []
    chart_data = []

    if len(sales_data) > 0:
        df = pd.DataFrame(sales_data)
        df['date'] = pd.to_datetime(df['date'])
        
        # DEMO MODE
        if len(df) < 3:
            today = df['date'].iloc[0]
            dummy_dates = [today - timedelta(days=2), today - timedelta(days=1)]
            dummy_sales = [2, 5] 
            dummy_df = pd.DataFrame({'date': dummy_dates, 'total_sold': dummy_sales})
            df = pd.concat([dummy_df, df]).reset_index(drop=True)

        df['days_since_start'] = (df['date'] - df['date'].min()).dt.days
        X = df[['days_since_start']].values
        y = df['total_sold'].values
        
        model = LinearRegression()
        model.fit(X, y)
        
        future_days = np.array([[df['days_since_start'].max() + i] for i in range(1, 8)])
        future_predictions = model.predict(future_days)
        next_week_demand = max(0, int(sum(future_predictions)))
        
        chart_labels = df['date'].dt.strftime('%Y-%m-%d').tolist()
        chart_data = df['total_sold'].astype(int).tolist()

    return render_template('analytics.html', 
                           role=session['role'], 
                           prediction_msg=prediction_msg, 
                           next_week_demand=next_week_demand,
                           chart_labels=json.dumps(chart_labels),
                           chart_data=json.dumps(chart_data))

# 9. User Management Route
@app.route('/users')
def users():
    # SECURITY Check
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Access Denied: Only Admins can manage users.", "danger")
        return redirect('/dashboard')
        
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email, role, created_at FROM users ORDER BY id DESC")
    all_users = cursor.fetchall()
    
    return render_template('users.html', users=all_users, role=session['role'])

# 10. Add New User Route
@app.route('/add_user', methods=['POST'])
def add_user():
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin']:
        return redirect('/dashboard')
        
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']
    
    db = get_db_connection()
    cursor = db.cursor()
    try:
  
        hashed_pw = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
            (name, email, hashed_pw, role)
        )
        db.commit()
        flash("User created successfully!", "success")
    except:
        flash("Error: Email already exists in the system.", "danger")
        
    return redirect('/users')

# 11. Delete User Route
def delete_user(id):
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin']:
        return redirect('/dashboard')
        
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (id,))
    db.commit()
    flash("User deleted.", "success")
    return redirect('/users')

# 12. Edit Product Route
@app.route('/edit_product', methods=['POST'])
def edit_product():
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin', 'Manager']:
        flash("Access Denied.", "danger")
        return redirect('/products')
        
    p_id = request.form['id']
    name = request.form['name']
    price = request.form['price']
    stock = request.form['stock']
    min_stock = request.form['min_stock']
    max_stock = request.form['max_stock']
    
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE products 
        SET name=%s, price=%s, current_stock=%s, min_stock_level=%s, max_stock_level=%s 
        WHERE id=%s
    """, (name, price, stock, min_stock, max_stock, p_id))
    db.commit()
    flash("Product updated successfully!", "success")
    return redirect('/products')

# 13. Edit User Route
@app.route('/edit_user', methods=['POST'])
def edit_user():
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin']:
        flash("Access Denied.", "danger")
        return redirect('/users')
        
    u_id = request.form['id']
    name = request.form['name']
    role = request.form['role']
    
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET name=%s, role=%s WHERE id=%s", (name, role, u_id))
    db.commit()
    flash("User updated successfully!", "success")
    return redirect('/users')

# 14. Edit Sale Route
@app.route('/edit_sale', methods=['POST'])
def edit_sale():
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin', 'Manager']:
        flash("Access Denied.", "danger")
        return redirect('/sales')
        
    s_id = request.form['id']
    new_qty = int(request.form['quantity'])
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT product_id, quantity FROM sales WHERE id = %s", (s_id,))
    old_sale = cursor.fetchone()
    
    if old_sale:
        qty_difference = new_qty - old_sale['quantity']
        
        cursor.execute("UPDATE sales SET quantity = %s WHERE id = %s", (new_qty, s_id))
        
        cursor.execute("UPDATE products SET current_stock = current_stock - %s WHERE id = %s", 
                       (qty_difference, old_sale['product_id']))
        db.commit()
        flash("Sale updated and inventory adjusted!", "success")
        
    return redirect('/sales')

# 15. View & Add Suppliers
@app.route('/suppliers', methods=['GET', 'POST'])
def suppliers():
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin', 'Purchase']:
        flash("Access Denied.", "danger")
        return redirect('/dashboard')
        
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    if request.method == 'POST':
        name = request.form['name']
        company = request.form['company']
        phone = request.form['phone']
        cursor.execute("INSERT INTO suppliers (name, company, phone) VALUES (%s, %s, %s)", (name, company, phone))
        db.commit()
        flash("Supplier added successfully!", "success")
        return redirect('/suppliers')
        
    cursor.execute("SELECT * FROM suppliers ORDER BY id DESC")
    all_suppliers = cursor.fetchall()
    return render_template('suppliers.html', suppliers=all_suppliers, role=session['role'])

# 16. Delete Supplier
@app.route('/delete_supplier/<int:id>')
def delete_supplier(id):
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin']:
        return redirect('/suppliers')
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM suppliers WHERE id = %s", (id,))
        db.commit()
        flash("Supplier removed.", "success")
    except:
        flash("Cannot delete supplier because they are linked to purchase orders.", "danger")
    return redirect('/suppliers')

# 17. View & Add Purchase
@app.route('/purchases', methods=['GET', 'POST'])
def purchases():
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin', 'Purchase', 'Store']:
        flash("Access Denied.", "danger")
        return redirect('/dashboard')
        
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    if request.method == 'POST':
        supplier_id = request.form['supplier_id']
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        total_cost = request.form['total_cost']
        
        # Insert Purchase
        cursor.execute("INSERT INTO purchases (supplier_id, product_id, quantity, total_cost) VALUES (%s, %s, %s, %s)", 
                       (supplier_id, product_id, quantity, total_cost))
        
        cursor.execute("UPDATE products SET current_stock = current_stock + %s WHERE id = %s", (quantity, product_id))
        db.commit()
        flash("Purchase recorded and inventory increased!", "success")
        return redirect('/purchases')
        
    cursor.execute("""
        SELECT purchases.id, suppliers.company, products.name as product_name, 
               purchases.quantity, purchases.total_cost, purchases.purchase_date 
        FROM purchases
        JOIN suppliers ON purchases.supplier_id = suppliers.id
        JOIN products ON purchases.product_id = products.id
        ORDER BY purchases.id DESC
    """)
    all_purchases = cursor.fetchall()
    
    cursor.execute("SELECT id, company FROM suppliers")
    supplier_list = cursor.fetchall()
    
    cursor.execute("SELECT id, name FROM products")
    product_list = cursor.fetchall()
    
    return render_template('purchases.html', purchases=all_purchases, suppliers=supplier_list, products=product_list, role=session['role'])

# 18.Delete Product
@app.route('/delete_product/<int:id>')
def delete_product(id):
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin', 'Manager']:
        return redirect('/product')
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM products WHERE id = %s", (id,))
        db.commit()
        flash("Product deleted successfully.", "success")
    except:
        flash("Cannot delete product: It is linked to existing sales or purchases.", "danger")
    return redirect('/products')

# 19.Delete Sale (Restores Inventory!)
@app.route('/delete_sale/<int:id>')
def delete_sale(id):
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin', 'Manager']:
        return redirect('/sales')
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT product_id, quantity FROM sales WHERE id = %s", (id,))
    sale = cursor.fetchone()
    if sale:

        cursor.execute("UPDATE products SET current_stock = current_stock + %s WHERE id = %s", (sale['quantity'], sale['product_id']))
        cursor.execute("DELETE FROM sales WHERE id = %s", (id,))
        db.commit()
        flash("Sale deleted and inventory stock restored.", "success")
    return redirect('/sales')

# 20.Update User Password (Admin Only)
@app.route('/edit_user_password', methods=['POST'])
def edit_user_password():
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin']:
        return redirect('/users')
    user_id = request.form['id']
    new_password = request.form['password']
    hashed_pw = generate_password_hash(new_password)
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_pw, user_id))
    db.commit()
    flash("User password updated successfully!", "success")
    return redirect('/users')

# 21. Edit Supplier
@app.route('/edit_supplier', methods=['POST'])
def edit_supplier():
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin', 'Purchase']:
        return redirect('/suppliers')
    s_id = request.form['id']
    name = request.form['name']
    company = request.form['company']
    phone = request.form['phone']
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE suppliers SET name=%s, company=%s, phone=%s WHERE id=%s", (name, company, phone, s_id))
    db.commit()
    flash("Supplier updated successfully!", "success")
    return redirect('/suppliers')

# 22. Edit Purchase
@app.route('/edit_purchase', methods=['POST'])
def edit_purchase():
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin', 'Purchase', 'Store']:
        return redirect('/purchases')
    p_id = request.form['id']
    new_qty = int(request.form['quantity'])
    new_cost = request.form['total_cost']
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT product_id, quantity FROM purchases WHERE id = %s", (p_id,))
    old_purchase = cursor.fetchone()
    if old_purchase:
        diff = new_qty - old_purchase['quantity']
        cursor.execute("UPDATE products SET current_stock = current_stock + %s WHERE id = %s", (diff, old_purchase['product_id']))
        cursor.execute("UPDATE purchases SET quantity=%s, total_cost=%s WHERE id=%s", (new_qty, new_cost, p_id))
        db.commit()
        flash("Purchase updated and inventory adjusted!", "success")
    return redirect('/purchases')

# 23. Delete Purchase
@app.route('/delete_purchase/<int:id>')
def delete_purchase(id):
    if 'loggedin' not in session or session.get('role') not in ['SuperAdmin', 'Admin', 'Purchase', 'Store']:
        return redirect('/purchases')
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT product_id, quantity FROM purchases WHERE id = %s", (id,))
    purchase = cursor.fetchone()
    if purchase:

        cursor.execute("UPDATE products SET current_stock = current_stock - %s WHERE id = %s", (purchase['quantity'], purchase['product_id']))
        cursor.execute("DELETE FROM purchases WHERE id = %s", (id,))
        db.commit()
        flash("Purchase deleted and inventory reduced.", "success")
    return redirect('/purchases')

if __name__ == "__main__":
    app.run(debug=True)