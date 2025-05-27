import { defineConfig } from "orval";
export default defineConfig({ 
    coverletter: {
        input: 'http://localhost:8000/openapi.json',
        output: {
            target: './src/clients/clients.ts',
            baseUrl: "http://localhost:8000/"
        },
    }
});