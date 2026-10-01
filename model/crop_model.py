import os
import joblib
import pandas as pd
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "modelo_recomendacao_safra.joblib")
_model = None

def get_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model

def crop_prev(data: dict) -> dict:
    model = get_model()
    
    n = float(data.get("N", data.get("n_ratio", 0)))
    p = float(data.get("P", data.get("p_ratio", 0)))
    k = float(data.get("K", data.get("k_ratio", 0)))
    temp = float(data.get("temperature", data.get("temperature_forecast", 25.0)))
    humidity = float(data.get("humidity", 70.0))
    rainfall = float(data.get("rainfall", data.get("rain_forecast", data.get("precipitation_forecast", data.get("precipitation", 100.0)))))
    
    input_df = pd.DataFrame([{
        "N": n,
        "P": p,
        "K": k,
        "temperature": temp,
        "humidity": humidity,
        "rainfall": rainfall
    }])
    
    prediction = model.predict(input_df)[0]
    
    probabilities = model.predict_proba(input_df)[0]
    max_idx = int(np.argmax(probabilities))
    confidence = float(probabilities[max_idx])
    
    top_indices = np.argsort(probabilities)[::-1][:3]
    top_recommendations = [
        {"crop": str(model.classes_[idx]), "probability": round(float(probabilities[idx]) * 100, 2)}
        for idx in top_indices if probabilities[idx] > 0.01
    ]
    
    return {
        "crop_recomendation": str(prediction),
        "confidence": round(confidence * 100, 2),
        "top_recommendations": top_recommendations,
        "features": {
            "N": n,
            "P": p,
            "K": k,
            "temperature": temp,
            "humidity": humidity,
            "rainfall": rainfall
        }
    }