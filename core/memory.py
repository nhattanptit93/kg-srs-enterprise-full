
from sentence_transformers import SentenceTransformer
import faiss, numpy as np, json, os

class VectorMemory:
    def __init__(self, path="memory.json"):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = faiss.IndexFlatL2(384)
        self.texts = []
        self.path = path
        if os.path.exists(path):
            self.load()

    def add(self, text):
        emb = self.model.encode([text])
        self.index.add(np.array(emb))
        self.texts.append(text)
        self.save()

    def search(self, query, k=3):
        if not self.texts:
            return []
        emb = self.model.encode([query])
        D,I = self.index.search(np.array(emb), k)
        return [self.texts[i] for i in I[0] if i < len(self.texts)]

    def save(self):
        with open(self.path,"w") as f:
            json.dump(self.texts,f)

    def load(self):
        with open(self.path) as f:
            self.texts = json.load(f)
        if self.texts:
            embs = self.model.encode(self.texts)
            self.index.add(np.array(embs))
