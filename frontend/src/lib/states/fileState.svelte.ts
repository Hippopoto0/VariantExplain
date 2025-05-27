type FileState = {
    file: File | null;
}
let fileState = $state<FileState>({file: null});

const setFile = (inpFile: File | null) => {
    fileState.file = inpFile;
}

export { fileState, setFile };