
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report
from sentence_transformers import SentenceTransformer, util

# -------- CONFIGURATION --------
MODEL_PATH = "backend/focus_model.pkl"
DATA_PATH = "backend/training_data.csv"

# 1. Load Data
df = pd.read_csv(DATA_PATH)

print(f"Loading data from {DATA_PATH}...")
print(f"Shape: {df.shape}")

# 2. Feature Engineering
# We will use SentenceTransformer for embeddings (SBERT)
# This is "Resume Gold" - State of the Art Semantic Similarity
print("Loading SentenceTransformer model (this may take a moment)...")
embedder = SentenceTransformer('all-MiniLM-L6-v2') 

# Compute Embeddings for Goals and Titles
print("Computing embeddings...")
goal_embeddings = embedder.encode(df['goal'].tolist(), convert_to_tensor=True)
title_embeddings = embedder.encode(df['window_title'].tolist(), convert_to_tensor=True)

# Compute Cosine Similarity
# util.cos_sim returns a matrix, we need diagonal for pair-wise
# Actually, iterating is safer/easier for disparate lists without matrix overhead if we just want row-by-row
from sklearn.metrics.pairwise import cosine_similarity

# Convert back to numpy designed for sklearn
goal_np = goal_embeddings.cpu().numpy()
title_np = title_embeddings.cpu().numpy()

# Calculate similarity for each row
similarities = []
for g, t in zip(goal_np, title_np):
    sim = cosine_similarity([g], [t])[0][0]
    similarities.append(sim)

df['cosine_similarity'] = similarities

# Mode Encoding
df['mode_encoded'] = df['mode'].map({'deep': 2, 'normal': 1}).fillna(1)

# TF-IDF for Window Title (Keywords matter too, e.g. "YouTube")
tfidf = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
X_text = tfidf.fit_transform(df['window_title']).toarray()

# Combine Features
# X = [cosine_similarity, mode_encoded, ...TF-IDF features...]
X_numeric = df[['cosine_similarity', 'mode_encoded']].values
X = np.hstack((X_numeric, X_text))

y = df['label']

# 3. Train Model
print("Training RandomForest Classifier...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

clf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight='balanced')
clf.fit(X_train, y_train)

# 4. Evaluate
print("Evaluating...")
y_pred = clf.predict(X_test)
print(classification_report(y_test, y_pred))

# 5. Save Artifacts
artifacts = {
    "model": clf,
    "tfidf": tfidf,
    "embedder": embedder, # We save reference or rely on loading separately? Loading SBERT is fast.
                          # Better to NOT pickle the whole torch model, just reload it in app.
    "feature_columns": ["cosine_similarity", "mode_encoded"] 
}
# We will NOT pickle the SBERT model inside the dict to avoid massive file size.
# The app will load SBERT fresh.

joblib.dump({
    "model": clf,
    "tfidf": tfidf
}, MODEL_PATH)

print(f"Model saved to {MODEL_PATH}")
