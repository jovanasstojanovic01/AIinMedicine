
import os
from flask import Blueprint, current_app, send_from_directory
from app.utils.media_helpers import get_mask_filename
from app.utils.responses import not_found

bp = Blueprint("media", __name__, url_prefix="/api/media")

@bp.get("/image/<string:filename>")
def serve_patient_image(filename):
    folder = current_app.config['IMAGES_FOLDER']
    if not os.path.exists(os.path.join(folder, filename)):
        return not_found("Tražena slika ne postoji na serveru.")
        
    return send_from_directory(folder, filename)

@bp.get("/mask/<string:original_filename>")
def serve_patient_mask(original_filename):
    mask_filename = get_mask_filename(original_filename)

    folder = current_app.config['MASKS_FOLDER']
    if not os.path.exists(os.path.join(folder, mask_filename)):
        return not_found("Maska za traženu sliku još uvek nije generisana.")
        
    return send_from_directory(folder, mask_filename)