import joblib
import re

class ProfanityDetector:
    def __init__(self, model_path='src/models/profanity_checker/profanity_model-2.1.pkl', vectorizer_path='src/models/profanity_checker/tfidf_vectorizer-1.0.pkl'):
        self.model = joblib.load(model_path)
        self.vectorizer = joblib.load(vectorizer_path)

    def clean(self, text):
        if not isinstance(text, str):
            return ""
        text = re.sub(r'[\u200c\u200d\u200e\u200f]', '', text)
        text = re.sub(r'[^آ-ی\s0-9]', '', text)
        return text.strip()
    
    def is_swear(self, text, threshold=0.7):
        clean_text = self.clean(text)
        if len(clean_text) < 3:
            return False
        
        vec = self.vectorizer.transform([clean_text])
        prob = self.model.predict_proba(vec)[0][1]
        return prob >= threshold, prob