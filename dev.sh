kill $(lsof -t -i:5173)
kill $(lsof -t -i:8000)

cd frontend && npm run dev &
cd frontend && npm run watch-orval &
cd backend && poetry run fastapi dev src/server.py
