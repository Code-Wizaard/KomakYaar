import pickle
import re

class ProfanityDetector:
    def __init__(self, model_path='profanity_model.pkl'):
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
        self.model = data['model']
        self.vectorizer = data['vectorizer']
    
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