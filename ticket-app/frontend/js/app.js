const API_URL = '/api';

async function registerUser() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const statusDiv = document.getElementById('status');

    const response = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ username, password })
    });
    const data = await response.json();
    statusDiv.textContent = data.message;
    statusDiv.style.color = response.ok ? 'green' : 'red';
}

async function loginUser() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const statusDiv = document.getElementById('status');

    const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ username, password })
    });

    if (response.ok) {
        const data = await response.json();
        localStorage.setItem('accessToken', data.access_token);
        window.location.href = '/tickets.html';
    } else {
        const data = await response.json();
        statusDiv.textContent = data.message;
        statusDiv.style.color = 'red';
    }
}

async function buyTicket(concertId) {
    const quantityInput = document.getElementById(`quantity-${concertId}`);
    const quantity = parseInt(quantityInput.value, 10);
    const statusDiv = document.getElementById(`status-${concertId}`);
    const token = localStorage.getItem('accessToken');

    if (!token) {
        statusDiv.textContent = "Sesja wygasła, proszę zalogować się ponownie.";
        statusDiv.style.color = 'red';
        return;
    }

    statusDiv.textContent = 'Wysyłanie zamówienia...';
    statusDiv.style.color = 'black';

    try {
        const initialResponse = await fetch(`${API_URL}/purchase`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ concert_id: concertId, quantity: quantity })
        });
        
        const data = await initialResponse.json();
        
        if (!initialResponse.ok) {
            throw new Error(data.message || 'Błąd przy składaniu zamówienia.');
        }

        if (data.queue_position) {
            statusDiv.textContent = `${data.message} Jesteś ~${data.queue_position} w kolejce.`;
        } else {
            statusDiv.textContent = data.message;
        }

        const orderId = data.order_id;
        
        const intervalId = setInterval(async () => {
            try {
                const statusResponse = await fetch(`${API_URL}/orders/status/${orderId}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const statusData = await statusResponse.json();

                if (statusData.status === 'zrealizowane' || statusData.status === 'nieudane') {
                    clearInterval(intervalId);
                    statusDiv.textContent = statusData.status === 'zrealizowane' ? 'Zamówienie zrealizowane! Dziękujemy.' : 'Niestety, bilety zostały wyprzedane.';
                    statusDiv.style.color = statusData.status === 'zrealizowane' ? 'green' : 'red';
                } else {
                }
            } catch (error) {
                clearInterval(intervalId);
                statusDiv.textContent = 'Błąd podczas sprawdzania statusu.';
                statusDiv.style.color = 'red';
            }
        }, 2000); 

    } catch (error) {
        statusDiv.textContent = `Błąd: ${error.message}`;
        statusDiv.style.color = 'red';
    }
}

function logout() {
    localStorage.removeItem('accessToken');
    window.location.href = '/index.html';
}