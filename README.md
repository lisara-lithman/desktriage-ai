# DeskTriage AI 🤖

DeskTriage AI is a secure, local, enterprise ticket routing and auto-drafting microservice. It is designed to run completely on-premise on Apple Silicon (M-series GPUs) using Apple's MLX framework. 

The application ingests employee support tickets, automatically classifies them into the correct department (**IT Support**, **HR**, or **Finance**), assigns a priority level (**Low**, **Medium**, **High**, **Critical**), and uses **Retrieval-Augmented Generation (RAG)** to draft highly professional, SOP-compliant resolution replies.

> 🔒 **Privacy First:** By utilizing a local 4-bit quantized open-source model with fine-tuned LoRA adapters, DeskTriage AI ensures that sensitive employee issues and corporate system error logs never leave the internal network.

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
         └─► [AI Triage Service] (Lifespan Loaded Singleton)
                   │
                   ├─► [ChromaDB Vector Store] (Retrieves Corporate SOP PDFs)
                   │
                   └─► [MLX Engine] (Metal GPU Accelerated Inference)
                             ▲
                             └─ [Llama-3.1-8B-Instruct-4bit + LoRA Adapters]
```

---

## 🚀 Key Features & ML Engineering

### 1. Synthetic Dataset Engineering
To bootstrap model training without risking sensitive real-world employee data, a synthetic ticket generator was built ([generate_dataset.py](file:///Users/lisara/Documents/desktriage-ai/backend/generate_dataset.py)).
* **Generator Model:** `gpt-4o-mini` with OpenAI Structured Outputs (guaranteeing strict schema compliance during synthesis).
* **Matrix Permutations:** The script randomly permutes combinations of:
  * **Departments:** `IT_Support`, `Finance`, `HR`
  * **Tones:** `highly frustrated and panicked`, `extremely formal`, `brief/direct`, `confused with typos`, `overly wordy`
  * **Topics:** Software crashes, payroll mismatches, paternity leaves, insurance boarding, etc.
* **Target Output:** 1,000 unique records compiled directly into standard Llama 3 ChatML template syntax.

### 2. Local QLoRA Fine-Tuning Specifications
The model was fine-tuned locally on Apple Silicon (M5 MacBook Pro) using Apple's native **MLX framework**.
* **Base Model:** `mlx-community/Meta-Llama-3.1-8B-Instruct-4bit` (~5.5 GB in RAM).
* **Tuning Method:** Quantized Low-Rank Adaptation (**QLoRA**).
* **Hyperparameters:**
  * **Rank (r):** `8`
  * **Scale ($\alpha$):** `20.0`
  * **Dropout:** `0.0`
  * **Learning Rate:** `5e-5` (stabilized down from the default `2e-4` to prevent gradient explosion and NaN loss).
  * **Batch Size:** `2`
  * **Iterations:** `400`
  * **Gradient Checkpointing:** Active (reduces memory consumption during backpropagation).
  * **Save Frequency:** Every `100` iterations.
* **Resulting Adapters:** Stored in [m5_adapters_8b](file:///Users/lisara/Documents/desktriage-ai/backend/m5_adapters_8b) (~100 MB).

### 3. Prompt Engineering & Templates
The fine-tuned model expects the standard **Llama 3 ChatML** template:
```text
<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

{user_message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
```

#### System Prompts:
* **Standard System Prompt:**
  > *"You are an expert corporate triage assistant. Analyze the employee's issue and return a valid JSON object containing department, priority, and llm_draft_reply. Do not include any introductory sentences, markdown blocks, or conversational filler."*
* **RAG System Prompt (With Context):**
  > *"You are an expert corporate triage assistant. Analyze the employee's issue using the provided Corporate SOPs context. In your draft reply, you MUST provide the specific troubleshooting steps, commands, or URLs described in the context. Return a valid JSON object containing department, priority, and llm_draft_reply. Do not include any introductory sentences, markdown blocks, or conversational filler."*

---

## 📚 Retrieval-Augmented Generation (RAG) Architecture

The RAG engine is built to inject authoritative company policy documents directly into the prompt context:

1. **Ingestion & Parsing ([ingest.py](file:///Users/lisara/Documents/desktriage-ai/backend/rag_engine/ingest.py)):** Reads PDF files in the corporate knowledge base and extracts text.
2. **Semantic Chunker ([chunker.py](file:///Users/lisara/Documents/desktriage-ai/backend/rag_engine/chunker.py)):** Implements a `hybrid_chunker` that:
   * Splits text by paragraph boundaries (`\n\n`).
   * Falls back to a word-aware sliding window of **1000 characters** with an overlap of **100 characters** if a paragraph is too long, avoiding splitting words in half.
3. **Embeddings & Vector Store:**
   * **Database:** `ChromaDB` (persistent storage under `chroma_db/`).
   * **Embedding Model:** `all-MiniLM-L6-v2` (SentenceTransformers, 384 dimensions).
   * **Distance Metric:** Cosine similarity.
4. **Retrieval ([retriever.py](file:///Users/lisara/Documents/desktriage-ai/backend/rag_engine/retriever.py)):** Retrieves the **top 2 matching chunks** ($N=2$) for every incoming ticket search query, merging them into the context variable.

---

## 📊 Model Evaluation & Performance Metrics

We built an automated evaluation pipeline ([evaluate_triage.py](file:///Users/lisara/Documents/desktriage-ai/backend/evaluate_triage.py)) to test the raw baseline model against the fine-tuned adapter version on a validation set of 15 tickets.

| Metric | Base Model (Un-tuned) | Fine-Tuned Model (Adapters) | Performance Delta |
| :--- | :---: | :---: | :---: |
| **JSON Parse Success Rate (Any Format)** | 100.0% | 100.0% | **0.0%** (Both can be parsed) |
| **Strict JSON Rate (Clean Output)** | 13.3% | 100.0% | **+86.7%** (Eliminated formatting errors) |
| **Markdown Fences Output (```json)** | 86.7% | 0.0% | **-86.7%** (Fences eliminated) |
| **Preamble / Conversational Filler** | 86.7% | 0.0% | **-86.7%** (Filler eliminated) |
| **Department Classification Accuracy** | 60.0% | 100.0% | **+40.0%** (Perfect classification) |
| **Priority Classification Accuracy** | 46.7% | 46.7% | **0.0%** (Identical accuracy) |
| **Perfect Triage Match (Strict + Correct)** | 26.7% | 46.7% | **+20.0%** (Overall improvement) |
| **Average Generation Latency** | 4.73s | 3.20s | **-1.53s** (~32% faster responses) |
| **Average Output Character Length** | 455.8 chars | 252.5 chars | **-203.3 chars** (~44% fewer tokens) |

### Key Evaluation Insights:
1. **Formatting Mastery:** The base model wrapped its JSON in markdown code blocks 86.7% of the time, risking API crashes. Fine-tuning brought strict formatting success to **100%**.
2. **Speed & Token Optimization:** The fine-tuned model outputs compact, single-line JSON instead of pretty-printed text, generating **44% fewer characters**. This reduces latency from **4.73s to 3.20s** on local Mac GPUs.
3. **Priority Calibration Bottleneck:** Both models scored **46.7%** on priority classification. Because priority is highly subjective, learning this mapping requires more than 400 training iterations, representing the primary target for future hyperparameter tuning.

---

## 📸 User Interface & Demo

The interface is built with dark-mode styling, glowing gradient indicators, and split ticket status queues.

### 1. Employee Ticket Submission
*The employee submits a ticket using informal language and typos (e.g., "paternity leaf" or "direct deposit deets").*
```text
[<img width="2464" height="612" alt="image" src="https://github.com/user-attachments/assets/1285a0e8-01e0-4761-9acd-0775ae4566c3" />

```

### 2. Admin Triage View (Human Resources Queue)
*The system successfully routes the ticket containing "paternity leaf" and "HR portal" to the Human Resources department, marks it Critical, and pre-fills the RAG-assisted draft reply with browser session recovery steps.*
```text

```

### 3. Admin Triage View (Finance Queue)
*The system correctly distinguishes a Finance direct deposit issue from an HR portal crash, routing it to the Finance queue and drafting a reply referencing direct deposit verification.*
```text
[Insert Screenshot of Admin Finance ticket detail here, e.g. /images/finance_ticket.png]
```

*(Note: To add your screenshots, save them under a `/public/images/` directory and update the markdown links above.)*

---

## 🛠️ Local Installation & Setup

### Prerequisites
* macOS running on Apple Silicon (M1, M2, M3, M4, or M5 chips).
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
   MLX_BASE_MODEL=mlx-community/Meta-Llama-3.1-8B-Instruct-4bit
   MLX_ADAPTER_PATH=./m5_adapters_8b
   ```
5. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```

### 2. Frontend Setup
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

## 🔮 Production Scaling Roadmap
To transition this local Mac prototype into a scalable enterprise application, the following updates are planned:
1. **Cloud Inference serving:** Convert MLX adapters to Hugging Face format and deploy them using **vLLM** on Linux instances with Nvidia GPUs to utilize continuous batching and parallel execution.
2. **Task Queueing:** Implement an asynchronous worker pattern using **Celery & Redis** to handle incoming ticket bursts gracefully without blocking the API threads.
3. **LLMOps Tracing:** Integrate **Langfuse** or **Langsmith** for logging and tracking model accuracy, latency drift, and prompt template versions in production.
