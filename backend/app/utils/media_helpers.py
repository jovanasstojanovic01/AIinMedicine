
import os
import uuid

def generisi_jedinstveno_ime(original_filename):
    if not original_filename:
        return None
        
    
    _, ekstenzija = os.path.splitext(original_filename)
    ekstenzija = ekstenzija.lower()
    
    
    jedinstveni_id = str(uuid.uuid4())
    
    return f"{jedinstveni_id}{ekstenzija}"
def get_mask_filename(original_filename):
    if not original_filename:
        return None
    
    
    base_name, _ = os.path.splitext(original_filename)
    
    return f"{base_name}_mask.png"