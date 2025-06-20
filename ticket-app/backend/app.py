import os
import pika
import json
import psycopg2
import time
import sys
import traceback
from psycopg2 import OperationalError
from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager

app = Flask(__name__)

# --- Konfiguracja ---
app.config["JWT_SECRET_KEY"] = "twoj-super-tajny-klucz-jwt"
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Dane do połączeń
RABBITMQ_HOST = 'rabbitmq'
RABBITMQ_QUEUE = 'purchase_queue'
DB_HOST = os.getenv('POSTGRES_HOST')
DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')

def get_db_connection():
    """
    Nawiązuje połączenie z bazą danych PostgreSQL.
    Zaimplementowano pętlę ponawiającą, aby dać bazie czas na start.
    """
    while True:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS
            )
            print("Backend: Połączenie z bazą danych udane.")
            return conn
        except OperationalError as e:
            print(f"Backend: Błąd połączenia z bazą: {e}. Próbuję ponownie za 2 sekundy...")
            time.sleep(2)

# --- Endpointy Autoryzacji ---

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Nazwa użytkownika i hasło są wymagane"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        return jsonify({"message": "Użytkownik zarejestrowany pomyślnie"}), 201
    except psycopg2.IntegrityError:
        if conn: conn.rollback()
        return jsonify({"message": "Użytkownik o tej nazwie już istnieje"}), 409
    except Exception as e:
        if conn: conn.rollback()
        print("--- KRYTYCZNY BŁĄD W ENDPOINCIE /api/auth/register ---", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        return jsonify({"message": "Wystąpił wewnętrzny błąd serwera"}), 500
    finally:
        if conn:
            cur.close()
            conn.close()


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Nazwa użytkownika i hasło są wymagane"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, password_hash FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user and bcrypt.check_password_hash(user[1], password):
        access_token = create_access_token(identity=str(user[0]))
        return jsonify(access_token=access_token)

    return jsonify({"message": "Nieprawidłowa nazwa użytkownika lub hasło"}), 401

# --- Endpoint Zakupu ---

@app.route('/api/purchase', methods=['POST'])
@jwt_required()
def purchase():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    concert_id = data.get('concert_id')
    quantity = data.get('quantity')

    if not concert_id or not quantity:
        return jsonify({"message": "ID koncertu i ilość są wymagane"}), 400
    
    conn = None
    new_order_id = None
    try:
        rabbit_conn = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = rabbit_conn.channel()
        queue_state = channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True, passive=True)
        message_count = queue_state.method.message_count
        initial_position = message_count + 1

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders (user_id, concert_id, quantity, status, initial_queue_position) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (current_user_id, concert_id, quantity, 'w kolejce', initial_position)
            )
            new_order_id = cur.fetchone()[0]
            conn.commit()

        body = { 'order_id': new_order_id, 'user_id': current_user_id, 'concert_id': concert_id, 'quantity': quantity }
        channel.basic_publish(exchange='', routing_key=RABBITMQ_QUEUE, body=json.dumps(body), properties=pika.BasicProperties(delivery_mode=2))
        rabbit_conn.close()
        
        print(f"Opublikowano wiadomość dla zamówienia ID {new_order_id}. Pozycja w kolejce: {initial_position}")
        
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        queue_state = channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        message_count = queue_state.method.message_count

        body = { 'order_id': new_order_id, 'user_id': current_user_id, 'concert_id': concert_id, 'quantity': quantity }

        channel.basic_publish(
            exchange='',
            routing_key=RABBITMQ_QUEUE,
            body=json.dumps(body),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        
        print(f"Opublikowano wiadomość dla zamówienia ID {new_order_id}. Czekających w kolejce: {message_count}")

        return jsonify({
            "status": "queued", 
            "message": "Twoje zamówienie zostało przyjęte do realizacji.",
            "order_id": new_order_id,
            "queue_position": initial_position
        }), 202

    except Exception as e:
        if conn: conn.rollback()
        print(f"Wystąpił krytyczny błąd podczas zakupu: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return jsonify({"status": "error", "message": "Wystąpił wewnętrzny błąd serwera."}), 500
    finally:
        if conn: conn.close()


@app.route('/api/internal/simulate_purchase', methods=['POST'])
def simulate_purchase():
    data = request.get_json()
    user_id = data.get('user_id', 'simulation-user')
    concert_id = data.get('concert_id')
    quantity = data.get('quantity')

    if not concert_id or not quantity:
        return jsonify({"message": "ID koncertu i ilość są wymagane"}), 400

    conn = None
    new_order_id = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders (user_id, concert_id, quantity, status) VALUES (%s, %s, %s, %s) RETURNING id",
                (user_id, concert_id, quantity, 'w kolejce')
            )
            new_order_id = cur.fetchone()[0]
            conn.commit()
        
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        queue_state = channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        message_count = queue_state.method.message_count

        body = { 'order_id': new_order_id, 'user_id': user_id, 'concert_id': concert_id, 'quantity': quantity }

        channel.basic_publish(exchange='', routing_key=RABBITMQ_QUEUE, body=json.dumps(body), properties=pika.BasicProperties(delivery_mode=2))
        connection.close()
        
        return jsonify({"status": "queued", "order_id": new_order_id}), 202
    except Exception as e:
        if conn: conn.rollback()
        print(f"Błąd krytyczny w endpoincie symulacji: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return jsonify({"status": "error", "message": "Wystąpił wewnętrzny błąd serwera."}), 500
    finally:
        if conn: conn.close()


@app.route('/api/concerts', methods=['GET'])
def list_concerts():
    """Zwraca listę wszystkich koncertów z bazy danych."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id, name, available_tickets FROM concerts ORDER BY id")
        concerts_raw = cur.fetchall()

        concerts_list = []
        for row in concerts_raw:
            concerts_list.append({
                "id": row[0],
                "name": row[1],
                "available_tickets": row[2]
            })

        return jsonify(concerts_list)

    except Exception as e:
        print(f"Błąd podczas pobierania koncertów: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return jsonify({"message": "Wystąpił błąd podczas pobierania danych o koncertach"}), 500
    finally:
        if conn:
            cur.close()
            conn.close()


@app.route('/api/orders/status/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order_status(order_id):
    """Zwraca status konkretnego zamówienia."""
    current_user_id = get_jwt_identity()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM orders WHERE id = %s AND user_id = %s", (order_id, current_user_id))
            result = cur.fetchone()
            
            if result:
                return jsonify({"status": result[0]})
            else:
                return jsonify({"message": "Nie znaleziono zamówienia lub brak dostępu"}), 404
    except Exception as e:
        print(f"Błąd podczas sprawdzania statusu zamówienia {order_id}: {e}", file=sys.stderr)
        return jsonify({"message": "Błąd serwera przy sprawdzaniu statusu"}), 500
    finally:
        if conn: conn.close()


@app.route('/api/my-orders', methods=['GET'])
@jwt_required()
def my_orders():
    current_user_id = get_jwt_identity()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            sql_query = """
                SELECT 
                    o.id,                       -- Indeks 0
                    c.name,                     -- Indeks 1
                    o.quantity,                 -- Indeks 2
                    o.status,                   -- Indeks 3
                    o.created_at,               -- Indeks 4
                    o.initial_queue_position,   -- Indeks 5
                    (SELECT COUNT(*) FROM orders o2 
                     WHERE o2.initial_queue_position < o.initial_queue_position 
                     AND o2.status IN ('zrealizowane', 'nieudane')) as processed_before
                FROM orders o
                JOIN concerts c ON o.concert_id = c.id
                WHERE o.user_id = %s
                ORDER BY o.created_at DESC
            """
            cur.execute(sql_query, (current_user_id,))
            
            orders_raw = cur.fetchall()
            orders_list = []
            for row in orders_raw:
                order_data = {
                    "id": row[0],
                    "concert_name": row[1],
                    "quantity": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "initial_queue_position": row[5]
                }

                if order_data["status"] == 'w kolejce' and order_data["initial_queue_position"] is not None:
                    processed_before_me = row[6]
                    people_in_front = (order_data["initial_queue_position"] - 1) - processed_before_me
                    order_data["people_in_front"] = people_in_front if people_in_front >= 0 else 0
                
                orders_list.append(order_data)

            return jsonify(orders_list)

    except Exception as e:
        print(f"Błąd podczas pobierania zamówień dla użytkownika {current_user_id}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return jsonify({"message": "Błąd serwera przy pobieraniu zamówień"}), 500
    finally:
        if conn:
            cur.close()
            conn.close()