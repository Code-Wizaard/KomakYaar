import joblib
import re

class AntiVirus():
    def __init__(self, model_path='src/models/anti_virus/malware_model-1.0.pkl', vectorizer_path='src/models/anti_virus/tfidf_vectorizer-1.0.pkl'):
        self.model = joblib.load(model_path)
        self.vectorizer = joblib.load(vectorizer_path)
    
    def is_malware(self, text, threshold=0.7):
        vec = self.vectorizer.transform([text])
        prob = self.model.predict_proba(vec)[0][1]
        return prob >= threshold, prob