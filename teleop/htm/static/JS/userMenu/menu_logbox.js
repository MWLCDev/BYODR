const apiUrl = 'api/datalog/event/v10/table';

// will make these values dynamic later, depending on the 45 doc and what data to show or sort
let drawCount = 1; // Initialize draw count
let start = 0; // Starting point in the dataset
let length = 10; // Number of records per page. Greater length will take longer to load
let orderDir = 'desc'; // Default sorting order
let currentPage = 1;
let totalRecords = 0;
let pagesAmount = 1;
//TODO: handle image showing

export function initLogbox(){
	fetchData();
	getSelect();
	getButtons(totalRecords, currentPage, pagesAmount);
}

function getButtons(totalRecords, currentPage, pag){
	const bDots = document.getElementById('bdots');
	bDots.style.display = 'none';
	const buttonContainer = document.getElementById('varpag');
	if (pagesAmount>1){
		for (var i=1; i<pagesAmount && i<3; i++){
			const newBtn = document.createElement('button');
			newBtn.id = 'nrbtn';
			newBtn.className = 'logbox';
			newBtn.textContent = i+1;
			buttonContainer.appendChild(newBtn);
		}
	}
	console.log(pagesAmount, 'pages before clickbuttons')
	clickButtons(pagesAmount)
}

function clickButtons(pages){
	const prevBtn = document.getElementById('prevBtn');
	const nextBtn = document.getElementById('nextBtn');
	const firstBtn = document.getElementById('firstBtn');
	const lastBtn = document.getElementById('lastBtn');
	const varpag = document.getElementById('varpag');

	prevBtn.addEventListener('click', function() {
		if (currentPage > 1){
			currentPage--;
			console.log('prev page')

		}
		changePage();
	});

	nextBtn.addEventListener('click', function(){
		console.log(currentPage, pages)
		if (currentPage < pages){
			currentPage++;
		}
		changePage();
	});

	firstBtn.addEventListener('click', function(){
		currentPage = 1;
		changePage();
	});

	lastBtn.addEventListener('click', function(){
		currentPage = pages;
		changePage();
	});
}

function changePage(){
	console.log(currentPage)
}

function getSelect(){
	const selectElement = document.getElementById('mySelect');
	selectElement.addEventListener('change', function() {
		const selectedValue = selectElement.value;
		length = Number(selectedValue);
		fetchData();
	});
}

function fetchData() {

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
			totalRecords = data.recordsTotal;
			displayNumbers(start, length, totalRecords);
			processData(data.data, data.draw); // Ensure draw from server matches the expected draw
		})
		.catch((error) => console.error('Error loading the data:', error));
}

function isStringNumber(str) {
	return !isNaN(Number(str));
}

function roundIfMoreThanTwoDecimals(number) {
    // Convert the number to a string and split it by the decimal point
    let [integerPart, decimalPart] = number.toString().split(".");

    // Check if there is a decimal part and if its length is greater than 2
    if (decimalPart && decimalPart.length > 3) {
        // Round the number to 2 decimal places
        return parseFloat(number).toFixed(3);
    }
    
    // Return the original number if it has 2 or fewer decimal places
    return number;
}

function displayNumbers(start, length, totalRecords){
	const maxNr = document.getElementById('max_nr');
	maxNr.textContent = totalRecords;
	const fromNr = document.getElementById('from_nr');
	fromNr.textContent = start;
	const toNr = document.getElementById('to_nr');
	toNr.textContent = start + length;
	const lastBtn = document.getElementById('lastBtn');
	pagesAmount = Math.ceil(totalRecords / length);
	lastBtn.textContent = pagesAmount;
	console.log('pages amount changed to', pagesAmount)
}

function processData(data, serverDraw) {
	if (serverDraw !== drawCount - 1) {
		console.warn('Received out of sync data');
		return; // Handling out of sync response.
	}

	const tableBody = document.querySelector('.logbox tbody');
	tableBody.innerHTML = ''; // Clear existing rows
	data.forEach((row) => {
		const tr = document.createElement('tr');
		tr.innerHTML = row
			.map((item, index) => {
				// Handling 'null' and numeric conversions explicitly for proper display

				if (item === 'null' || item === null) return '<td></td>'; // Render empty cell for null values
				if (isStringNumber(item) == true){
					return `<td>${roundIfMoreThanTwoDecimals(item)}</td>`; // Format numbers
				}
				return `<td>${item}</td>`; // Default rendering
			})
			.join('');

		tableBody.appendChild(tr);
	});
}
