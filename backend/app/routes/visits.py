# app/routes/visits.py
from flask import Blueprint, request
from app.extensions import db
from app.models.models import Patient, Visit, EyeExamination
from app.utils.responses import ok, created, error, not_found
from app.ml.ml_service import ml_service # Tvoj servis za U-Net i GRU

bp = Blueprint("visits", __name__, url_prefix="/api/visits")

# 1. PRIKAZ SVIH PREGLEDA U KLINICI (Prva strana)
@bp.get("")
def list_all_visits():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    
    pagination = Visit.query.order_by(Visit.visit_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    visits_data = []
    for v in pagination.items:
        visits_data.append({
            "visit_id": v.id,
            "patient_name": f"{v.patient.first_name} {v.patient.last_name}",
            "jmbg": v.patient.jmbg,
            "visit_type": v.visit_type,
            "date": v.visit_date.strftime("%Y-%m-%d %H:%M")
        })
        
    return ok({
        "visits": visits_data,
        "total": pagination.total,
        "pages": pagination.pages,
        "page": page
    })

# 2. DODAVANJE INICIJALNOG PREGLEDA (Novi pacijent + slike)
@bp.post("/initial")
def create_initial_visit():
    # Pošto šaljemo i slike i tekst, frontend koristi multipart/form-data umesto JSON-a
    form = request.form
    files = request.files

    # Provera JMBG-a da se izbegnu duplikati
    if Patient.query.filter_by(jmbg=form.get("jmbg")).first():
        return error("Patient with this JMBG already exists.", 400)

    try:
        # Kreiramo pacijenta
        new_patient = Patient(
            jmbg=form.get("jmbg"),
            first_name=form.get("first_name"),
            last_name=form.get("last_name"),
            birth_year=int(form.get("birth_year")),
            gender=form.get("gender"),
            family_history=form.get("family_history"),
            general_notes=form.get("general_notes")
        )
        db.session.add(new_patient)
        db.session.flush() # Dobijamo new_patient.id pre commit-a

        # Kreiramo krovni pregled
        visit = Visit(
            patient_id=new_patient.id,
            visit_type="INITIAL",
            clinical_conclusion=form.get("clinical_conclusion"),
            therapy=form.get("therapy")
        )
        db.session.add(visit)
        db.session.flush()

        # Obrada očiju i aktivacija RefugeUNet modela
        for lat in ["OD", "OS"]:
            # Izvlačimo pritisak i fajl slike specifično za levo/desno oko
            iop_val = form.get(f"iop_{lat}", type=float)
            image_file = files.get(f"image_{lat}")

            eye_exam = EyeExamination(visit_id=visit.id, laterality=lat, iop=iop_val)

            if image_file:
                # 1. Pokrećemo tvoj RefugeUNet model nad sirovim bajtovima slike
                ml_result = ml_service.predict_glaucoma_segmentation(image_file.read())
                
                # 2. Upisujemo automatski izvučene vrednosti modela u bazu
                eye_exam.vcdr = ml_result["vcdr"]
                eye_exam.glaucoma_suspect = (ml_result["status"] == "High Risk / Glaucoma Suspect")
                
                # Ovde bi išao kod za čuvanje slike na disk i upis putanje
                eye_exam.cfp_image_path = f"uploads/{visit.id}_{lat}.jpg"

            db.session.add(eye_exam)

        db.session.commit()
        return created({"visit_id": visit.id}, "Initial visit and patient recorded successfully.")

    except Exception as e:
        db.session.rollback()
        return error(f"Database error: {str(e)}", 500)

# 3. DODAVANJE KONTROLNOG PREGLEDA (Za postojećeg pacijenta)
@bp.post("/control")
def create_control_visit():
    form = request.form
    files = request.files
    
    patient = Patient.query.filter_by(jmbg=form.get("jmbg")).first()
    if not patient:
        return not_found("Patient with given JMBG not found.")

    try:
        visit = Visit(
            patient_id=patient.id,
            visit_type="CONTROL",
            clinical_conclusion=form.get("clinical_conclusion"),
            therapy=form.get("therapy")
        )
        db.session.add(visit)
        db.session.flush()

        for lat in ["OD", "OS"]:
            iop_val = form.get(f"iop_{lat}", type=float)
            image_file = files.get(f"image_{lat}")

            eye_exam = EyeExamination(visit_id=visit.id, laterality=lat, iop=iop_val)
            
            if image_file:
                ml_result = ml_service.predict_glaucoma_segmentation(image_file.read())
                eye_exam.vcdr = ml_result["vcdr"]
                eye_exam.glaucoma_suspect = (ml_result["status"] == "High Risk / Glaucoma Suspect")

            db.session.add(eye_exam)

        db.session.commit()
        return created({"visit_id": visit.id}, "Control visit recorded successfully.")
        
    except Exception as e:
        db.session.rollback()
        return error(f"Error recording control visit: {str(e)}", 500)