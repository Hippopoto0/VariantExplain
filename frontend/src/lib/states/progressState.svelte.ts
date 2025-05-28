import type { StatusPollResponseStatus} from "../../clients/clients"

type ProgressStateType = {
    status: StatusPollResponseStatus
}

let progressState: ProgressStateType = $state({status: "idle"});

const setProgressState = (state: StatusPollResponseStatus) => {
    progressState.status = state;
}

export {progressState, setProgressState}