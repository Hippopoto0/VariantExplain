<script lang="ts">
    import { fileState, setFile } from "$lib/states/fileState.svelte";

    let { disabled }: {disabled?: boolean} = $props()

    function handleFileChange(event: Event) {
        const target = event.target as HTMLInputElement;
        const files = target.files;
        if (files && files.length > 0) {
            setFile(files[0]);
            // Reset the input value to allow selecting the same file again
            target.value = '';
        }
    }
</script>

<div class={`relative ${disabled ? 'opacity-50 cursor-not-allowed grayscale' : ''}`} >
    <div class="relative w-full">
        <div class="h-24 max-w-[480px] sm:h-auto sm:py-14 mx-auto"
             style="height: ${fileState.file ? '224px' : '96px'};">
        </div>
    </div>
    <div class="absolute flex flex-col p-4 top-0 left-0 right-0">
        <div class={`relative flex flex-col items-center gap-6 rounded-xl border-2 border-dashed border-[#cde9df] px-6 py-14 bg-gray-50
        transition-all duration-300 ease-in-out
        ${fileState.file ? 'invisible opacity-0 translate-y-10' : 'visible opacity-100 translate-y-0'}`}>
            <div class="flex max-w-[480px] flex-col items-center gap-2">
            <p class="text-[#0c1c17] text-lg font-bold leading-tight tracking-[-0.015em] max-w-[480px] text-center">Drag and drop your VCF file here</p>
            <p class="text-[#0c1c17] text-sm font-normal leading-normal max-w-[480px] text-center">Or browse to select a file from your computer</p>
            </div>
            <button
            class="flex min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-xl h-10 px-4 bg-[#e6f4ef] text-[#0c1c17] text-sm font-bold leading-normal tracking-[0.015em]"
            >
            <span class="truncate">Browse Files</span>
            </button>
            <input type="file" accept=".vcf" oninput={handleFileChange} class="absolute inset-0 opacity-0 size-full" />
        </div>
    </div>
    <div class={`absolute size-full flex flex-col top-0 items-center justify-center p-4 h-24 max-w-[480px] rounded-xl border-2 border-dashed border-[#cde9df]
    transition-all duration-300 ease-in-out
    ${fileState.file ? 'visible opacity-100 translate-y-0' : 'invisible opacity-0 -translate-y-10'}`}>
        <span class="flex items-center gap-2">
            <div class="flex items-center gap-2">
            <h1 class="text-green-700 text-lg font-bold leading-tight tracking-[-0.015em]">{fileState.file?.name}</h1>
            <button 
                onclick={(e) => {e.stopPropagation(); setFile(null)}}
                class="text-gray-500 hover:text-red-500 transition-colors"
                aria-label="Remove file"
                disabled={disabled}
            >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
            </button>
            </div>
        </span>
        <div class="mt-2"></div>
        <div class="relative">
            <button class="flex min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-xl h-10 px-4 bg-[#e6f4ef] text-[#0c1c17] text-sm font-bold leading-normal tracking-[0.015em]"
            disabled={disabled}
            >Click here to change</button>
            <input type="file" accept=".vcf" oninput={handleFileChange} class="absolute inset-0 opacity-0 size-full" />
        </div>
    </div>
</div>

