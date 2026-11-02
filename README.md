# AI PDF Study Assistant (RAG)

An intelligent, interactive study assistant built with **FastAPI**, **React (Vite + Tailwind CSS)**, **PyMuPDF**, **ChromaDB**, **Sentence-Transformers**, and **Google Gemini API**.

---

## 🌟 Key Architecture & Concept Highlights
- **Retrieval-Augmented Generation (RAG):** Enhances LLM precision by searching your uploaded study notes before prompting the model, avoiding hallucinations.
- **Local Embedding Vector Store:** Generates vector embeddings locally using `sentence-transformers` and indexes them into an embedded `ChromaDB` instance.
- **Accurate Document Citations:** Answers are grounded in the retrieved text chunks, explicitly returning the source document name and page number.
- **Safe Fallback:** If the retrieved document context doesn't contain the answer, the assistant clearly informs you instead of guessing.

---

## 📁 Project Structure

```text
first rag pro/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app & CORS configuration
│   │   ├── config.py            # Pydantic environment configuration
│   │   ├── services/            # (Stage 2-4) PDF parsing, ChromaDB, Gemini
│   │   └── models/              # (Stage 2-4) Request & response schemas
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_api.py          # Backend unit tests
│   ├── requirements.txt         # Python dependencies
│   ├── .env.example             # Environment template
│   └── .env                     # Local secrets (never commit to git)
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main UI & Health connection view
│   │   ├── main.jsx             # React entry point
│   │   └── index.css            # Tailwind CSS styling
│   ├── package.json             # NPM dependencies & scripts
│   ├── vite.config.js           # Vite dev server & API proxy
│   └── tailwind.config.js       # Tailwind CSS configuration
└── README.md                    # Setup and guide
```

---

## 🚀 Getting Started Locally

### Prerequisites
1. **Python 3.12** (Recommended for PyTorch and ChromaDB compatibility)
2. **Node.js (v18+)** and **npm**

---

### Step 1: Run Backend (FastAPI)

1. Open a terminal in the project root:
   ```powershell
   cd "backend"
   ```

2. Activate the virtual environment:
   - **Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD):**
     ```cmd
     venv\Scripts\activate.bat
     ```
   - **macOS / Linux:**
     ```bash
     source venv/bin/activate
     ```

3. Ensure dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your `.env` file (copy from `.env.example` if not already created):
   ```bash
   # Add your Gemini API key from https://aistudio.google.com/
   GEMINI_API_KEY=your_actual_key_here
   ```

5. Run unit tests to verify:
   ```bash
   pytest
   ```

6. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   - API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - Health Check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

### Step 2: Run Frontend (React + Vite)

1. Open a second terminal in the project root:
   ```powershell
   cd "frontend"
   ```

2. Install dependencies (if not already installed):
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:5173](http://localhost:5173) in your browser. The UI will automatically connect to your running backend and verify connectivity in real time!
