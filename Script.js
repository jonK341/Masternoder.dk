document.addEventListener('DOMContentLoaded', () => {
    const button = document.getElementById('fetch-data');
    const dataBody = document.getElementById('data-body');
    const loading = document.getElementById('loading');
    const errorMessage = document.getElementById('error-message');

    button.addEventListener('click', async () => {
        dataBody.innerHTML = ''; // Clear previous data
        errorMessage.classList.add('hidden'); // Hide previous error messages
        loading.classList.remove('hidden'); // Show loading message

        const endpoints = [
            { url: 'https://explorer.masternoder.dk/ext/getmoneysupply', label: 'Money Supply' },
            { url: 'https://explorer.masternoder.dk/ext/getnetworkpeers', label: 'Network Peers' },
            { url: 'https://explorer.masternoder.dk/api/getnetworkhashps', label: 'Network Hash Per Second' },
            { url: 'https://explorer.masternoder.dk/api/getmasternodecount', label: 'Masternode Count' },
            { url: 'https://explorer.masternoder.dk/api/getconnectioncount', label: 'Connection Count' }
        ];

        try {
            for (const { url, label } of endpoints) {
                console.log(`Fetching data from: ${url}`); // Debugging log
                const response = await fetch(url);

                // Check if the response is ok
                if (!response.ok) {
                    console.error(`Network response error: ${response.statusText}`);
                    throw new Error(`Failed to fetch from ${url}: ${response.statusText}`);
                }

                const data = await response.json();
                console.log(`Received data for ${label}:`, data); // Debugging log

                // Handle accessing the data based on expected structure
                let value;
                switch (label) {
                    case 'Money Supply':
                        value = data.result; // Update based on actual response
                        break;
                    case 'Network Peers':
                        value = Array.isArray(data.result) ? data.result.length : 'N/A';
                        break;
                    case 'Network Hash Per Second':
                        value = data.result; // Update based on actual response
                        break;
                    case 'Masternode Count':
                        value = data.result; // Update based on actual response
                        break;
                    case 'Connection Count':
                        value = data.result; // Update based on actual response
                        break;
                    default:
                        value = 'N/A';
                }

                // Create a new row for the table
                const newRow = document.createElement('tr');
                newRow.innerHTML = `<td>${label}</td><td>${value !== undefined ? value : 'N/A'}</td>`;
                dataBody.appendChild(newRow);
            }
        } catch (error) {
            console.error('Error fetching data:', error);
            errorMessage.textContent = `Error: ${error.message}`;
            errorMessage.classList.remove('hidden'); // Display error message
        } finally {
            loading.classList.add('hidden'); // Hide loading message
        }
    });
});
