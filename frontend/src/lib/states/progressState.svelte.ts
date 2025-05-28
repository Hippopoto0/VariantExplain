import type { StatusPollResponseProgress, StatusPollResponseStatus } from "../../clients/clients"

type ProgressStateType = {
    status: StatusPollResponseStatus,
    percentage: StatusPollResponseProgress
}

let progressState: ProgressStateType = $state({status: "idle", percentage: 0});

const setProgressState = (state: StatusPollResponseStatus, percentage: StatusPollResponseProgress | null) => {
    progressState.status = state;
    progressState.percentage = percentage ? percentage : 0;
}

export {progressState, setProgressState}