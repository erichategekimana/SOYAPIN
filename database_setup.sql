DROP DATABASE IF EXISTS soyapin_db;
CREATE DATABASE soyapin_db;
\c soyapin_db;


-- Enable pgvector extension for AI/Chatbot capabilities
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION if not exists postgis;


-- 1. IDENTITY & ACCESS
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    role_id INTEGER REFERENCES roles(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone_number VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_addresses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    address_line TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    coordinates POINT, -- Stores longitude and latitude
    is_default BOOLEAN DEFAULT FALSE
);

-- 2. SUPPLY & LOGISTICS
CREATE TABLE vendors (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    business_name VARCHAR(255) NOT NULL,
    tin_number VARCHAR(50),
    location_data TEXT,
    verification_status VARCHAR(50) DEFAULT 'pending',
    bio TEXT
);

CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    assigned_zone VARCHAR(100),
    vehicle_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'available',
    rating_avg DECIMAL(3, 2) DEFAULT 0.0
);

CREATE TABLE agent_payouts (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id),
    amount DECIMAL(12, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    processed_at TIMESTAMP WITH TIME ZONE
);

-- 3. PRODUCT CATALOG & INVENTORY
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_price DECIMAL(12, 2) NOT NULL,
    image_url TEXT,
    nutritional_data JSONB, -- Flexible storage for protein, calories, etc.
    is_published BOOLEAN DEFAULT FALSE
);

CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    quantity_available INTEGER NOT NULL DEFAULT 0,
    restock_threshold INTEGER DEFAULT 5,
    expiry_date DATE,
    batch_number VARCHAR(100)
);

-- 4. SALES & TRANSACTIONS
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    total_amount DECIMAL(12, 2) NOT NULL,
    order_status VARCHAR(50) DEFAULT 'pending',
    shipping_address_id INTEGER REFERENCES user_addresses(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price_at_sale DECIMAL(12, 2) NOT NULL -- Snapshotted price
);

CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    transaction_reference VARCHAR(255) UNIQUE,
    provider_name VARCHAR(50), -- e.g., 'MTN', 'Airtel', 'Equity'
    amount DECIMAL(12, 2) NOT NULL,
    payment_status VARCHAR(50) DEFAULT 'pending',
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 5. FULFILLMENT & FEEDBACK
CREATE TABLE deliveries (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    agent_id INTEGER REFERENCES agents(id),
    delivery_status VARCHAR(50) DEFAULT 'preparing',
    pickup_time TIMESTAMP WITH TIME ZONE,
    actual_delivery_time TIMESTAMP WITH TIME ZONE,
    delivery_fee DECIMAL(10, 2)
);

CREATE TABLE product_reviews (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    product_id INTEGER REFERENCES products(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. HEALTH & AI PERSONALIZATION
CREATE TABLE health_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    dietary_goals TEXT,
    allergies JSONB,
    daily_protein_target INTEGER
);

CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    message_text TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    embedding_vector vector(1536), -- Dimension depends on the AI model (e.g., 1536 for OpenAI)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- INDEXES for performance
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_inventory_product ON inventory(product_id);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_chat_vector ON chat_history USING hnsw (embedding_vector vector_cosine_ops);



grant select on spatial_ref_sys to public;


-- Use PostGIS Geography type for meter-based accuracy
ALTER TABLE agents 
ADD COLUMN current_location GEOGRAPHY(Point, 4326),
ADD COLUMN last_location_update TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Specialized spatial index
CREATE INDEX idx_agents_location_geog ON agents USING GIST(current_location);
