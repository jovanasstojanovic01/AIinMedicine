"""
Patient routes
==============
GET    /api/patients           – list all patients (with pagination)
POST   /api/patients           – create a patient
GET    /api/patients/<id>      – retrieve a single patient (with eyes)
PUT    /api/patients/<id>      – update a patient
DELETE /api/patients/<id>      – delete a patient (cascades to eyes / visits)
"""

from flask import Blueprint, request
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from app.ml.ml_service import ml_service
from app.extensions import db
from app.models.db_models import Patient
from app.models.schemas import patient_schema, patients_schema
from app.utils.responses import ok, created, error, not_found

bp = Blueprint("patients", __name__, url_prefix="/api/patients")

@bp.get("/<int:patient_id>/predict-progression")
def evaluate_progression(patient_id):
    # 1. Čitamo pacijenta iz baze podataka
    patient = Patient.query.get(patient_id)
    if patient is None:
        return not_found("Patient")

    # 2. Izvlačimo sve istorijske posete (preglede) pacijenta iz baze.
    # Pretpostavka je da tvoj model Patient ima vezu (relationship) sa posetama,
    # ili da posete izvlačimo preko očiju. Na primer:
    visits = []
    for eye in patient.eyes:
        # Skupljamo sve posete za oba oka ili specifično oko
        for visit in eye.visits:
            visits.append(visit)
            
    # Ako želiš odvojeno po oku (npr. samo za levo ili desno), filtrira se ovde.
    # Sortiramo posete hronološki po datumu (od najstarije ka najnovijoj)
    visits.sort(key=lambda v: v.date)

    if len(visits) == 0:
        return error("Patient has no historical visits recorded in the database.", 400)

    # 3. Pakujemo tačno 5 kolona na kojima je model treniran
    # Zameni nazive polja (iop, vf_md...) sa stvarnim nazivima kolona iz tvoje baze
    sequence_history = []
    for v in visits:
        sequence_history.append([
            float(v.intraocular_pressure),  # Obeležje 1
            float(v.visual_field_md),       # Obeležje 2
            float(v.rnfl_thickness),         # Obeležje 3
            float(v.cup_to_disc_ratio),     # Obeležje 4
            float(v.pachymetry)             # Obeležje 5
        ])

    try:
        prediction = ml_service.predict_progression(mock_sequence_history)
        return ok(prediction, "Patient progression calculation completed successfully.")
    except Exception as e:
        return error(f"Failed to calculate progression ensemble metrics: {str(e)}", 500)
    
@bp.get("")
def list_patients():
    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    search   = request.args.get("search", "").strip()

    q = Patient.query
    if search:
        like = f"%{search}%"
        q = q.filter(
            Patient.first_name.ilike(like) | Patient.last_name.ilike(like)
        )

    pagination = q.order_by(Patient.last_name, Patient.first_name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return ok({
        "patients": patients_schema.dump(pagination.items),
        "total":    pagination.total,
        "pages":    pagination.pages,
        "page":     page,
    })


@bp.post("")
def create_patient():
    json_data = request.get_json(silent=True)
    if not json_data:
        return error("Request body must be JSON.")

    try:
        patient = patient_schema.load(json_data, session=db.session)
    except ValidationError as exc:
        return error("Validation failed.", 422, exc.messages)

    db.session.add(patient)
    db.session.commit()
    return created(patient_schema.dump(patient), "Patient created.")


@bp.get("/<int:patient_id>")
def get_patient(patient_id):
    patient = Patient.query.get(patient_id)
    if patient is None:
        return not_found("Patient")
    return ok(patient_schema.dump(patient))


@bp.put("/<int:patient_id>")
def update_patient(patient_id):
    patient = Patient.query.get(patient_id)
    if patient is None:
        return not_found("Patient")

    json_data = request.get_json(silent=True)
    if not json_data:
        return error("Request body must be JSON.")

    try:
        patient = patient_schema.load(json_data, instance=patient,
                                       session=db.session, partial=True)
    except ValidationError as exc:
        return error("Validation failed.", 422, exc.messages)

    db.session.commit()
    return ok(patient_schema.dump(patient), "Patient updated.")


@bp.delete("/<int:patient_id>")
def delete_patient(patient_id):
    patient = Patient.query.get(patient_id)
    if patient is None:
        return not_found("Patient")

    db.session.delete(patient)
    db.session.commit()
    return ok(message="Patient deleted.")
# app/routes/patients.py (Dodatak postojećem fajlu)

@bp.get("/search")
def search_patients():
    query_param = request.args.get("query", "").strip()
    if not query_param:
        return ok({"results": []})

    # Pretraga: provera da li query odgovara JMBG-u, imenu ili prezimenu
    like_query = f"%{query_param}%"
    matched_patients = Patient.query.filter(
        (Patient.jmbg.like(like_query)) |
        (Patient.first_name.ilike(like_query)) |
        (Patient.last_name.ilike(like_query))
    ).limit(10).all()

    results = []
    for p in matched_patients:
        results.append({
            "patient_id": p.id,
            "jmbg": p.jmbg,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "birth_year": p.birth_year
        })

    return ok({"results": results})