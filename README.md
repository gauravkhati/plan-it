# Plan-It 📋

**Plan-It** is a sophisticated conversational planning agent that helps users organize thoughts, create structured plans, and refine them through natural dialogue.

Built with a **FastAPI** backend powering a **LangGraph** agent (using **Gemini 2.0 Flash**), and a modern, premium **React** frontend.

## ✨ Features

- **Conversational Intelligence** — Powered by Gemini 2.0 and LangGraph for context-aware, multi-turn planning.
- **Structured Planning** —  Automatically generates organized plans with steps, status tracking, and descriptions.
- **Smart Context Management** — Handles long conversations with intelligent context compression and token management.
- **Secure Authentication** — Complete email/password authentication system with JWT sessions.
- **Persistent Storage** — Saves all plans, versions, and chat history using MongoDB (or in-memory for testing).
- **Premium UI/UX** — A polished "Vibrant Pro" React interface with:
  - Real-time chat with optimistic updates
  - Split-view dashboard (Chat + Plan)
  - Plan version history
  - Responsive design with smooth animations
  - Modern "Vibrant Pro" theme (Electric Indigo/Violet)

## 🏗️ Project Structure

```
Plan-It/
├── backend/
│   ├── agent.py           # LangGraph agent definition & logic
│   ├── auth.py            # JWT auth, user management, password hashing
│   ├── context_manager.py # Token counting & context compression
│   ├── models.py          # Pydantic data models
│   ├── server.py          # FastAPI application & endpoints
│   └── session_store.py   # MongoDB & In-Memory storage backends
├── frontend-react/        # Modern React Frontend
│   ├── src/
│   │   ├── components/    # React components (ChatPanel, PlanPanel, etc.)
│   │   ├── services/      # API client
│   │   ├── App.jsx        # Main application logic
│   │   └── index.css      # Premium "Vibrant Pro" styling
│   └── vite.config.js     # Vite configuration
├── requirements.txt       # Python dependencies
└── README.md
```

## 🚀 Quick Start

### Backend Setup

1. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   Copy `.env.example` to `.env` and configure your keys:
   ```bash
   cp .env.example .env
   ```
   *Required:* `GOOGLE_API_KEY` (Get from AI Studio)
   *Optional:* `MONGODB_URI` (Defaults to in-memory storage if omitted)

3. **Start the Server**
   ```bash
   uvicorn backend.server:app --reload --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend-react
   ```

2. **Install Node dependencies**
   ```bash
   npm install
   ```

3. **Start the Development Server**
   ```bash
   npm run dev
   ```
   Open [http://localhost:5173](http://localhost:5173) to start planning!

## 🔌 API Endpoints

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| **Auth** | | | |
| `POST` | `/auth/register` | Register new user | Public |
| `POST` | `/auth/login` | Login & get JWT | Public |
| `GET` | `/auth/me` | Get current user info | Auth |
| **Sessions** | | | |
| `GET` | `/sessions` | List all user plans | Auth |
| `POST` | `/session` | Create new plan/session | Auth |
| `GET` | `/session/{id}` | Get plan details | Auth |
| **Chat** | | | |
| `POST` | `/chat` | Send message to agent | Auth |
| `GET` | `/session/{id}/history` | Get chat history | Auth |
| `GET` | `/session/{id}/versions` | Get plan version history | Auth |

## 🛠️ Tech Stack

- **AI/LLM:** Google Gemini 2.0 Flash, LangChain, LangGraph
- **Backend:** Python 3.10, FastAPI, Pydantic, PyJWT, Bcrypt
- **Database:** MongoDB (Motor async driver)
- **Frontend:** React 19, Vite, Lucide React
- **Styling:** Custom CSS Variables system ("Vibrant Pro" theme)

## How It Works

1. **Preprocess** — the user message is added to the session; preferences are extracted and context is compressed if needed.
2. **Generate** — the full conversation (or compressed summary + recent messages) is sent to Gemini with a structured-output system prompt. The LLM returns a JSON object with `thought`, `response_to_user`, `action`, `plan`, and `change_summary`.
3. **Postprocess** — the agent's response is recorded, and if a plan was created or updated, a new version is saved.

These three steps run as nodes in a **LangGraph** state graph.
