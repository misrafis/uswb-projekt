CREATE TYPE order_status AS ENUM ('w kolejce', 'zrealizowane', 'nieudane');

CREATE TABLE concerts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    total_tickets INT NOT NULL,
    available_tickets INT NOT NULL
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, password_hash) VALUES ('simulation_user', '---');

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    concert_id INT NOT NULL,
    quantity INT NOT NULL,
    status order_status NOT NULL,
    initial_queue_position INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (concert_id) REFERENCES concerts(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

INSERT INTO concerts (name, total_tickets, available_tickets) VALUES
('Koncert Rockowy - Zespół Tytani', 5000, 5000),
('Festiwal Jazzowy - Letnie Brzmienia', 1500, 1500),
('Występ Akustyczny - Solo Artystka', 100, 100),
('Mega Festiwal na Stadionie Narodowym', 100000, 100000);

CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_initial_queue_position ON orders(initial_queue_position);