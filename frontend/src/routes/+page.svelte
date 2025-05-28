<script lang="ts">
    import VCFFileUpload from "$lib/components/VCFFileUpload.svelte";
	import { fileState } from "$lib/states/fileState.svelte";
	import { onMount } from "svelte";
  import type { AnalysisResponse, FileUploadResponse, HealthResponse, ResultsResponse, StatusPollResponse, TraitSummary } from "../clients/clients";
	import { setProgressState, progressState } from "$lib/states/progressState.svelte";
	import { fade } from "svelte/transition";
  // Track completed steps using Svelte 5 runes
  let completedSteps = $state(new Set());
  // let results = $state<TraitSummary[]>([{'trait_title': 'Early-onset schizophrenia', 'increase_decrease': 34.6, 'details': "Early-onset schizophrenia (EOS) is a rare form of schizophrenia that begins before the age of 18. This association study found that the 'A' allele of the rs1801133 variant is associated with an increased risk of EOS in Han Chinese populations. The study involved a two-stage genome-wide association study (GWAS) with over 2,159 EOS cases and 6,561 controls. The identified risk loci may provide potential targets for therapeutics and diagnostics.", 'good_or_bad': 'bad', 'image_url': 'https://tse4.mm.bing.net/th/id/OIP.6-VgYes6T0EYLl9UaW4dUAHaHa?w=159&h=180&c=7&r=0&o=5&pid=1.7'}]);
  let results = $state<TraitSummary[]>([]);

  // Track progress state changes
  $effect(() => {
    if (progressState.status && progressState.status !== 'idle' && !completedSteps.has(progressState.status)) {
      completedSteps = new Set([...completedSteps, progressState.status]);
    }
  });

  onMount(async () => {
    const res = await fetch("http://localhost:8000/health");
    const resJSON: HealthResponse = await res.json();
    
    console.log(resJSON.status);
  });

  let intervalId: NodeJS.Timeout;

  const startPolling = async () => {
    intervalId = setInterval(async () => {
      const res = await fetch("http://localhost:8000/status_poll");
      const resJSON: StatusPollResponse = await res.json();
      console.log("Status:", resJSON.status);
      setProgressState(resJSON.status, resJSON.progress ?? 0);

      if (resJSON.status === "completed") {
        stopPolling();
        getResults();
      }
    }, 200);
  }

  const stopPolling = () => {
    clearInterval(intervalId);
  }

  const getResults = async () => {
    const res = await fetch("http://localhost:8000/results");
    const resJSON: ResultsResponse = await res.json();
    console.log("Results:", resJSON.results);

    results = [...resJSON.results];
  }

  const handleAnalyseVariants = async () => {
    const fileToSend = fileState.file;
    if (!fileToSend) {
      console.error("No file selected");
      return;
    }

    const formData = new FormData();
    formData.append("file", fileToSend);

    try {
      // Send file to server
      const res = await fetch("http://localhost:8000/upload_file", {
        method: "POST",
        body: formData,
        // Don't set Content-Type header, let the browser set it with the boundary
      });

      if (!res.ok) {
        const error = await res.text();
        throw new Error(`Upload failed: ${error}`);
      }

      const resJSON = await res.json();
      console.log("File uploaded successfully:", resJSON.filename);

      // Start the analysis
      const analysisRes = await fetch("http://localhost:8000/analysis");
      const analysisResJSON: AnalysisResponse = await analysisRes.json();
      console.log("Analysis started:", analysisResJSON.message);
      if (analysisRes.ok) {
        startPolling();
      }

    } catch (error) {
      console.error("Error uploading file:", error);
    }
  };
</script>

<main class="relative flex size-full min-h-screen flex-col bg-[#f8fcfa] group/design-root overflow-x-hidden" style='font-family: Manrope, "Noto Sans", sans-serif;'>
    <div class="layout-container flex h-full grow flex-col">
      <header class="flex items-center justify-between whitespace-nowrap border-b border-solid border-b-[#e6f4ef] px-10 py-3">
        <div class="flex items-center gap-4 text-[#0c1c17]">
          <div class="size-4">
            <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path
                d="M13.8261 30.5736C16.7203 29.8826 20.2244 29.4783 24 29.4783C27.7756 29.4783 31.2797 29.8826 34.1739 30.5736C36.9144 31.2278 39.9967 32.7669 41.3563 33.8352L24.8486 7.36089C24.4571 6.73303 23.5429 6.73303 23.1514 7.36089L6.64374 33.8352C8.00331 32.7669 11.0856 31.2278 13.8261 30.5736Z"
                fill="currentColor"
              ></path>
              <path
                fill-rule="evenodd"
                clip-rule="evenodd"
                d="M39.998 35.764C39.9944 35.7463 39.9875 35.7155 39.9748 35.6706C39.9436 35.5601 39.8949 35.4259 39.8346 35.2825C39.8168 35.2403 39.7989 35.1993 39.7813 35.1602C38.5103 34.2887 35.9788 33.0607 33.7095 32.5189C30.9875 31.8691 27.6413 31.4783 24 31.4783C20.3587 31.4783 17.0125 31.8691 14.2905 32.5189C12.0012 33.0654 9.44505 34.3104 8.18538 35.1832C8.17384 35.2075 8.16216 35.233 8.15052 35.2592C8.09919 35.3751 8.05721 35.4886 8.02977 35.589C8.00356 35.6848 8.00039 35.7333 8.00004 35.7388C8.00004 35.739 8 35.7393 8.00004 35.7388C8.00004 35.7641 8.0104 36.0767 8.68485 36.6314C9.34546 37.1746 10.4222 37.7531 11.9291 38.2772C14.9242 39.319 19.1919 40 24 40C28.8081 40 33.0758 39.319 36.0709 38.2772C37.5778 37.7531 38.6545 37.1746 39.3151 36.6314C39.9006 36.1499 39.9857 35.8511 39.998 35.764ZM4.95178 32.7688L21.4543 6.30267C22.6288 4.4191 25.3712 4.41909 26.5457 6.30267L43.0534 32.777C43.0709 32.8052 43.0878 32.8338 43.104 32.8629L41.3563 33.8352C43.104 32.8629 43.1038 32.8626 43.104 32.8629L43.1051 32.865L43.1065 32.8675L43.1101 32.8739L43.1199 32.8918C43.1276 32.906 43.1377 32.9246 43.1497 32.9473C43.1738 32.9925 43.2062 33.0545 43.244 33.1299C43.319 33.2792 43.4196 33.489 43.5217 33.7317C43.6901 34.1321 44 34.9311 44 35.7391C44 37.4427 43.003 38.7775 41.8558 39.7209C40.6947 40.6757 39.1354 41.4464 37.385 42.0552C33.8654 43.2794 29.133 44 24 44C18.867 44 14.1346 43.2794 10.615 42.0552C8.86463 41.4464 7.30529 40.6757 6.14419 39.7209C4.99695 38.7775 3.99999 37.4427 3.99999 35.7391C3.99999 34.8725 4.29264 34.0922 4.49321 33.6393C4.60375 33.3898 4.71348 33.1804 4.79687 33.0311C4.83898 32.9556 4.87547 32.8935 4.9035 32.8471C4.91754 32.8238 4.92954 32.8043 4.93916 32.7889L4.94662 32.777L4.95178 32.7688ZM35.9868 29.004L24 9.77997L12.0131 29.004C12.4661 28.8609 12.9179 28.7342 13.3617 28.6282C16.4281 27.8961 20.0901 27.4783 24 27.4783C27.9099 27.4783 31.5719 27.8961 34.6383 28.6282C35.082 28.7342 35.5339 28.8609 35.9868 29.004Z"
                fill="currentColor"
              ></path>
            </svg>
          </div>
          <h2 class="text-[#0c1c17] text-lg font-bold leading-tight tracking-[-0.015em]">Health Insights</h2>
        </div>
        <div class="flex flex-1 justify-end gap-8">
          <div class="flex items-center gap-9">
            <a class="text-[#0c1c17] text-sm font-medium leading-normal" href="#">Dashboard</a>
            <a class="text-[#0c1c17] text-sm font-medium leading-normal" href="#">Reports</a>
            <a class="text-[#0c1c17] text-sm font-medium leading-normal" href="#">Settings</a>
          </div>
          <div
            class="bg-center bg-no-repeat aspect-square bg-cover rounded-full size-10"
            style='background-image: url("https://lh3.googleusercontent.com/aida-public/AB6AXuAs0vy__ja4kuicIZdn22KlOyxFZcn5B7ga77zi6tNK5Nx0oWADCGNZ8ASpE-iotiSjGHvpNzEpIGMYFJxQQ1OQX2EehJGgoJl5-n581BX-UVeBqpRGlvyQiqJfjuwbVBKu7Rs0thqeWkZdWSyRiazq2JprQ4a4O1BAmZCG7Q3Zqn1k1qjhiusFgL8UemUfypCBMeN5JxDdqXx_1sm8jKIPc8KZHmW-TNz3OuECLjBoX8HaqL5V6HvuvXE_17mc_pkoW8VnoQSDouI");'
          ></div>
        </div>
      </header>
      <div class="gap-1 px-6 flex flex-1 justify-center py-5">
        <div class="layout-content-container flex flex-col w-80">
          <div class="flex flex-wrap justify-between gap-3 p-4">
            <div class="flex min-w-72 flex-col gap-3">
              <p class="text-[#0c1c17] tracking-light text-[32px] font-bold leading-tight">Upload VCF File</p>
              <p class="text-[#46a080] text-sm font-normal leading-normal">Upload your VCF file to analyze potential health conditions.</p>
            </div>
          </div>
         <VCFFileUpload disabled={progressState.status !== 'idle'} />
         <div class="mt-4"></div>
         <button
          class={`flex min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-xl h-10 px-4 bg-emerald-600 text-white text-sm font-bold leading-normal tracking-[0.015em] 
          transition-all duration-300 ease-in-out
          ${fileState.file ? 'visible opacity-100 translate-y-0 delay-150' : 'invisible opacity-0 -translate-y-4 duration-75 delay-0'}
          ${progressState.status !== 'idle' ? 'bg-gray-300 cursor-not-allowed' : ''}
          `}
          disabled={progressState.status !== 'idle'}
          onclick={handleAnalyseVariants}
          >
          <span class="truncate">Analyse Variants</span>
         </button>
        </div>
        <div class="relative layout-content-container bg-gray-100 rounded-2xl flex flex-col max-w-[960px] max-h-[calc(100vh-120px)] flex-1 ml-6 overflow-auto">
          {#if progressState.status != "idle"}
            <h2 transition:fade class="text-[#0c1c17] text-[22px] font-bold leading-tight tracking-[-0.015em] px-4 pb-3 pt-5">Processing Steps</h2>
          {/if}

          {#if completedSteps.has('vep_annotation') || progressState.status === 'vep_annotation'}
          <div class="flex flex-col gap-3 p-4" in:fade>
            <div class="flex gap-6 justify-between">
              <p class="text-[#0c1c17] text-base font-medium leading-normal">
                {progressState.status === 'vep_annotation' ? 'Generating VEP...' : 'Generated VEP'}
              </p>
              {#if progressState.status !== 'vep_annotation'}
                <span class="text-green-600">✓</span>
              {/if}
            </div>
            {#if progressState.status === 'vep_annotation'}
              <div class="rounded bg-[#cde9df]"><div class="h-2 rounded bg-[#019863] transition-width duration-300 ease-in-out" style={`width: ${progressState.percentage}%`}></div></div>
            {/if}
          </div>
          {/if}
          
          {#if completedSteps.has('find_damaging_variants') || progressState.status === 'find_damaging_variants'}
          <div class="flex flex-col gap-3 p-4" in:fade>
            <div class="flex gap-6 justify-between">
              <p class="text-[#0c1c17] text-base font-medium leading-normal">
                {progressState.status === 'find_damaging_variants' ? 'Finding Damaging Variants...' : 'Found Damaging Variants'}
              </p>
              {#if progressState.status !== 'find_damaging_variants' && completedSteps.has('find_damaging_variants')}
                <span class="text-green-600">✓</span>
              {/if}
            </div>
            {#if progressState.status === 'find_damaging_variants'}
              <div class="rounded bg-[#cde9df]"><div class="h-2 rounded bg-[#019863] transition-width duration-300 ease-in-out" style={`width: ${progressState.percentage}%`}></div></div>
            {/if}
          </div>
          {/if}
          
          {#if completedSteps.has('fetch_gwas_associations') || progressState.status === 'fetch_gwas_associations'}
          <div class="flex flex-col gap-3 p-4" in:fade>
            <div class="flex gap-6 justify-between">
              <p class="text-[#0c1c17] text-base font-medium leading-normal">
                {progressState.status === 'fetch_gwas_associations' ? 'Finding GWAS Associations...' : 'Found GWAS Associations'}
              </p>
              {#if progressState.status !== 'fetch_gwas_associations' && completedSteps.has('fetch_gwas_associations')}
                <span class="text-green-600">✓</span>
              {/if}
            </div>
            {#if progressState.status === 'fetch_gwas_associations'}
              <div class="rounded bg-[#cde9df]"><div class="h-2 rounded bg-[#019863] transition-width duration-300 ease-in-out" style={`width: ${progressState.percentage || 0}%`}></div></div>
            {/if}
          </div>
          {/if}
          
          {#if completedSteps.has('fetch_pubmed_abstracts') || progressState.status === 'fetch_pubmed_abstracts'}
          <div class="flex flex-col gap-3 p-4" in:fade>
            <div class="flex gap-6 justify-between">
              <p class="text-[#0c1c17] text-base font-medium leading-normal">
                {progressState.status === 'fetch_pubmed_abstracts' ? 'Finding Related Studies...' : 'Found Related Studies'}
              </p>
              {#if progressState.status !== 'fetch_pubmed_abstracts' && completedSteps.has('fetch_pubmed_abstracts')}
                <span class="text-green-600">✓</span>
              {/if}
            </div>
            {#if progressState.status === 'fetch_pubmed_abstracts'}
              <div class="rounded bg-[#cde9df]"><div class="h-2 rounded bg-[#019863] transition-width duration-300 ease-in-out" style={`width: ${progressState.percentage || 0}%`}></div></div>
            {/if}
          </div>
          {/if}

          {#if completedSteps.has('summarise_traits') || progressState.status === 'summarise_traits'}
          <div class="flex flex-col gap-3 p-4" in:fade>
            <div class="flex gap-6 justify-between">
              <p class="text-[#0c1c17] text-base font-medium leading-normal">
                {progressState.status === 'summarise_traits' ? 'Summarising Traits...' : 'Summarised Traits'}
              </p>
              {#if progressState.status !== 'summarise_traits' && completedSteps.has('summarise_traits')}
                <span class="text-green-600">✓</span>
              {/if}
            </div>
            {#if progressState.status === 'summarise_traits'}
              <div class="rounded bg-[#cde9df]"><div class="h-2 rounded bg-[#019863] transition-width duration-300 ease-in-out" style={`width: ${progressState.percentage || 0}%`}></div></div>
            {/if}
          </div>
          {/if}

          {#each results as result}
            <div class="flex flex-col gap-3 p-4 w-full" in:fade>
              <span class="flex flex-row items-center">
                <h1 class="font-bold text-2xl">{result.trait_title}</h1>
                <h2 class={`font-bold ml-4 ${result.good_or_bad === 'good' ? 'text-green-600' : 'text-red-600'}`}>{result.increase_decrease > 0 ? '+' : ''}{result.increase_decrease}%</h2>
              </span>
              <div class="w-full flex flex-row gap-4">
                <img src={result.image_url} alt="" class="w-36 aspect-square rounded-xl">
                <p>{result.details}</p>
              </div>
            </div>
          {/each}

          <div class={`absolute w-full min-h-[30rem] flex flex-col items-center justify-center text-center 
          
            ${progressState.status != "idle" ? 'invisible opacity-0 -translate-y-4 duration-75 delay-0' : 'visible opacity-100 translate-y-0 delay-150'}`}>
            <div class="relative w-full max-w-[960px] px-8">
              <!-- Animated arrow pointing left -->

              <div class="flex flex-col items-center">
                <h1 class="text-[#2e8f71] text-2xl font-bold leading-normal">VariantExplain</h1>
                <div class="mt-4"></div>
                <p class="text-gray-400 text-sm font-normal leading-normal max-w-[400px]">This is a tool that helps you understand the potential health conditions associated with your genetic variants.</p>
                <div class="mt-4"></div>
                <p class="text-[#2e8f71] text-sm font-bold leading-normal max-w-[400px]">Upload your VCF file to analyze potential health conditions.</p>
                <div class="mt-8"></div>
                {#if !fileState.file}
                  <div class="flex items-center animate-bounce-left">
                    <svg class="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 17l-5-5m0 0l5-5m-5 5h16"></path>
                      <!-- <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 17l-5-5m0 0l5-5m-5 5h16" style="transform: translateX(-10px);"></path> -->
                    </svg>
                  </div>
                  <p class="text-[#2e8f71] text-sm font-normal leading-normal max-w-[400px]">Go to the sidebar to upload your VCF file and analyse variants.</p>
                {/if}
              
              </div>

            </div>
          </div>

          <style>
            @keyframes bounce-left {
              0%, 100% { transform: translateX(0) translateY(-50%); }
              50% { transform: translateX(-10px) translateY(-50%); }
            }
            .animate-bounce-left {
              animation: bounce-left 2s infinite;
            }
          </style>
        </div>
      </div>
    </div>
</main>
