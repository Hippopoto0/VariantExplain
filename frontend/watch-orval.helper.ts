import http from 'http';
import { exec } from 'child_process';
import { Buffer } from 'buffer';

const OPENAPI_URL = 'http://localhost:8000/openapi.json';
const POLL_INTERVAL_MS = 1000; // Poll every 1 second
const ORVAL_COMMAND = 'npm run orval';

let previousSpecContent: Buffer | null = null;
let isGenerating = false; // Prevent multiple orval runs if checks overlap

console.log(`Starting orval watcher. Polling ${OPENAPI_URL} every ${POLL_INTERVAL_MS}ms`);

const fetchOpenApiSpec = (): Promise<Buffer> => {
    return new Promise((resolve, reject) => {
        http.get(OPENAPI_URL, (res) => {
            if (res.statusCode !== 200) {
                reject(new Error(`Request failed with status code ${res.statusCode}`));
                // Consume response data to free up memory
                res.resume();
                return;
            }

            const chunks: Buffer[] = [];
            res.on('data', (chunk) => {
                chunks.push(chunk);
            });
            res.on('end', () => {
                resolve(Buffer.concat(chunks));
            });
        }).on('error', (err) => {
            reject(err);
        });
    });
};

const runOrval = (): Promise<void> => {
    return new Promise((resolve, reject) => {
        console.log(`Executing command: "${ORVAL_COMMAND}"`);
        const child = exec(ORVAL_COMMAND, (error, stdout, stderr) => {
            isGenerating = false; // Command finished
            if (error) {
                console.error(`Error executing command: ${error.message}`);
                reject(error);
                return;
            }
            if (stderr) {
                console.error(`Command stderr:\n${stderr}`);
            }
            if (stdout) {
                console.log(`Command stdout:\n${stdout}`);
            }
            console.log('Orval command finished successfully.');
            resolve();
        });

        // Optional: Stream stdout/stderr in real-time if desired
        // child.stdout?.pipe(process.stdout);
        // child.stderr?.pipe(process.stderr);
    });
};

const checkAndGenerate = async () => {
    if (isGenerating) {
        console.log('Orval is already running, skipping check.');
        return;
    }

    try {
        const currentSpecContent = await fetchOpenApiSpec();

        if (previousSpecContent === null) {
            // First successful fetch
            console.log('Initial OpenAPI spec loaded.');
            previousSpecContent = currentSpecContent;
            // Optionally run orval on initial load
            // isGenerating = true;
            // runOrval().catch(err => console.error('Initial orval run failed:', err));
        } else if (!currentSpecContent.equals(previousSpecContent)) {
            // Content has changed
            console.log('OpenAPI spec has changed. Running orval...');
            previousSpecContent = currentSpecContent; // Update to new content
            isGenerating = true;
            runOrval().catch(err => console.error('Orval run failed:', err));
        } else {
            // No change
            // console.log('No change detected in OpenAPI spec.'); // Uncomment for verbose logging
        }

    } catch (error: any) {
        console.error(`Failed to fetch OpenAPI spec: ${error.message}`);
    }
};

// Start the polling interval
setInterval(checkAndGenerate, POLL_INTERVAL_MS);

// Also run an initial check immediately
checkAndGenerate();

// Keep the process alive
process.stdin.resume();

process.on('SIGINT', () => {
  console.log('\nWatcher stopped.');
  process.exit();
});

process.on('SIGTERM', () => {
    console.log('\nWatcher stopped.');
    process.exit();
});