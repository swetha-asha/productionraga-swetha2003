# prductionraga-swetha (RAG Assistant)

A production-style Retrieval Augmented Generation (RAG) chatbot that answers questions using document embeddings and similarity search.

## Tech Stack

- **Python (Flask)**: Backend API and server.
- **OpenAI API**: For generating text embeddings (`text-embedding-3-small`) and grounded responses (`gpt-4o`).
- **SQLite**: Persistent vector storage.
- **HTML/CSS/JS**: Modern, responsive chat interface.
- **NumPy**: Vector similarity calculations.

## Architecture

```text
                    +----------------------+
                    |      docs.json       |
                    |  Knowledge Base      |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |  Document Chunking   |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |  Embedding Generator |
                    |  (Gemini API)        |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |   Vector Database    |
                    |      SQLite DB       |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
User Question ----->| Query Embedding      |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Similarity Search    |
                    | Cosine Similarity    |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Retrieve Top Chunks  |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Prompt Construction  |
                    | Context + Question   |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |  LLM Response        |
                    | (Gemini API)         |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Chat UI (HTML/JS)    |
                    +----------------------+
```

## RAG Workflow

1. **User question** is received via the chat interface.
2. **Query embedding** is generated using Google Gemini's `embedding-001` model.
3. **Similarity search** is performed against stored document embeddings using Cosine Similarity.
4. **Top 3 chunks** (context) are retrieved from the SQLite database.
5. **Context grounded prompt** is constructed and sent to Gemini.
6. **Gemini generates response** based strictly on the provided context.
7. **Response** is returned to the user with a typing indicator.

## Setup Instructions

1. **Clone repository**:
   ```bash
   git clone https://github.com/username/genai-rag-assistant.git
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Key**:
   Set your OpenAI API key as an environment variable or edit `embeddings.py` and `app.py`.
   ```bash
   set OPENAI_API_KEY=sk-your-key-here
   ```

4. **Reset Database**:
   Since you switched from Gemini to OpenAI, the old embeddings are incompatible. Delete the `vectors.db` file to allow the system to regenerate them:
   ```bash
   del vectors.db
   ```

5. **Run application**:
   ```bash
   python app.py
   ```

6. **Open browser**:
   Navigate to `http://localhost:5000`

## Author

Swetha
