# DeskTriage AI 🤖

DeskTriage AI is a secure, enterprise ticket routing and auto-drafting microservice. It is designed with dual-architecture support: it can run completely on-premise on Apple Silicon (M-series GPUs) using Apple's MLX framework for maximum privacy, or scale seamlessly to the cloud using **Modal** serverless GPUs for high-throughput inference.

The application ingests employee support tickets, automatically classifies them into the correct department (**IT Support**, **HR**, or **Finance**), assigns a priority level (**Low**, **Medium**, **High**, **Critical**), and uses **Retrieval-Augmented Generation (RAG)** to draft highly professional, SOP-compliant resolution replies.

> 🔒 **Privacy First:** By utilizing a local 4-bit quantized open-source model with fine-tuned LoRA adapters, DeskTriage AI ensures that sensitive employee issues and corporate system error logs never leave the internal network when running in local mode.

---

## 🏗️ System Architecture

The application is structured into decoupled frontend, backend, and machine learning components:

```text
[Employee / Admin UI] (React + Vite)
         │  ▲
         ▼  │  (JSON API)
[FastAPI Backend Core] (Python)
         │  
         ├─► [MongoDB Atlas Database] (Ticket Persistence & Audit logs)
         │
         └─► [AI Triage Service] (Dual-Mode Engine)
                   │
                   ├─► [ChromaDB Vector Store] (Retrieves Corporate SOP PDFs)
                   │
                   └─► [Inference Backend]
                             │
                             ├─► Local: [MLX Engine] (Metal GPU Accelerated)
                             │       └─ [Llama-3.1-8B-Instruct-4bit + LoRA]
                             │
                             └─► Cloud: [Modal Serverless GPU] (A10G)
                                     └─ [HuggingFace Transformers + QLoRA]
```

---

## 🚀 Key Features & ML Engineering

### 1. Synthetic Dataset Engineering
To bootstrap model training without risking sensitive real-world employee data, a synthetic ticket generator was built (`generate_dataset.py`).
* **Generator Model:** `gpt-4o-mini` with OpenAI Structured Outputs (guaranteeing strict schema compliance during synthesis).
* **Matrix Permutations:** The script randomly permutes combinations of:
  * **Departments:** `IT_Support`, `Finance`, `HR`
  * **Tones:** `highly frustrated and panicked`, `extremely formal`, `brief/direct`, `confused with typos`, `overly wordy`
  * **Topics:** Software crashes, payroll mismatches, paternity leaves, insurance boarding, etc.
* **Target Output:** 1,000 unique records compiled directly into standard Llama 3 ChatML template syntax.

### 2. Fine-Tuning Specifications (Local & Cloud)
The model was fine-tuned for structured JSON output and tested across two ecosystems. See the full [Fine-Tuning Notebook](docs/DeskTriage_AI_Fine_Tuning.ipynb) for the complete training walkthrough.

#### Local Edge Training (Apple MLX)
* **Base Model:** `mlx-community/Meta-Llama-3.1-8B-Instruct-4bit` (~5.5 GB in RAM).
* **Tuning Method:** Quantized Low-Rank Adaptation (**QLoRA**).
* **VRAM Performance:** Capped at **6.17 GB** peak Unified Memory on an M5 MacBook Pro, taking ~12 minutes for 400 iterations.
* **Learning Rate:** `5e-5` (stabilized down from the default `2e-4` to prevent gradient explosion and NaN loss).

**Local Training Run — MLX Terminal Output:**

![MLX training run on Apple M5 — 400 iterations, peak 6.17 GB unified memory](docs/Screenshot%202026-06-09%20at%2003.25.44.png)

#### Cloud CUDA Training (PyTorch + PEFT)
* **Base Model:** `Llama-3-8B-Instruct`
* **Memory Optimization:** 4-bit NormalFloat (NF4) with Double Quantization and Paged AdamW (8-bit).
* **VRAM Performance:** Held steady at **90% GPU allocation** over a 4-hour run tracked on Weights & Biases.
* **Convergence:** Training loss dropped from **2.45 → ~0.70**, while evaluation loss dropped from **0.985 → 0.898**, proving no overfitting.

**Cloud Training Metrics (Weights & Biases):**

| Training Loss Curve | Eval Loss Curve | GPU Memory Usage |
|:---:|:---:|:---:|
| ![Train loss dropping from 2.45 to 0.70 over 400 steps](docs/W%26B%20Chart%207_6_2026%2C%2011_29_10%20PM.png) | ![Eval loss steadily decreasing — no overfitting](docs/W%26B%20Chart%207_6_2026%2C%2011_36_03%20PM.png) | ![GPU memory held steady at 90% across the full 4-hour run](docs/W%26B%20Chart%207_6_2026%2C%2011_34_28%20PM.png) |

### 3. Prompt Engineering & Templates
The fine-tuned model expects the standard **Llama 3 ChatML** template:
```text
<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

{user_message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
```
*When deployed to Modal, the Hugging Face Tokenizer (`apply_chat_template`) correctly translates these tags to control token IDs to ensure 100% strict JSON compliance.*

---

## 📚 Retrieval-Augmented Generation (RAG) Architecture

The RAG engine is built to inject authoritative company policy documents directly into the prompt context:

1. **Ingestion & Parsing (`ingest.py`):** Reads PDF files in the corporate knowledge base and extracts text.
2. **Semantic Chunker (`chunker.py`):** Implements a `hybrid_chunker` that:
   * Splits text by paragraph boundaries (`\n\n`).
   * Falls back to a word-aware sliding window of **1000 characters** with an overlap of **100 characters** if a paragraph is too long, avoiding splitting words in half.
3. **Embeddings & Vector Store:**
   * **Database:** `ChromaDB` (persistent storage under `chroma_db/`).
   * **Embedding Model:** `all-MiniLM-L6-v2` (SentenceTransformers, 384 dimensions).
   * **Distance Metric:** Cosine similarity.
4. **Retrieval (`retriever.py`):** Retrieves the **top 2 matching chunks** for every incoming ticket search query, merging them into the context variable.

---

## 📊 Model Evaluation & Performance Metrics

An automated evaluation pipeline (`evaluate_triage.py`) was built to test the raw baseline model against the fine-tuned adapter version on a held-out validation set of **10 unseen tickets**.

| Metric | Base Model (Un-tuned) | Fine-Tuned Model (Adapters) | Performance Delta |
| :--- | :---: | :---: | :---: |
| **JSON Parse Success Rate (Any Format)** | 100.0% | 100.0% | **0.0%** (Both parseable) |
| **Strict JSON Rate (Clean Output)** | 0.0% | 100.0% | **+100.0%** ✅ Eliminated all formatting errors |
| **Markdown Fences Output (```json)** | 100.0% | 0.0% | **-100.0%** ✅ Fences eliminated |
| **Preamble / Conversational Filler** | 100.0% | 0.0% | **-100.0%** ✅ Filler eliminated |
| **Department Classification Accuracy** | 100.0% | 100.0% | **0.0%** (Both correct) |
| **Priority Classification Accuracy** | 40.0% | 60.0% | **+20.0%** ✅ |
| **Perfect Triage Match (Strict + Correct)** | 40.0% | 60.0% | **+20.0%** ✅ |
| **Average Generation Latency** | 4.2s | 2.9s | **-1.36s** (~32% faster) ✅ |
| **Average Output Character Length** | 448.2 chars | 258.9 chars | **-189.3 chars** (~42% fewer tokens) ✅ |

> 📄 See [`backend/evaluation_report.md`](backend/evaluation_report.md) for the full side-by-side sample output comparisons between the base and fine-tuned model.

---

## 📸 User Interface

The interface is built with dark-mode styling, glowing gradient indicators, and split ticket status queues.

### Employee Ticket Submission
Employees submit support tickets in plain, informal language. The system handles typos, slang, and ambiguous phrasing (e.g., *"paternity leaf"*, *"direct deposit deets"*) and routes them correctly.

### Admin Triage Dashboard
The admin view shows all incoming tickets organized by department queue (IT Support, HR, Finance), each with its AI-assigned priority badge and the RAG-drafted reply pre-filled in the response editor — ready to review and send.

---

## 🗂️ Repository Structure

```text
desktriage-ai/
├── backend/
│   ├── app/
│   │   ├── auth/          # JWT authentication
│   │   ├── models/        # MongoDB document models
│   │   ├── routes/        # FastAPI route handlers
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   └── services/
│   │       └── ai_service.py   # Core AI triage engine (MLX + Modal)
│   ├── rag_engine/
│   │   ├── chunker.py     # Hybrid semantic chunker
│   │   ├── ingest.py      # PDF ingestion & embedding pipeline
│   │   └── retriever.py   # ChromaDB vector search
│   ├── m5_adapters_8b/    # Fine-tuned LoRA adapter weights
│   ├── modal_app.py       # Serverless GPU deployment (Modal)
│   └── evaluation_report.md
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── EmployeeDashboard.jsx
│       │   └── AdminDashboard.jsx
│       └── index.css
└── docs/
    ├── DeskTriage_AI_Fine_Tuning.ipynb   # Full fine-tuning notebook
    ├── Model_Fine_Tune_Details.pdf       # Detailed fine-tuning documentation
    └── [W&B Charts & Screenshots]
```

---

## 🛠️ Local Installation & Setup

### Prerequisites
* macOS running on Apple Silicon (M1-M5) OR a Modal account for cloud deployment.
* Python 3.9+ (configured in virtual environment).
* Node.js & npm (for the frontend).
* MongoDB Atlas cluster database.

### 1. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install required libraries:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your environment variables in `.env`:
   ```env
   MONGODB_URI=your_mongodb_connection_string
   JWT_SECRET=your_jwt_secret_token
   HF_TOKEN=your_hugging_face_read_token
   
   # For Local MLX:
   MLX_BASE_MODEL=mlx-community/Meta-Llama-3.1-8B-Instruct-4bit
   MLX_ADAPTER_PATH=./m5_adapters_8b
   
   # For Cloud Modal:
   MODAL_TOKEN_ID=your_modal_token_id
   MODAL_TOKEN_SECRET=your_modal_token_secret
   ```
5. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```

### 2. Serverless Cloud Deployment (Modal)
If you don't have an Apple Silicon GPU, or want to scale inference globally, you can deploy the model to Modal's serverless GPU cloud.
1. Authenticate with Modal:
   ```bash
   modal setup
   ```
2. Deploy the Inference app (will spin up an A10G GPU only when requested):
   ```bash
   modal deploy modal_app.py
   ```
3. The backend `ai_service.py` is configured to route traffic to your Modal endpoint automatically.

### 3. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Vite local server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to `http://localhost:5173`.

---

## 🧰 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | React, Vite |
| **Backend** | Python, FastAPI, Uvicorn |
| **Database** | MongoDB Atlas, ChromaDB |
| **Local Inference** | Apple MLX, Llama-3.1-8B-Instruct-4bit |
| **Cloud Inference** | Modal (A10G GPU), HuggingFace Transformers |
| **Fine-Tuning** | QLoRA, PEFT, LoRA Adapters |
| **Embeddings** | SentenceTransformers (`all-MiniLM-L6-v2`) |
| **Dataset Generation** | OpenAI GPT-4o-mini, Structured Outputs |
| **Training Monitoring** | Weights & Biases (W&B) |
| **Auth** | JWT |
