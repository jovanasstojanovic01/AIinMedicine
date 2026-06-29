import os
import json
import pandas as pd
from datetime import datetime
from app import create_app
from app.extensions import db
from app.models.db_models import Pacijent, Pregled, PregledMultimedija  



from app.utils.media_helpers import read_vf_xml 

def parsiraj_i_izvuci_niz_iz_fajla(putanja_fajla):
    """
    Pomoćna funkcija koja simulira slanje fajla tvojoj funkciji read_and_save_vf_xml.
    Pošto read_and_save_vf_xml očekuje objekat fajla iz request.files, otvorićemo ga u 'rb' modu.
    """
    if not os.path.exists(putanja_fajla):
        return None
    
    try:
        
        with open(putanja_fajla, 'rb') as f:
            bajtovi_fajla = f.read()
        
        
        vf_niz = read_vf_xml(bajtovi_fajla)
        return vf_niz
    except Exception as e:
        print(f"⚠️ Greška pri čitanju fajla {putanja_fajla}: {str(e)}")
        return None

def pokreni_migraciju():
    app = create_app()
    with app.app_context():
        print("⏳ Kreiranje tabela i brisanje starih podataka...")
        trenutni_dir = os.path.dirname(os.path.abspath(__file__))  
        koren_projekta = os.path.dirname(trenutni_dir)             

        
        seed_db_folder = os.path.join(koren_projekta, "seed_db")
        db.create_all()
        PregledMultimedija.query.delete()
        Pregled.query.delete()
        Pacijent.query.delete()
        db.session.commit()

        
        vf_folder = app.config.get('VF_FOLDER', '../uploads/visual_fields')

        
        print("📥 Učitavanje pacijenata...")
        df_patients = pd.read_excel(os.path.join(seed_db_folder, "table_patients.xlsx"))
        for _, row in df_patients.iterrows():
            pacijent = Pacijent(
                patient_id =int(row['patient_id']),
                first_name=row.get('first_name', 'Pacijent'),
                last_name=row.get('last_name', f"Broj_{row['patient_id']}"),
                gender=row.get('gender'),
                birth_date=datetime.strptime(str(row['birth_date']), "%Y-%m-%d").date() if pd.notna(row.get('birth_date')) else datetime.utcnow().date(),
                cct=float(row['cct']) if pd.notna(row.get('cct')) else 540.0,
                glaucoma_category =row.get('glaucoma_category','None')
            )
            db.session.add(pacijent)
        db.session.flush()

        
        print("📥 Učitavanje pregleda i povezivanje sa VF XML fajlovima...")
        df_exams = pd.read_excel(os.path.join(seed_db_folder, "table_exams.xlsx"))
        df_exams.columns = df_exams.columns.str.strip()
        for _, row in df_exams.iterrows():
            p_id = int(row['patient_id'])
            
            original_visit = int(row['visit_number'])
            xml_visit_idx = original_visit 

            
            ocekivani_xml_od = f"{p_id}_{xml_visit_idx}_OD_VF.xml"
            ocekivani_xml_os = f"{p_id}_{xml_visit_idx}_OS_VF.xml"

            putanja_od = os.path.join(vf_folder, ocekivani_xml_od)
            putanja_os = os.path.join(vf_folder, ocekivani_xml_os)

            
            od_matrix_list = parsiraj_i_izvuci_niz_iz_fajla(putanja_od)
            os_matrix_list = parsiraj_i_izvuci_niz_iz_fajla(putanja_os)

            
            datum_str = row.get('exam_date')
            exam_date_obj = None
            if pd.notna(datum_str):
                try:
                    exam_date_obj = datetime.strptime(str(datum_str), "%Y-%m-%d").date()
                except ValueError:
                    exam_date_obj = datetime.utcnow().date()

            
            pregled = Pregled(
                exam_id=int(row['exam_id']),
                patient_id=p_id,
                visit_number=original_visit, 
                exam_date=exam_date_obj,
                physician_comment =row.get('physician_comment', ''),
                therapy=row.get('therapy', ''),

                od_iop=float(row['od_iop']) if pd.notna(row.get('od_iop')) else None,
                os_iop=float(row['os_iop']) if pd.notna(row.get('os_iop')) else None,
                
                
                od_vf_file=ocekivani_xml_od,
                od_vf_matrix=json.dumps(od_matrix_list) if od_matrix_list else None,
                os_vf_file=ocekivani_xml_os,
                os_vf_matrix=json.dumps(os_matrix_list) if os_matrix_list else None,
            )
            db.session.add(pregled)
        db.session.flush()

        
        print("📥 Učitavanje multimedijalnih podataka (UNet rezultati)...")
        df_multimedia = pd.read_excel(os.path.join(seed_db_folder, "table_multimedia.xlsx"))
        for _, row in df_multimedia.iterrows():
            multimedija = PregledMultimedija(
                multimedia_id=int(row['multimedia_id']),
                exam_id=int(row['exam_id']),
                od_vcdr=float(row['od_vcdr']) if pd.notna(row.get('od_vcdr')) else 0.0,
                os_vcdr=float(row['os_vcdr']) if pd.notna(row.get('os_vcdr')) else 0.0,
                od_hcdr=float(row['od_hcdr']) if pd.notna(row.get('od_hcdr')) else 0.0,
                os_hcdr=float(row['os_hcdr']) if pd.notna(row.get('os_hcdr')) else 0.0,
                od_acdr=float(row['od_acdr']) if pd.notna(row.get('od_acdr')) else 0.0,
                os_acdr=float(row['os_acdr']) if pd.notna(row.get('os_acdr')) else 0.0,
                od_rim_area_pixels=float(row['od_rim_area_pixels']) if pd.notna(row.get('od_rim_area_pixels')) else 0.0,
                os_rim_area_pixels=float(row['os_rim_area_pixels']) if pd.notna(row.get('os_rim_area_pixels')) else 0.0,
                
                od_image=row.get('od_image'),
                os_image=row.get('os_image'),
            )
            db.session.add(multimedija)

        
        db.session.commit()
        print("🚀 Baza podataka je uspešno restrukturirana, migrirana i napunjena sa svim VF matricama!")

if __name__ == "__main__":
    pokreni_migraciju()