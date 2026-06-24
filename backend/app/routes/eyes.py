"""
Eye routes
==========
GET    /api/patients/<pid>/eyes          – list eyes for a patient
POST   /api/patients/<pid>/eyes          – add an eye record
GET    /api/patients/<pid>/eyes/<eid>    – get single eye with visits
DELETE /api/patients/<pid>/eyes/<eid>    – delete eye (cascades)
"""

from flask import Blueprint, request
from marshmallow import ValidationError

from app.extensions import db
from app.models.db_models import Patient, Eye
from app.models.schemas import eye_schema, eyes_schema
from app.utils.responses import ok, created, error, not_found, conflict

bp = Blueprint("eyes", __name__, url_prefix="/api/patients/<int:patient_id>/eyes")


def _get_patient_or_404(patient_id):
    p = Patient.query.get(patient_id)
    if p is None:
        return None, not_found("Patient")
    return p, None


def _get_eye_or_404(patient_id, eye_id):
    eye = Eye.query.filter_by(id=eye_id, patient_id=patient_id).first()
    if eye is None:
        return None, not_found("Eye")
    return eye, None


@bp.get("")
def list_eyes(patient_id):
    patient, err = _get_patient_or_404(patient_id)
    if err:
        return err
    return ok(eyes_schema.dump(patient.eyes))


@bp.post("")
def create_eye(patient_id):
    patient, err = _get_patient_or_404(patient_id)
    if err:
        return err

    json_data = request.get_json(silent=True) or {}
    json_data["patient_id"] = patient_id

    # Enforce one eye per laterality per patient
    lat = json_data.get("laterality", "").upper()
    existing = Eye.query.filter_by(patient_id=patient_id, laterality=lat).first()
    if existing:
        return conflict(f"Eye '{lat}' already exists for this patient.")

    try:
        eye = eye_schema.load(json_data, session=db.session)
    except ValidationError as exc:
        return error("Validation failed.", 422, exc.messages)

    db.session.add(eye)
    db.session.commit()
    return created(eye_schema.dump(eye), "Eye record created.")


@bp.get("/<int:eye_id>")
def get_eye(patient_id, eye_id):
    eye, err = _get_eye_or_404(patient_id, eye_id)
    if err:
        return err

    data = eye_schema.dump(eye)
    # Include visit summaries
    data["has_baseline"]    = eye.baseline_visit is not None
    data["followup_count"]  = len(eye.followup_visits)
    return ok(data)


@bp.delete("/<int:eye_id>")
def delete_eye(patient_id, eye_id):
    eye, err = _get_eye_or_404(patient_id, eye_id)
    if err:
        return err
    db.session.delete(eye)
    db.session.commit()
    return ok(message="Eye record deleted.")