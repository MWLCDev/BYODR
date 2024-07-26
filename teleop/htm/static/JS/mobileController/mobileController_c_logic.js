import CTRL_STAT from './mobileController_z_state.js';
import { gamepad_socket } from '../Index/index_e_teleop.js';


function setStatistics(x, y, getInferenceState) {
	CTRL_STAT.throttleSteeringJson = {
		throttle: Number(y),
		steering: Number(x),
		mobileInferenceState: getInferenceState,
	};
	gamepad_socket._capture();
}
export { setStatistics };
