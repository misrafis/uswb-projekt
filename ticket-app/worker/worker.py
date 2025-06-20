import pika
import time
import json
import os
import psycopg2
from psycopg2 import OperationalError
import sys
import traceback

# --- Stałe konfiguracyjne ---
RABBITMQ_HOST = 'rabbitmq'
RABBITMQ_QUEUE = 'purchase_queue'
DB_HOST = os.getenv('POSTGRES_HOST')
DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')

# --- Funkcje pomocnicze ---
def get_db_connection():
    """Nawiązuje połączenie z bazą danych PostgreSQL z logiką ponawiania."""
    while True:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS
            )
            sys.stdout.write("Worker: Połączenie z bazą danych udane.\n")
            sys.stdout.flush()
            return conn
        except OperationalError as e:
            sys.stderr.write(f"Worker: Błąd połączenia z bazą: {e}. Próbuję ponownie za 5 sekund...\n")
            sys.stderr.flush()
            time.sleep(5)

# --- Główna logika workera ---
def process_purchase(ch, method, properties, body):
    """Przetwarza pojedynczą wiadomość zakupu z kolejki."""
    message = json.loads(body)
    sys.stdout.write(f" [x] Otrzymano zadanie dla zamówienia: {message.get('order_id')}\n")
    sys.stdout.flush()
    
    time.sleep(0.05) 

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            order_id = message['order_id']
            concert_id = message['concert_id']
            quantity = message['quantity']
            
            cur.execute("SELECT available_tickets FROM concerts WHERE id = %s FOR UPDATE", (concert_id,))
            result = cur.fetchone()

            if result is None:
                sys.stdout.write(f" [!] Błąd: Koncert o ID {concert_id} nie istnieje. Odrzucam wiadomość.\n")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            available_tickets = result[0]

            if available_tickets >= quantity:
                new_available_tickets = available_tickets - quantity
                cur.execute("UPDATE concerts SET available_tickets = %s WHERE id = %s", (new_available_tickets, concert_id))
                cur.execute("UPDATE orders SET status = %s WHERE id = %s", ('zrealizowane', order_id))
                sys.stdout.write(f" [✔] Zamówienie {order_id} zrealizowane.\n")
            else:
                cur.execute("UPDATE orders SET status = %s WHERE id = %s", ('nieudane', order_id))
                sys.stdout.write(f" [!] Zamówienie {order_id} nieudane: brak biletów.\n")
            
            conn.commit()
            sys.stdout.flush()

            ch.basic_ack(delivery_tag=method.delivery_tag)
            sys.stdout.write(f" [ack] Potwierdzono przetworzenie zamówienia {order_id}.\n")
            sys.stdout.flush()

    except Exception as e:
        sys.stderr.write(f"--- KRYTYCZNY BŁĄD W WORKERZE DLA ZAMÓWIENIA {message.get('order_id')} ---\n")
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# --- Główna pętla startowa workera ---
def main():
    print(' [*] Worker startuje. Oczekiwanie na połączenie z RabbitMQ...')
    
    connection = None
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            channel = connection.channel()
            channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=process_purchase)
            
            print(' [*] Połączono z RabbitMQ. Oczekiwanie na wiadomości.')
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            print(f"Nie można połączyć się z RabbitMQ: {e}. Próbuję ponownie za 5 sekund...")
            time.sleep(5)
        except KeyboardInterrupt:
            print('Zatrzymano.')
            if connection and connection.is_open:
                connection.close()
            break

if __name__ == '__main__':
    main()