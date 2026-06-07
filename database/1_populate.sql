-- Initialize Sales Database Schema
USE sales;

-- Create items table for products
CREATE TABLE IF NOT EXISTS items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    available INT NOT NULL DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_available (available)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert trial smartphone data
INSERT INTO items (name, price, available, timestamp) VALUES
    ('iPhone 15 Pro', 999.99, 50, NOW()),
    ('iPhone 15', 799.99, 75, NOW()),
    ('Samsung Galaxy S24 Ultra', 1299.99, 30, NOW()),
    ('Samsung Galaxy S24', 899.99, 60, NOW()),
    ('Google Pixel 9 Pro', 1099.99, 45, NOW()),
    ('Google Pixel 9', 799.99, 55, NOW()),
    ('iPhone 12', 649.99, 40, NOW()),
    ('Google Pixel 9a', 499.99, 35, NOW()),
    ('Motorola Edge 50 Pro', 749.99, 50, NOW()),
    ('Nothing Phone 2a', 449.99, 0, NOW());

-- Verify data insertion
SELECT COUNT(*) as total_items FROM items;
