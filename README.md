# Plan-It: Intelligent Planning Assistant

Plan-It is an AI-powered conversational agent designed to help users create, refine, and manage structured plans. Unlike generic chatbots that often lose context or hallucinate structure, Plan-It uses a deterministic state machine to guide users through a specific workflow: clarifying goals, proposing a structure, and refining tasks iteratively.

This project demonstrates a production-grade implementation of an agentic workflow using **LangChain**, **LangGraph**, **FastAPI**, and **React**.

---

## 🏗️ Architecture & Design Decisions

Building a reliable planning agent requires more than just prompting an LLM. This project implements several specific architectural patterns to ensure reliability, safety, and usability.

### 1. The Two-Phase "Commit" Protocol
One of the biggest challenges with LLM agents is preventing them from finalizing decisions prematurely. To solve this, the agent in `backend/agent.py` implements specific `ActionType` states:
*   **PROPOSE:** The agent gathers requirements and presents a draft plan. This is a read-only preview state.
*   **CREATE:** This action is *only* triggered after the user explicitly confirms the proposed plan (e.g., "Yes, looks good").
*   This separation ensures the user is always in the loop before any persistent state change occurs, preventing the "runaway agent" problem.

### 2. Structured State Management (LangGraph)
Instead of treating the conversation as a simple append-only list of strings, the system uses **LangGraph** to model the interaction as a state machine.
*   The agent's output is not just text; it's a structured `AgentResponse` JSON object containing a `thought` trace (hidden from user), a `response_to_user`, and a strongly-typed `Plan` object.
*   This allows the Frontend to render interactive UI components (like the Kanban implementation in `PlanPanel.jsx`) rather than just parsing markdown text.

### 3. Context Budgeting & Semantic Compression
LLM context windows are finite and expensive. The `ContextManager` (`backend/context_manager.py`) actively manages the token budget:
*   **Token Estimation:** We approximate token counts for every message using a heuristic (1 token ≈ 4 chars).
*   **Smart Compression:** When the conversation history exceeds 75% of the limit (approx. 6k tokens), a specialized summarization prompt kicks in.
*   **Key Insight:** Crucially, the *current active plan* is never summarized. It is always injected fresh into the context (`_format_plan_for_context`), ensuring the AI never "forgets" the specific details of the document it's working on, even if the conversation history is compressed.

### 4. Safety Guardrails vs. System Prompts
To keep the agent focused, we separated the logic into two distinct layers:
*   **Guardrail Layer:** A specific `GUARDRAIL_PROMPT` screens inputs *before* they reach the planning logic. This cheaply filters out irrelevant queries (e.g., "Write a poem about dogs") without wasting the main agent's reasoning capacity.
*   **System Layer:** The core `SYSTEM_PROMPT` focuses purely on the mechanics of plan creation (ID generation, status tracking, summarization), keeping the main prompt cleaner and more effective.

---

## 🚀 Setup & Run Instructions

### Prerequisites
*   **Python:** 3.10 or higher
*   **Node.js:** 16+ and npm
*   **API Keys:** A Google Cloud API Key (for Gemini models)
*   **Database (Optional):** MongoDB (the app falls back to in-memory storage if not provided)

### 1. Backend Setup

1.  Navigate to the project root.
2.  **Create your environment file:**
    Create a `.env` file in the root directory:
    ```bash
    GOOGLE_API_KEY="your_actual_api_key_here"
    # Optional: MONGODB_URI="mongodb://localhost:27017"
    # Optional: JWT_SECRET="your_secret_key"
    ```

3.  **Install dependencies:**
    It is recommended to use a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # on Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

4.  **Start the API Server:**
    ```bash
    uvicorn backend.server:app --reload
    ```
    The backend will start at `http://127.0.0.1:8000`.

### 2. Frontend Setup

1.  **Navigate to the frontend directory:**
    Open a new terminal window.
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Start the Development Server:**
    ```bash
    npm run dev
    ```
    The application will be available at `http://localhost:5173`.

### 3. Usage Guide

1.  Open the web interface.
2.  (Optional) Click "Login" -> "Continue as Guest" for a quick start.
3.  **Start Planning:** Type a goal like *"Plan a 3-day marketing sprint"*.
4.  **Refine:** The agent will ask clarifying questions. Answer them to narrow down the scope.
5.  **Confirm:** Once the agent proposes a plan, review it in the right-hand panel. Type *"Yes"* to finalize it.
6.  **Execute:** You can now ask the agent to add steps, mark items as complete, or pivots goals.

---

## 🔮 Future Roadmap

### 1. Advanced Tool Calling
Currently, the agent is purely conversational and structural. The next phase involves equipping the agent with **executable tools** to perform real-world actions. This would allow the agent to not just *plan* a task, but *execute* parts of it (e.g., "Draft an email to the team" or "Search for optimization libraries").

### 2. Model Context Protocol (MCP) Integration
To extend the agent's capabilities without bloating the core codebase, we plan to integrate **MCP (Model Context Protocol)** servers. This effectively gives the agent a plugin system to interact with external services:
*   **Calendar Integration:** Automatically block time for planned tasks (Google Calendar/Outlook).
*   **Travel & Logistics:** Check flight availability and book tickets for travel-related plans.
*   **Knowledge Retrieval:** Fetch documentation or internal wiki pages to support technical planning tasks.

---

## Technical Stack
*   **Backend:** FastAPI, Pydantic, Python 3.10+
*   **AI Orchestration:** LangChain, LangGraph, Google Gemini Pro 2.5
*   **Frontend:** React 19, Vite, Tailwind CSS (via class names)
*   **Storage:** MongoDB (Async Motor driver) / In-Memory Fallback
