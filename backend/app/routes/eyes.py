from flask import Blueprint, request
from app.ml.ml_service import ml_service
from app.utils.responses import ok, error

bp = Blueprint("eyes", __name__, url_prefix="/api/patients/<int:patient_id>/eyes")

@bp.post("/predict")
def predict_eye_metrics(patient_id):
    # Ensure a file asset named 'file' or 'image' was submitted in the form request
    if 'image' not in request.files:
        return error("No image file provided in the 'image' key form parameter.", 400)
        
    image_file = request.files['image']
    
    if image_file.filename == '':
        return error("Selected file is empty.", 400)
        
    try:
        # Read the raw file stream into binary bytes directly
        raw_bytes = image_file.read()
        
        # Send byte block straight to the service pipeline
        analysis_result = ml_service.predict_glaucoma_segmentation(raw_bytes)
        
        return ok(analysis_result, "Image segmentation processed successfully.")
        
    except Exception as e:
        return error(f"An error occurred during inference: {str(e)}", 500)