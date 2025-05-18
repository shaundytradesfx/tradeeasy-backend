-- TradeEasy Seed Data
-- Inserts initial data into the database for development and testing

-- Insert demo user (password is 'password' hashed)
INSERT INTO users (username, email, password_hash, created_at)
VALUES
('demo', 'demo@tradeeasy.com',
 '$2b$12$sWSdpNcQrRB2vaggoOQNce6cKDJyFWsABXuIllYR3Ubzw3JvWZIqu',
 CURRENT_TIMESTAMP)
ON CONFLICT (username) DO NOTHING;

-- Insert assets by category
-- Stocks
INSERT INTO assets (symbol, name, type, description)
VALUES
('AAPL', 'Apple Inc.', 'stock', 'Technology company that designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories.'),
('MSFT', 'Microsoft Corporation', 'stock', 'Technology company that develops, licenses, and supports software, services, devices, and solutions.'),
('AMZN', 'Amazon.com Inc.', 'stock', 'Online retailer and web service provider.'),
('GOOGL', 'Alphabet Inc.', 'stock', 'Technology company specializing in Internet-related services and products.'),
('TSLA', 'Tesla, Inc.', 'stock', 'Electric vehicle and clean energy company.')
ON CONFLICT (symbol) DO NOTHING;

-- Cryptocurrencies
INSERT INTO assets (symbol, name, type, description)
VALUES
('BTC-USD', 'Bitcoin', 'crypto', 'The original cryptocurrency.'),
('ETH-USD', 'Ethereum', 'crypto', 'Blockchain platform with smart contract functionality.'),
('XRP-USD', 'Ripple', 'crypto', 'Digital payment protocol and cryptocurrency.'),
('ADA-USD', 'Cardano', 'crypto', 'Proof-of-stake blockchain platform.'),
('SOL-USD', 'Solana', 'crypto', 'High-performance blockchain supporting smart contracts.')
ON CONFLICT (symbol) DO NOTHING;

-- Forex
INSERT INTO assets (symbol, name, type, description)
VALUES
('EUR-USD', 'Euro/US Dollar', 'forex', 'Currency pair representing the Euro against the US Dollar.'),
('USD-JPY', 'US Dollar/Japanese Yen', 'forex', 'Currency pair representing the US Dollar against the Japanese Yen.'),
('GBP-USD', 'British Pound/US Dollar', 'forex', 'Currency pair representing the British Pound against the US Dollar.'),
('USD-CHF', 'US Dollar/Swiss Franc', 'forex', 'Currency pair representing the US Dollar against the Swiss Franc.'),
('AUD-USD', 'Australian Dollar/US Dollar', 'forex', 'Currency pair representing the Australian Dollar against the US Dollar.')
ON CONFLICT (symbol) DO NOTHING;

-- Commodities
INSERT INTO assets (symbol, name, type, description)
VALUES
('GC=F', 'Gold', 'commodity', 'Precious metal used as a store of value and in jewelry.'),
('SI=F', 'Silver', 'commodity', 'Precious metal used in industry and as a store of value.'),
('CL=F', 'Crude Oil', 'commodity', 'Fossil fuel used for energy production.'),
('NG=F', 'Natural Gas', 'commodity', 'Fossil fuel used for heating and electricity generation.'),
('HG=F', 'Copper', 'commodity', 'Industrial metal used in construction and electronics.')
ON CONFLICT (symbol) DO NOTHING;

-- Create sample watchlist entries for demo user
DO $$
DECLARE
    demo_user_id UUID;
BEGIN
    SELECT id INTO demo_user_id FROM users WHERE username = 'demo';

    IF demo_user_id IS NOT NULL THEN
        -- Add some assets to demo user's watchlist
        INSERT INTO watchlists (user_id, asset_id, created_at)
        SELECT demo_user_id, id, CURRENT_TIMESTAMP
        FROM assets
        WHERE symbol IN ('AAPL', 'MSFT', 'BTC-USD', 'ETH-USD', 'GC=F')
        ON CONFLICT (user_id, asset_id) DO NOTHING;

        -- Create some alerts for demo user
        INSERT INTO alerts (user_id, asset_id, threshold, direction, created_at, is_active)
        SELECT
            demo_user_id,
            id,
            CASE
                WHEN type = 'stock' THEN 0.05
                WHEN type = 'crypto' THEN 0.1
                ELSE 0.03
            END,
            'above',
            CURRENT_TIMESTAMP,
            TRUE
        FROM assets
        WHERE symbol IN ('AAPL', 'BTC-USD', 'EUR-USD')
        ON CONFLICT DO NOTHING;
    END IF;
END $$;
