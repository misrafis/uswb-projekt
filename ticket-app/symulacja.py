import asyncio
import aiohttp
import time

URL = "http://localhost:5000/api/internal/simulate_purchase"
NUM_REQUESTS = 90000

async def send_request(session, i):
    """Wysyła pojedyncze żądanie zakupu."""
    payload = {
        'user_id': 1,
        'concert_id': 4,
        'quantity': 1
    }
    try:
        async with session.post(URL, json=payload) as response:
            if response.status == 202:
                if i % 1000 == 0:
                    print(f"Żądanie {i}: Sukces - w kolejce")
            else:
                print(f"Żądanie {i}: Błąd - {await response.text()}")
                
    except Exception as e:
        print(f"Żądanie {i}: Wyjątek - {e}")

async def main():
    """Główna funkcja uruchamiająca symulację."""
    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [send_request(session, i) for i in range(NUM_REQUESTS)]
        await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    print(f"\nZakończono! Wysłano {NUM_REQUESTS} żądań w {duration:.2f} sekund.")
    print(f"Średnio {NUM_REQUESTS/duration:.2f} żądań/sekundę.")

if __name__ == '__main__':
    asyncio.run(main())