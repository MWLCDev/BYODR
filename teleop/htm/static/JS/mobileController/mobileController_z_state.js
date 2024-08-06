//Shared State variables that goes between the files/modules used
class MobileControllerState {
	#selectedSquare = null;
	#followingState = null;
	// At first we send a default value
	#mobileCommandJSON = { steering: 0, throttle: 0 };
	#mobileIsActive;
	#currentPage;
	#stateErrors;
	#ws;

	set mobileIsActive(value) {
		this.#mobileIsActive = value;
	}
	get mobileIsActive() {
		return this.#mobileIsActive;
	}
	set currentPage(value) {
		this.#currentPage = value;
	}
	get currentPage() {
		return this.#currentPage;
	}

	set selectedSquare(value) {
		this.#selectedSquare = value;
	}
	get selectedSquare() {
		return this.#selectedSquare;
	}

	set mobileCommandJSON(value) {
		this.#mobileCommandJSON = value;
	}
	get mobileCommandJSON() {
		return this.#mobileCommandJSON;
	}

	set stateErrors(value) {
		if (this.#stateErrors != value) {
			this.#stateErrors = value;
		}
	}
	get stateErrors() {
		return this.#stateErrors;
	}

	set websocket(value) {
		this.#ws = value;
	}
	get websocket() {
		return this.#ws;
	}

	set followingState(value) {
		this.#followingState = value;
	}
	get followingState() {
		return this.#followingState;
	}
}

const sharedState = new MobileControllerState();

// Shared instance will make sure that all the imports can access the same value without change in them
export default sharedState;
