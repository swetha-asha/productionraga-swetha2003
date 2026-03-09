import json
import numpy as np
from embeddings import generate_embedding
from vector_db import insert_vector, get_vectors

def cosine_similarity(a, b):
    # Ensure they are numpy arrays
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def load_documents():
    """Loads documents from docs.json, generates embeddings, and stores them in the DB if empty."""
    existing_vectors = get_vectors()
    if existing_vectors:
        print("Knowledge base already loaded.")
        return

    with open("docs.json") as f:
        docs = json.load(f)

    print(f"Loading {len(docs)} documents into the vector store...")
    for doc in docs:
        text = doc["content"]
        embedding = generate_embedding(text)
        if embedding:
            insert_vector(text, embedding)
    print("Knowledge base loading complete.")

def search(query_embedding):
    """Searches for the most similar documents based on the query embedding."""
    vector_store = get_vectors()
    scores = []

    for item in vector_store:
        score = cosine_similarity(query_embedding, item["embedding"])
        scores.append((score, item["text"]))

    # Sort by score descending
    scores.sort(key=lambda x: x[0], reverse=True)

    # Return top 3 results
    return scores[:3]

def keyword_search(query):
    """Fallback: Searches for documents containing query keywords if embeddings fail."""
    with open("docs.json") as f:
        docs = json.load(f)
    
    query_words = set(query.lower().split())
    results = []
    
    for doc in docs:
        text = doc["content"]
        text_words = set(text.lower().split())
        # Check intersection of words
        match_count = len(query_words.intersection(text_words))
        if match_count > 0:
            results.append((match_count, text))
    
    # Sort by match count descending
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:3]
