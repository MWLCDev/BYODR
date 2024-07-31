//Shared State variables that goes between the files/modules used
class MobileControllerState {
	#mobileIsActive;
	#selectedSquare = null;
	// At first we send a default value
	#throttleSteeringJson = { steering: 0, throttle: 0 };
	#ws;
	#stateErrors;

	set mobileIsActive(value) {
		this.#mobileIsActive = value;
	}
	get mobileIsActive() {
		return this.#mobileIsActive;
	}
  
	set selectedSquare(value) {
		this.#selectedSquare = value;
	}
	get selectedSquare() {
		return this.#selectedSquare;
	}

	set throttleSteeringJson(value) {
		this.#throttleSteeringJson = value;
	}
	get throttleSteeringJson() {
		return this.#throttleSteeringJson;
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
}

const sharedState = new MobileControllerState();

// Shared instance will make sure that all the imports can access the same value without change in them
export default sharedState;
