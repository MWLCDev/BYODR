const apiUrl = 'api/datalog/event/v10/table';

// will make these values dynamic later, depending on the 45 doc and what data to show or sort
let drawCount = 1; // Initialize draw count
let start = 0; // Starting point in the dataset
let length = 10; // Number of records per page. Greater length will take longer to load
let orderDir = 'desc'; // Default sorting order
let currentPage = 1;
let totalRecords = 0; // {AM to MB}: There is no need to have this variable
let pagesAmount = 1;
//TODO: handle image showing

export function initLogBox() {
	fetchData();
	getSelect();
	document.getElementById('startDots').style.display = 'none';
	document.getElementById('firstBtn').style.display = 'none';
	document.getElementById('prevBtn').classList.add('limit');
	// document.getElementById('firstBtn').classList.add('currentBtn');
	document.getElementById('pagination').addEventListener('click',(event) => {
		const isButton = event.target.nodeName === 'BUTTON';
		if (!isButton) {
		  return;
		}
		clickButtons(event.target)
	  })
	}


function getButtons() {
	const buttonContainer = document.getElementById('varpag');
	buttonContainer.innerHTML = ''; // Clear existing buttons
	if (pagesAmount >= 1) {
		for (var i = 0; i < pagesAmount && i < 5; i++) {
			const newBtn = document.createElement('button');
			newBtn.id = i-2;
			newBtn.className = 'logbox nrbtn';
			let buttonNr = currentPage + i - 2;
			if (buttonNr >= 1 && buttonNr <= pagesAmount){
				newBtn.textContent = buttonNr;
				buttonContainer.appendChild(newBtn);
			}
		}
	}
}

function clickButtons(clickedBtn) {
	let clickedId = clickedBtn.id
	switch(clickedId){
		case 'prevBtn':
			if (currentPage > 1) {
			currentPage--;
			}
			break;
		case 'nextBtn':
			if (currentPage < pagesAmount) {
				currentPage++;
			}
			break;
		case 'firstBtn':
			currentPage = 1;
			break;
		case 'lastBtn':
			currentPage = pagesAmount;
			break;
		default:
			currentPage = Number(clickedBtn.textContent)
			break;
	}

	changePage();
}

function showExtraButtons(){
	if (currentPage <= 1){
		document.getElementById('prevBtn').classList.add('limit');
		document.getElementById('nextBtn').classList.remove('limit');
	}
	else if(currentPage >= pagesAmount){
		document.getElementById('nextBtn').classList.add('limit');
		document.getElementById('prevBtn').classList.remove('limit');
	}
	else {
		document.getElementById('nextBtn').classList.remove('limit');
		document.getElementById('prevBtn').classList.remove('limit');
	}

	if (currentPage > 3){
		document.getElementById('startDots').style.display ='inline'
		document.getElementById('firstBtn').style.display ='inline'

	}
	else{
		document.getElementById('startDots').style.display = 'none'
		document.getElementById('firstBtn').style.display ='none'
	}

	if (currentPage < pagesAmount-2){
		document.getElementById('endDots').style.display = 'inline'
		document.getElementById('lastBtn').style.display ='inline'
	}
	else{
		document.getElementById('endDots').style.display = 'none'
		document.getElementById('lastBtn').style.display ='none'
	}
}

function changePage() {
	start = (currentPage-1)*length;
	fetchData();

}

function getSelect() {
	const selectElement = document.getElementById('mySelect');
	selectElement.addEventListener('change', function () {
		const selectedValue = selectElement.value;
		length = Number(selectedValue);
		start = 0;
		currentPage = 1;
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
			getButtons();
			showExtraButtons();

			const currentBtn = document.querySelector('.currentBtn');
			if (currentBtn) {
				currentBtn.classList.remove('currentBtn');
			}
		
			

			document.querySelectorAll('.nrbtn').forEach(function(btn){
				if (currentPage == Number(btn.textContent)){
					btn.classList.add('currentBtn');
				}

			})
		})
		.catch((error) => console.error('Error loading the data:', error));
}

function isStringNumber(str) {
	return !isNaN(Number(str));
}

function roundIfMoreThanTwoDecimals(number) {
	// Convert the number to a string and split it by the decimal point
	let [integerPart, decimalPart] = number.toString().split('.');

	// Check if there is a decimal part and if its length is greater than 2
	if (decimalPart && decimalPart.length > 3) {
		// Round the number to 2 decimal places
		return parseFloat(number).toFixed(3);
	}

	// Return the original number if it has 2 or fewer decimal places
	return number;
}

function displayNumbers(start, length, totalRecords) {
	document.getElementById('max_nr').textContent = totalRecords;
	document.getElementById('from_nr').textContent = start;
	document.getElementById('to_nr').textContent = start + length;
	pagesAmount = Math.ceil(totalRecords / length);
	document.getElementById('lastBtn').textContent = pagesAmount;
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
				if (isStringNumber(item) == true) {
					return `<td>${roundIfMoreThanTwoDecimals(item)}</td>`; // Format numbers
				}
				return `<td>${item}</td>`; // Default rendering
			})
			.join('');

		tableBody.appendChild(tr);
	});
}
