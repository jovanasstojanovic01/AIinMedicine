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

from app.extensions import db
from app.models.db_models import Patient
from app.models.schemas import patient_schema, patients_schema
from app.utils.responses import ok, created, error, not_found

bp = Blueprint("patients", __name__, url_prefix="/api/patients")


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