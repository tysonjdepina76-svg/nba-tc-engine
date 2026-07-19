import os
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

import numpy as np
from sentence_transformers import SentenceTransformer


class LocalFilingSystem:
    def __init__(self, index_dir="data/filing_system"):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.index_dir / "files.db"
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self._init_db()
        self._embeddings_cache = {}

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                path TEXT,
                sport TEXT,
                description TEXT,
                tags TEXT,
                drive_url TEXT,
                created_at TEXT,
                embedding BLOB
            )
        ''')
        conn.commit()
        conn.close()

    def save_file(self, path, sport, description, tags="", drive_url=""):
        file_id = hashlib.md5(path.encode()).hexdigest()
        embedding = self.model.encode(description).tolist()
        embedding_blob = np.array(embedding, dtype=np.float32).tobytes()

        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO files (id, path, sport, description, tags, drive_url, created_at, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (file_id, path, sport, description, tags, drive_url, datetime.now().isoformat(), embedding_blob))
        conn.commit()
        conn.close()

        self._embeddings_cache[file_id] = embedding
        return file_id

    def search(self, query, top_k=5):
        query_vec = self.model.encode(query).tolist()

        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT id, embedding FROM files")
        rows = c.fetchall()
        conn.close()

        results = []
        for file_id, blob in rows:
            if file_id in self._embeddings_cache:
                vec = self._embeddings_cache[file_id]
            else:
                vec = np.frombuffer(blob, dtype=np.float32).tolist()
                self._embeddings_cache[file_id] = vec

            sim = np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec))
            results.append((file_id, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        top_results = results[:top_k]

        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        output = []
        for file_id, sim in top_results:
            c.execute("SELECT path, sport, description, tags, drive_url FROM files WHERE id = ?", (file_id,))
            row = c.fetchone()
            if row:
                output.append({
                    "id": file_id,
                    "path": row[0],
                    "sport": row[1],
                    "description": row[2],
                    "tags": row[3],
                    "drive_url": row[4],
                    "similarity": round(sim, 4)
                })
        conn.close()
        return output

    def list_all(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT path, sport, description, tags, created_at FROM files ORDER BY created_at DESC")
        rows = c.fetchall()
        conn.close()
        return [{"path": r[0], "sport": r[1], "description": r[2], "tags": r[3], "created_at": r[4]} for r in rows]

    def delete_file(self, file_id):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("DELETE FROM files WHERE id = ?", (file_id,))
        conn.commit()
        conn.close()
        self._embeddings_cache.pop(file_id, None)
