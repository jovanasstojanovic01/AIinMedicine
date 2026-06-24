"""
Marshmallow schemas for request validation and response serialization.
"""

import json
from marshmallow import fields, validate, validates, ValidationError, pre_load, post_load
from app.extensions import ma
from app.models.db_models import (
    Patient, Eye, BaselineVisit, FollowUpVisit, ProgressionPrediction
)

LATERALITY_CHOICES = ["OD", "OS"]
GENDER_CHOICES = ["M", "F", "Other"]


# ─────────────────────────────────────────────────────────────────────────────
# Patient
# ─────────────────────────────────────────────────────────────────────────────
class PatientSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Patient
        load_instance = True
        exclude = ("predictions",)

    first_name    = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    last_name     = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    date_of_birth = fields.Date(required=True)
    gender        = fields.Str(validate=validate.OneOf(GENDER_CHOICES))

    # Nested: show brief eye summaries on GET
    eyes = fields.Nested(lambda: EyeBriefSchema(), many=True, dump_only=True)


class EyeBriefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Eye
        fields = ("id", "laterality", "created_at")


# ─────────────────────────────────────────────────────────────────────────────
# Eye
# ─────────────────────────────────────────────────────────────────────────────
class EyeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Eye
        load_instance = True

    laterality = fields.Str(required=True, validate=validate.OneOf(LATERALITY_CHOICES))
    patient_id = fields.Int(required=True, load_only=True)


# ─────────────────────────────────────────────────────────────────────────────
# Shared visit mixin helper
# ─────────────────────────────────────────────────────────────────────────────
def _vf_data_field():
    """Returns a field that accepts a JSON array of 61 integers or a raw list."""
    return fields.Raw(
        metadata={"description": "Visual field data: list of 61 integers or JSON string"}
    )


class _VisitSchemaMixin:
    iop             = fields.Float()
    vcdr            = fields.Float()
    hcdr            = fields.Float()
    acdr            = fields.Float()
    rim_area_pixels = fields.Float()
    vf_data         = fields.Raw()   # accepted as list[int] or JSON string

    @validates("vf_data")
    def validate_vf(self, value):
        if value is None:
            return
        # Accept both a Python list and a pre-serialised JSON string
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise ValidationError("vf_data must be a JSON array of integers.")
        if not isinstance(value, list):
            raise ValidationError("vf_data must be a list.")
        if len(value) != 61:
            raise ValidationError(f"vf_data must have exactly 61 values (got {len(value)}).")

    @pre_load
    def coerce_vf_to_string(self, data, **kwargs):
        """Store vf_data internally as a JSON string in the DB."""
        if "vf_data" in data and isinstance(data["vf_data"], list):
            data["vf_data"] = json.dumps(data["vf_data"])
        return data


# ─────────────────────────────────────────────────────────────────────────────
# Baseline Visit
# ─────────────────────────────────────────────────────────────────────────────
class BaselineVisitSchema(_VisitSchemaMixin, ma.SQLAlchemyAutoSchema):
    class Meta:
        model = BaselineVisit
        load_instance = True
        exclude = ("cfp_image_path", "disc_mask_path", "cup_mask_path")

    eye_id             = fields.Int(required=True, load_only=True)
    age                = fields.Float()
    cct                = fields.Float()
    total_visits       = fields.Int()
    progression_status = fields.Str()
    glaucoma_category  = fields.Str()
    oct_rnfl_mean      = fields.Float()
    oct_rnfl_s         = fields.Float()
    oct_rnfl_n         = fields.Float()
    oct_rnfl_i         = fields.Float()
    oct_rnfl_t         = fields.Float()
    acquisition_device = fields.Str()
    image_resolution   = fields.Str()


# ─────────────────────────────────────────────────────────────────────────────
# Follow-up Visit
# ─────────────────────────────────────────────────────────────────────────────
class FollowUpVisitSchema(_VisitSchemaMixin, ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FollowUpVisit
        load_instance = True
        exclude = ("cfp_image_path", "disc_mask_path", "cup_mask_path")

    eye_id         = fields.Int(required=True, load_only=True)
    visit_number   = fields.Int(required=True)
    interval_years = fields.Float()
    acquisition_device = fields.Str()
    image_resolution   = fields.Str()


# ─────────────────────────────────────────────────────────────────────────────
# Progression Prediction (read-only)
# ─────────────────────────────────────────────────────────────────────────────
class ProgressionPredictionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProgressionPrediction
        load_instance = False   # predictions are created by the ML pipeline, not by users


# ─────────────────────────────────────────────────────────────────────────────
# Singleton instances (used in routes)
# ─────────────────────────────────────────────────────────────────────────────
patient_schema        = PatientSchema()
patients_schema       = PatientSchema(many=True)

eye_schema            = EyeSchema()
eyes_schema           = EyeSchema(many=True)

baseline_schema       = BaselineVisitSchema()
baselines_schema      = BaselineVisitSchema(many=True)

followup_schema       = FollowUpVisitSchema()
followups_schema      = FollowUpVisitSchema(many=True)

prediction_schema     = ProgressionPredictionSchema()
predictions_schema    = ProgressionPredictionSchema(many=True)