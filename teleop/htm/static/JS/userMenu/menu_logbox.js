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
			firstBtn: document.getElementById('firstBtn'),
			prevBtn: document.getElementById('prevBtn'),
			nextBtn: document.getElementById('nextBtn'),
			lastBtn: document.getElementById('lastBtn'),
			endDots: document.getElementById('endDots'),
			pagination: document.getElementById('pagination'),
			varpag: document.getElementById('varpag'),
			selectElement: document.getElementById('mySelect'),
			tableBody: document.querySelector('.logbox tbody'),
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
			case 'firstBtn':
				this.currentPage = 1;
				break;
			case 'lastBtn':
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
		const { prevBtn, nextBtn, startDots, firstBtn, endDots, lastBtn } = this.elements;

		prevBtn.classList.toggle('limit', this.currentPage <= 1);
		nextBtn.classList.toggle('limit', this.currentPage >= this.pagesAmount);

		const showStartButtons = this.currentPage > 3;
		startDots.style.display = showStartButtons ? 'inline' : 'none';
		firstBtn.style.display = showStartButtons ? 'inline' : 'none';

		const showEndButtons = this.currentPage < this.pagesAmount - 2;
		endDots.style.display = showEndButtons ? 'inline' : 'none';
		lastBtn.style.display = showEndButtons ? 'inline' : 'none';
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
		this.elements.maxNr.textContent = this.totalRecords;
		this.elements.fromNr.textContent = this.start + 1;
		this.elements.toNr.textContent = Math.min(this.start + this.length, this.totalRecords);
		this.pagesAmount = Math.ceil(this.totalRecords / this.length);
		this.elements.lastBtn.textContent = this.pagesAmount;
	}

	/**
	 * Processes and displays the fetched data in the table.
	 * @param {Array} data - The array of data to be displayed.
	 * @param {number} serverDraw - The draw count from the server.
	 */
	processData(data, serverDraw) {
		if (serverDraw !== this.drawCount - 1) {
			console.warn('Received out of sync data');
			return;
		}

		this.elements.tableBody.innerHTML = '';
		data.forEach((row) => {
			const tr = document.createElement('tr');
			tr.innerHTML = row.map(this.formatCell).join('');
			this.elements.tableBody.appendChild(tr);
		});
	}

	formatCell(item) {
		if (item === 'null' || item === null) return '<td></td>';
		if (LogBox.isStringNumber(item)) {
			return `<td>${LogBox.roundIfMoreThanTwoDecimals(item)}</td>`;
		}
		return `<td>${item}</td>`;
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
