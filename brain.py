import os
import json
import re
import math
import threading
import collections

# Global local LLM state
llm_pipeline = None
llm_ready = False
model_id = "Qwen/Qwen2-0.5B-Instruct"

# Pure Python Simple SLM Vectorizer (TF-IDF Cosine Similarity)
class SimpleSLM:
    def __init__(self):
        self.intents = []
        self.vocabulary = set()
        self.idf = {}
        self.pattern_vectors = [] # List of tuples: (vector, tag, responses)
        
    def tokenize(self, text):
        # Convert to lower case and isolate words
        words = re.findall(r'\b\w+\b', text.lower())
        return words

    def train(self, filepath):
        if not os.path.exists(filepath):
            print(f"[SLM] Training data not found at {filepath}")
            return
            
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        self.intents = data.get("intents", [])
        
        # 1. Build Vocabulary and Document counts
        doc_count = 0
        word_doc_counts = collections.defaultdict(int)
        
        all_patterns = []
        for intent in self.intents:
            tag = intent["tag"]
            responses = intent["responses"]
            for pattern in intent["patterns"]:
                words = self.tokenize(pattern)
                all_patterns.append((words, tag, responses))
                doc_count += 1
                
                # Document frequency for IDF
                unique_words = set(words)
                for w in unique_words:
                    word_doc_counts[w] += 1
                    self.vocabulary.add(w)
                    
        # 2. Calculate IDF
        for word, count in word_doc_counts.items():
            self.idf[word] = math.log(doc_count / (1 + count))
            
        # 3. Build tf-idf vectors for all patterns
        for words, tag, responses in all_patterns:
            vector = self.vectorize(words)
            self.pattern_vectors.append((vector, tag, responses))
            
        print(f"[SLM] Custom vector brain trained successfully on {len(self.pattern_vectors)} patterns.")

    def vectorize(self, words):
        # Compute term frequency tf
        tf = collections.defaultdict(int)
        for w in words:
            if w in self.vocabulary:
                tf[w] += 1
                
        # Compute tf-idf
        vector = {}
        for w, count in tf.items():
            vector[w] = count * self.idf.get(w, 0.0)
        return vector

    def cosine_similarity(self, vec1, vec2):
        # Dot product
        dot_product = 0.0
        for w, val in vec1.items():
            if w in vec2:
                dot_product += val * vec2[w]
                
        # Magnitude
        mag1 = math.sqrt(sum(v**2 for v in vec1.values()))
        mag2 = math.sqrt(sum(v**2 for v in vec2.values()))
        
        if mag1 == 0.0 or mag2 == 0.0:
            return 0.0
            
        return dot_product / (mag1 * mag2)

    def predict(self, text, threshold=0.45):
        words = self.tokenize(text)
        query_vec = self.vectorize(words)
        
        best_similarity = 0.0
        best_tag = None
        best_responses = []
        
        for vec, tag, responses in self.pattern_vectors:
            sim = self.cosine_similarity(query_vec, vec)
            if sim > best_similarity:
                best_similarity = sim
                best_tag = tag
                best_responses = responses
                
        if best_similarity >= threshold:
            import random
            return {
                "tag": best_tag,
                "similarity": best_similarity,
                "response": random.choice(best_responses)
            }
        return None

# Instantiate and train the local SLM
slm = SimpleSLM()
slm.train("data/brain_data.json")

# Background thread to load the local transformer LLM (offline generative assistant)
def load_huggingface_llm():
    global llm_pipeline, llm_ready
    try:
        import importlib.util
        import torch
        from transformers import pipeline

        print(f"[LLM] Initializing local generative LLM '{model_id}' on CPU...")

        # Only attempt offline model loading when a local model directory exists
        if not os.path.isdir(model_id):
            print(f"[LLM] Local model directory not found for '{model_id}'. Skipping generative LLM load.")
            return

        accelerate_spec = importlib.util.find_spec("accelerate")
        pipeline_kwargs = {
            "model": model_id,
            "dtype": torch.float32,
            "trust_remote_code": False,
            "local_files_only": True
        }

        if accelerate_spec is not None:
            pipeline_kwargs["device_map"] = "auto"
        else:
            pipeline_kwargs["device"] = "cpu"
            print("[LLM] accelerate package not installed. Loading LLM on CPU without device_map.")

        llm_pipeline = pipeline(
            "text-generation",
            **pipeline_kwargs
        )
        llm_ready = True
        print("[LLM] Generative transformer engine online and ready.")
    except Exception as e:
        print(f"[LLM] Error/Warning loading local LLM model: {e}")
        print("[LLM] Running in SLM-Only fallback mode. General chat prompts will fallback to preset greetings.")

# Trigger background loader
threading.Thread(target=load_huggingface_llm, daemon=True).start()

def get_llm_reply(prompt):
    if not llm_ready or llm_pipeline is None:
        return "I am currently loading my secondary cognitive transformer core, Sir. Please allow me a moment."
        
    try:
        # Prompt structure for Qwen instruction following
        messages = [
            {"role": "system", "content": "You are J.A.R.V.I.S., a sleek, polite, and brief AI assistant. Talk to the user as 'Sir', and keep replies to 1 or 2 sentences max."},
            {"role": "user", "content": prompt}
        ]
        
        # Format conversation using the model's chat template
        formatted_prompt = llm_pipeline.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        
        outputs = llm_pipeline(
            formatted_prompt,
            max_new_tokens=90,
            do_sample=True,
            temperature=0.7,
            top_p=0.9
        )
        
        generated_text = outputs[0]["generated_text"]
        
        # Extract response from Qwen Chat prompt syntax
        if "<|im_start|>assistant" in generated_text:
            reply = generated_text.split("<|im_start|>assistant")[-1].strip()
            reply = reply.replace("<|im_end|>", "").strip()
        else:
            reply = generated_text[len(formatted_prompt):].strip()
            
        return reply
    except Exception as e:
        print(f"[LLM] Generation error: {e}")
        return "I encountered a cognitive delay while compiling a response in my local transformers core, Sir."

def query_brain(query_text):
    query_text = query_text.strip()
    if not query_text:
        return {
            "type": "generative",
            "tag": "error",
            "reply": "I didn't receive any input stream, Sir."
        }
        
    # 1. Check local SLM patterns (Instant, zero dependencies)
    prediction = slm.predict(query_text)
    if prediction:
        print(f"[BRAIN] SLM Match tag: {prediction['tag']} (Similarity: {prediction['similarity']:.2f})")
        return {
            "type": "control",
            "tag": prediction["tag"],
            "reply": prediction["response"]
        }
        
    # 2. Fallback to local LLM for full generative AI (offline)
    print(f"[BRAIN] Routing query to Generative LLM fallback: '{query_text}'")
    reply = get_llm_reply(query_text)
    return {
        "type": "generative",
        "tag": "generative_chat",
        "reply": reply
    }
