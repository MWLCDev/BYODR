class LogBox {
	constructor() {
		this.apiUrl = 'api/datalog/event/v10/table';
		this.drawCount = 1; // Starting point in the dataset
		this.start = 0;
		this.length = 10; // Number of records per page. Greater length will take longer to load
		this.orderDir = 'desc'; // Default sorting order
		this.currentPage = 1;
		this.pagesAmount = 1;
		this.totalRecords = 0;

		//TODO: handle image showing
		this.elements = {
			startDots: document.getElementById('startDots'),
			first_btn: document.getElementById('first_btn'),
			prevBtn: document.getElementById('prevBtn'),
			nextBtn: document.getElementById('nextBtn'),
			last_btn: document.getElementById('last_btn'),
			endDots: document.getElementById('endDots'),
			pagination: document.getElementById('pagination'),
			varpag: document.getElementById('varpag'),
			selectElement: document.getElementById('mySelect'),
			tableBody: document.getElementById('table_order'),
			fromNr: document.getElementById('from_nr'),
			toNr: document.getElementById('to_nr'),
			maxNr: document.getElementById('max_nr'),
		};
	}

	init() {
		this.fetchData();
		this.setupEventListeners();
		this.updateButtonVisibility();
	}

	setupEventListeners() {
		this.elements.pagination.addEventListener('click', (event) => this.handlePaginationClick(event));
		this.elements.selectElement.addEventListener('change', () => this.handleSelectChange());
	}

	handlePaginationClick(event) {
		if (event.target.nodeName !== 'BUTTON') return;
		this.clickButtons(event.target);
	}
	/**
	 * Handles changes in the entries per page select element.
	 */
	handleSelectChange() {
		this.length = Number(this.elements.selectElement.value);
		this.start = 0;
		this.currentPage = 1;
		this.fetchData();
	}

	/**
	 * Processes clicks on pagination buttons and updates the current page.
	 * @param {HTMLButtonElement} clickedBtn - The clicked button element.
	 */
	clickButtons(clickedBtn) {
		const clickedId = clickedBtn.id;
		switch (clickedId) {
			case 'prevBtn':
				if (this.currentPage > 1) this.currentPage--;
				break;
			case 'nextBtn':
				if (this.currentPage < this.pagesAmount) this.currentPage++;
				break;
			case 'first_btn':
				this.currentPage = 1;
				break;
			case 'last_btn':
				this.currentPage = this.pagesAmount;
				break;
			default:
				this.currentPage = Number(clickedBtn.textContent);
				break;
		}
		this.changePage();
	}

	/**
	 * Updates the start index based on the current page and fetches new data.
	 */
	changePage() {
		this.start = (this.currentPage - 1) * this.length;
		this.fetchData();
	}

	/**
	 * Updates the visibility of pagination buttons based on the current page.
	 */
	updateButtonVisibility() {
		const { prevBtn, nextBtn, startDots, first_btn, endDots, last_btn } = this.elements;

		prevBtn.classList.toggle('limit', this.currentPage <= 1);
		nextBtn.classList.toggle('limit', this.currentPage >= this.pagesAmount);

		const showStartButtons = this.currentPage > 3;
		startDots.style.display = showStartButtons ? 'inline' : 'none';
		first_btn.style.display = showStartButtons ? 'inline' : 'none';

		const showEndButtons = this.currentPage < this.pagesAmount - 2;
		endDots.style.display = showEndButtons ? 'inline' : 'none';
		last_btn.style.display = showEndButtons ? 'inline' : 'none';
	}

	/**
	 * Generates and displays pagination buttons.
	 */
	getButtons() {
		const buttonContainer = this.elements.varpag;
		buttonContainer.innerHTML = '';
		if (this.pagesAmount >= 1) {
			for (let i = 0; i < 5 && i < this.pagesAmount; i++) {
				const buttonNr = this.currentPage + i - 2;
				if (buttonNr >= 1 && buttonNr <= this.pagesAmount) {
					const newBtn = document.createElement('button');
					newBtn.id = i - 2;
					newBtn.className = 'logbox nrbtn';
					newBtn.textContent = buttonNr;
					buttonContainer.appendChild(newBtn);
				}
			}
		}
	}

	fetchData() {
		const params = new URLSearchParams({
			draw: this.drawCount++,
			start: this.start,
			length: this.length,
			'order[0][dir]': this.orderDir,
		});

		fetch(`${this.apiUrl}?${params.toString()}`)
			.then((response) => response.json())
			.then((data) => this.handleFetchResponse(data))
			.catch((error) => console.error('Error loading the data:', error));
	}

	/**
	 * Handles the API response, updating the table and pagination.
	 * @param {Object} data - The data returned from the API.
	 */
	handleFetchResponse(data) {
		if (data.error) {
			console.error('Error from server:', data.error);
			return;
		}
		this.totalRecords = data.recordsTotal;
		this.displayNumbers();
		this.processData(data.data, data.draw);
		this.getButtons();
		this.updateButtonVisibility();
		this.updateCurrentButton();
	}

	/**
	 * Updates the display of record numbers and calculates total pages.
	 */
	displayNumbers() {
		try {
			this.elements.maxNr.textContent = this.totalRecords;
			this.elements.fromNr.textContent = this.start + 1;
			this.elements.toNr.textContent = Math.min(this.start + this.length, this.totalRecords);
			this.pagesAmount = Math.ceil(this.totalRecords / this.length);
			this.elements.last_btn.textContent = this.pagesAmount;
		} catch (error) {
			console.log('cannot display the numbers');
		}
	}

	/**
	 * Processes and displays the fetched data in the table.
	 * @param {Array} data - The array of data to be displayed.
	 * @param {number} serverDraw - The draw count from the server.
	 */
	processData(data, serverDraw) {
		try {
			if (serverDraw !== this.drawCount - 1) {
				console.warn('Received out of sync data');
				return;
			}

			this.elements.tableBody.innerHTML = '';
			data.forEach((row) => {
				const tr = document.createElement('tr');
				// Use an arrow function here to preserve 'this' context
				tr.innerHTML = row.map((item, index) => this.formatCell(item, index)).join('');
				this.elements.tableBody.appendChild(tr);
			});
		} catch (error) {
			console.error("Couldn't process server data", error);
		}
	}
	/**
	 * Formats a cell's content for display in the table.
	 * @param {*} item - The item to be formatted.
	 * @param {number} columnIndex - The index of the column.
	 * @returns {string} The HTML string for the formatted cell.
	 */
	formatCell(item, columnIndex) {
		if (item === 'null' || item === null) return '<td></td>';

		// Check if this is the Timestamp column (assuming it's the second column, index 1)
		if (columnIndex === 1) {
			return `<td>${this.formatTimestamp(item)}</td>`;
		}

		if (LogBox.isStringNumber(item)) {
			return `<td>${LogBox.roundIfMoreThanTwoDecimals(item)}</td>`;
		}
		return `<td>${item}</td>`;
	}

	/**
	 * Formats a timestamp from microseconds to the desired string format.
	 * @param {string} timestamp - The timestamp in microseconds.
	 * @returns {string} The formatted date string.
	 */
	formatTimestamp(timestamp) {
		const date = new Date(parseInt(timestamp) / 1000); // Convert microseconds to milliseconds

		const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
		const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

		const dayName = days[date.getDay()];
		const day = date.getDate();
		const monthName = months[date.getMonth()];
		const year = date.getFullYear();
		const hours = date.getHours().toString().padStart(2, '0');
		const minutes = date.getMinutes().toString().padStart(2, '0');
		const seconds = date.getSeconds().toString().padStart(2, '0');
		const milliseconds = date.getMilliseconds().toString().padStart(3, '0');

		return `${dayName}, ${day}/${monthName}/${year}, ${hours}:${minutes}:${seconds}.${milliseconds}`;
	}
	/**
	 * Updates the current button's visual state in the pagination.
	 */
	updateCurrentButton() {
		const currentBtn = document.querySelector('.currentBtn');
		if (currentBtn) currentBtn.classList.remove('currentBtn');

		document.querySelectorAll('.nrbtn').forEach((btn) => {
			if (this.currentPage == Number(btn.textContent)) {
				btn.classList.add('currentBtn');
			}
		});
	}

	static isStringNumber(str) {
		return !isNaN(Number(str));
	}

	static roundIfMoreThanTwoDecimals(number) {
		const [integerPart, decimalPart] = number.toString().split('.');
		if (decimalPart && decimalPart.length > 3) {
			return parseFloat(number).toFixed(3);
		}
		return number;
	}
}

export { LogBox };
