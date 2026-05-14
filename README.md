# Zoom Meeting Intelligence

AI-powered meeting assistant that joins Zoom, Google Meet, and Teams calls as a participant. It transcribes with speaker identification, contributes real-time insights to the meeting chat, and delivers comprehensive post-meeting summaries.

## What It Does

**During calls:**
- Transcribes everything with speaker labels
- Detects topics, action items, and decisions in real time
- Posts relevant insights and research findings to the meeting chat
- Tracks who committed to what

**After calls:**
- Generates an executive summary
- Lists all action items with assignees
- Documents all decisions with context
- Provides the full searchable transcript

## Architecture

```
Meeting URL
    |
    v
Recall.ai Bot (joins as participant)
    |
    v
Real-time Transcript Stream (WebSocket)
    |
    v
AI Processing Pipeline (Claude API)
    |
    +--> Chat Messages (posted to meeting in real time)
    +--> Action Items (tracked and attributed)
    +--> Decisions (logged with context)
    +--> Post-Meeting Summary (comprehensive report)
```

**Stack:** Python 3.11+, FastAPI, Recall.ai, Anthropic Claude API

## Quick Start

### 1. Install dependencies

```bash
cd zoom-intelligence
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

For demo mode (no API keys needed):
```bash
echo "DEMO_MODE=true" > .env
```

For live mode:
```bash
DEMO_MODE=false
RECALL_API_KEY=your_recall_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 3. Run the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8900 --reload
```

Or:
```bash
python -m app.main
```

### 4. Try the API

**Join a meeting (demo mode):**
```bash
curl -X POST http://localhost:8900/api/v1/meetings/join \
  -H "Content-Type: application/json" \
  -d '{"meeting_url": "https://zoom.us/j/1234567890"}'
```

**Check meeting status:**
```bash
curl http://localhost:8900/api/v1/meetings/{meeting_id}
```

**Get live transcript:**
```bash
curl http://localhost:8900/api/v1/meetings/{meeting_id}/transcript
```

**End meeting and get summary:**
```bash
curl -X POST http://localhost:8900/api/v1/meetings/{meeting_id}/end
```

**List all meetings:**
```bash
curl http://localhost:8900/api/v1/meetings
```

### 5. Interactive API docs

Visit http://localhost:8900/docs for the Swagger UI.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service info and endpoint list |
| GET | `/health` | Health check with config status |
| POST | `/api/v1/meetings/join` | Join a meeting |
| GET | `/api/v1/meetings` | List all meetings |
| GET | `/api/v1/meetings/{id}` | Get meeting status and data |
| GET | `/api/v1/meetings/{id}/transcript` | Get live transcript |
| POST | `/api/v1/meetings/{id}/end` | End meeting and get summary |
| POST | `/api/v1/webhooks/recall/transcript/{id}` | Recall.ai transcript webhook |
| POST | `/api/v1/webhooks/recall/status/{id}` | Recall.ai status webhook |

## Demo Mode

When `DEMO_MODE=true`, the system simulates a meeting with a pre-scripted transcript. This exercises the full pipeline (transcript handling, AI analysis, action item extraction, summary generation) without needing live API credentials.

The demo transcript simulates a product strategy meeting with four participants discussing roadmap, pricing, and competitive analysis.

## Project Structure

```
zoom-intelligence/
    app/
        api/
            routes.py          # FastAPI route handlers
        core/
            config.py          # Settings from environment
            logging.py         # Structured logging
        models/
            meeting.py         # Pydantic data models
        services/
            recall_client.py   # Recall.ai API integration
            ai_processor.py    # Claude-powered transcript analysis
            transcript_handler.py  # Real-time processing pipeline
            meeting_manager.py # Meeting lifecycle orchestration
            demo_provider.py   # Demo transcript generator
        main.py               # FastAPI application entry point
    tests/
        test_models.py
        test_demo_provider.py
        test_ai_processor.py
        test_transcript_handler.py
        test_api.py
    config/
        settings.toml
    .env.example
    pyproject.toml
```

## Running Tests

```bash
pytest -v
```

## Going Live (Recall.ai Setup)

1. Sign up at https://recall.ai and get an API key
2. Set `RECALL_API_KEY` in your `.env`
3. Set `DEMO_MODE=false`
4. Configure your webhook URL in Recall.ai dashboard to point to:
   - Transcript: `https://your-domain/api/v1/webhooks/recall/transcript/{meeting_id}`
   - Status: `https://your-domain/api/v1/webhooks/recall/status/{meeting_id}`
5. Set `ANTHROPIC_API_KEY` for Claude-powered analysis

## Cost Per Meeting Hour

| Component | Cost |
|-----------|------|
| Recall.ai (bot + recording) | ~$0.50/hr |
| Transcription (built-in) | ~$0.15/hr |
| LLM processing (Claude) | ~$0.10-0.30/hr |
| Infrastructure | ~$0.05/hr |
| **Total** | **~$0.80-1.00/hr** |
