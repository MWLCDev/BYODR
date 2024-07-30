const apiUrl = 'api/datalog/event/v10/table';

// will make these values dynamic later, depending on the 45 doc and what data to show or sort
let drawCount = 1; // Initialize draw count
let start = 0; // Starting point in the dataset
let length = 10; // Number of records per page. Greater length will take longer to load
let orderDir = 'desc'; // Default sorting order
//TODO: handle image showing

export function fetchData() {
	const params = new URLSearchParams({
		draw: drawCount++, // Increment and send current draw count
		start: start,
		length: length,
		'order[0][dir]': orderDir,
	}); // Include ordering parameters
	
	fetch(`${apiUrl}?${params.toString()}`)
		.then((response) => response.json())
		.then((data) => {
			if (data.error) {
				console.error('Error from server:', data.error);
				return;
			}
			processData(data.data, data.draw, data.recordsTotal); // Ensure draw from server matches the expected draw
		})
		.catch((error) => console.error('Error loading the data:', error));
}

function processData(data, serverDraw, totalRecords) {
	console.log(data)
	if (serverDraw !== drawCount - 1) {
		console.warn('Received out of sync data');
		return; // Handling out of sync response.
	}
	const tableBody = document.querySelector('#logbox tbody');
	tableBody.innerHTML = ''; // Clear existing rows
	data.forEach((row) => {
		const tr = document.createElement('tr');
		tr.innerHTML = row
			.map((item, index) => {
				// Handling 'null' and numeric conversions explicitly for proper display
				if (item === 'null' || item === null) return '<td></td>'; // Render empty cell for null values
				console.log(typeof item, item)
				if (typeof item === "number"){
					console.log(item.toFixed(2)) 
					return `<td>${item.toFixed(2)}</td>`; // Format numbers

				} 
				return `<td>${item}</td>`; // Default rendering
			})
			.join('');
		tableBody.appendChild(tr);
	});
}
