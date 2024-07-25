//Shared State variables that goes between the files/modules used
class MobileControllerState {
	#selectedTriangle = null;
	// Hold the current value for steering and throttle to be sent through the websocket
	// At first we send a default value
	#throttleSteeringJson = { steering: 0, throttle: 0 };
	//stands for WebSocket
	#ws;
	#stateErrors;

	set selectedTriangle(value) {
		this.#selectedTriangle = value;
	}
	get selectedTriangle() {
		return this.#selectedTriangle;
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
