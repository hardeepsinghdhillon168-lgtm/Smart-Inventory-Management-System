CREATE DATABASE IF NOT EXISTS smart_inventory;
USE smart_inventory;

-- 1. Users Table 
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('SuperAdmin', 'Admin', 'Manager', 'Staff', 'Purchase', 'Store') DEFAULT 'Staff',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Categories Table
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- 3. Products Table
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    current_stock INT DEFAULT 0,
    min_stock_level INT DEFAULT 10,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- 4. Sales Table
CREATE TABLE sales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    quantity INT NOT NULL,
    sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 5. Suppliers Table
CREATE TABLE suppliers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    company VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL
);

-- 6. Purchase Table
CREATE TABLE purchase (
    id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_id INT,
    product_id INT,
    quantity INT NOT NULL,
    total_cost DECIMAL(10,2) NOT NULL,
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 7. Stock Alerts Table
CREATE TABLE stock_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    message VARCHAR(255),
    is_read BOOLEAN DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 8. The Trigger for Low Stock
DELIMITER //
CREATE TRIGGER low_stock_trigger
AFTER UPDATE ON products
FOR EACH ROW
BEGIN
    IF NEW.current_stock <= NEW.min_stock_level AND OLD.current_stock > NEW.min_stock_level THEN
        INSERT INTO stock_alerts (product_id, message) 
        VALUES (NEW.id, CONCAT('Low Stock Alert: ', NEW.name));
    END IF;
END;
//
DELIMITER ;

-- 9. Default Super Admin account (Password is 'admin123')
INSERT INTO users (name, email, password, role) 
VALUES ('Super Admin', 'admin@system.com', 'scrypt:32768:8:1$x8sT9...dummyhash', 'SuperAdmin');