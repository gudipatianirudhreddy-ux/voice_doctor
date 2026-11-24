# NexovAI Voice Doctor

Voice-based doctor appointment assistant built with FastAPI, SQLAlchemy, PostgreSQL, and Pipecat.

## Repository layout

- `backend/app/api` — REST endpoints
- `backend/app/service` — appointment business rules
- `backend/app/voice` — Pipecat bot and LLM tool adapters
- `backend/app/migrations` — Alembic migrations
- `frontend/` — browser dashboard (being developed)

## Backend setup

Requirements: Python 3.13+ and [uv](https://docs.astral.sh/uv/).

1. Create a local `.env` file in the repository root or `backend/` (do not commit it).
2. Set the required environment variables:

   - `DATABASE_URL`
   - `GROQ_API_KEY`
   - `ELEVENLABS_API_KEY`
   - `ELEVENLABS_VOICE_ID`

3. Install dependencies from the repository root:

   ```bash
   uv sync
   ```

4. Apply migrations from the repository root:

   ```bash
   uv run alembic -c alembic.ini upgrade head
   ```

5. Start the REST API from the backend directory:

   ```bash
   cd backend
   uv run uvicorn app.main:app --reload
   ```

   API docs: http://127.0.0.1:8000/docs

## Frontend development

The REST API allows local browser origins on ports 5173 (Vite) and 3000 by default. To override these, set `FRONTEND_ORIGINS` to a comma-separated list of full origins, for example:

```env
FRONTEND_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Dashboard endpoints

- `GET /doctors/` — active doctors
- `GET /doctors/{doctor_id}/availability?requested_date=YYYY-MM-DD` — available slots
- `GET /appointments/?limit=100` — recent appointments (up to 100; patient phone numbers are not returned)
- `POST /appointments/` — create an appointment
- `POST /appointments/{appointment_id}/cancel` — cancel after phone verification
- `PUT /appointments/{appointment_id}/reschedule` — reschedule after phone verification

The browser voice call uses Pipecat's WebRTC runner/signaling flow; it is separate from the REST appointment endpoints.
