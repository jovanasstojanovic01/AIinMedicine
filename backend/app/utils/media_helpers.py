
import os
import uuid
import xml.etree.ElementTree as ET

from flask import current_app, json

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
def read_vf_xml(xml_bytes):
    root = ET.fromstring(xml_bytes)


    vf_niz = []
    for value_tag in root.findall(".//RawValues/Value"):
        vf_niz.append(int(value_tag.text))
        
    
    if len(vf_niz) != 61:
        raise ValueError(f"Greška: Očekivan 61 parametar iz Octopus fajla, dobijeno {len(vf_niz)}.")

    return vf_niz
def read_and_save_vf_xml(xml_file):
    if not xml_file or xml_file.filename == '':
        return

    unikatno_ime=generisi_jedinstveno_ime(xml_file.filename)
    putanja_za_cuvanje = os.path.join(current_app.config['VF_FOLDER'], unikatno_ime)
    xml_file.save(putanja_za_cuvanje)
    xml_file.seek(0)  
    xml_bytes=xml_file.read()

    vf_niz = read_vf_xml(xml_bytes)

    return unikatno_ime, vf_niz