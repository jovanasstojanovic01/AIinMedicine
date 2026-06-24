# app/schemas.py
import json
from marshmallow import fields, validate, validates, ValidationError, pre_load
from app.extensions import ma
from app.models.db_models import (
    Patient, Visit, EyeExamination, ProgressionPrediction
)

LATERALITY_CHOICES = ["OD", "OS"]
GENDER_CHOICES = ["M", "F", "Other"]
VISIT_TYPE_CHOICES = ["INITIAL", "CONTROL"]


# ─────────────────────────────────────────────────────────────────────────────
# Patient Schema
# ─────────────────────────────────────────────────────────────────────────────
class PatientSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Patient
        load_instance = True
        exclude = ("predictions", "visits") # Ne šaljemo celu istoriju kroz bazični šablon pacijenta

    jmbg           = fields.Str(required=True, validate=validate.Length(equal=13))
    first_name     = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    last_name      = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    birth_year     = fields.Int(required=True, validate=validate.Range(min=1900, max=2026))
    gender         = fields.Str(validate=validate.OneOf(GENDER_CHOICES))
    family_history = fields.Str(allow_none=True)
    general_notes  = fields.Str(allow_none=True)


# ─────────────────────────────────────────────────────────────────────────────
# Eye Examination Schema (Podaci za jedno oko unutar pregleda)
# ─────────────────────────────────────────────────────────────────────────────
class EyeExaminationSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = EyeExamination
        load_instance = True
        include_fk = True # Uključujemo visit_id ako zatreba
        exclude = ("cfp_image_path", "disc_mask_path", "cup_mask_path") # Sakrivamo sirove putanje na disku

    laterality       = fields.Str(required=True, validate=validate.OneOf(LATERALITY_CHOICES))
    iop              = fields.Float(allow_none=True)
    vcdr             = fields.Float(allow_none=True)
    glaucoma_suspect = fields.Boolean(allow_none=True)
    oct_rnfl_mean    = fields.Float(allow_none=True)
    vf_data          = fields.Raw(allow_none=True) # Može lista, a u bazi je Text

    @validates("vf_data")
    def validate_vf(self, value):
        if value is None or value == "":
            return
        
        # Ako stigne kao JSON string, parsiraj ga za proveru
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise ValidationError("vf_data must be a valid JSON array of integers.")
                
        if not isinstance(value, list):
            raise ValidationError("vf_data must be a list (array).")
            
        if len(value) != 61:
            raise ValidationError(f"vf_data must have exactly 61 values (got {len(value)}).")

    @pre_load
    def coerce_vf_to_string(self, data, **kwargs):
        """Pre nego što ode u bazu, ako je niz, pretvori ga u JSON string."""
        if "vf_data" in data and isinstance(data["vf_data"], list):
            data["vf_data"] = json.dumps(data["vf_data"])
        return data


# ─────────────────────────────────────────────────────────────────────────────
# Visit Schema (Krovni pregled koji ugnježđuje podatke za oba oka)
# ─────────────────────────────────────────────────────────────────────────────
class VisitSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Visit
        load_instance = True
        include_fk = True

    visit_type          = fields.Str(required=True, validate=validate.OneOf(VISIT_TYPE_CHOICES))
    clinical_conclusion = fields.Str(allow_none=True)
    therapy             = fields.Str(allow_none=True)
    visit_date          = fields.DateTime(dump_only=True)

    # Polja za ugnježđivanje (Nested Relationships)
    # Kada povlačimo pregled, prikazaće nam i podatke o pacijentu i preglede očiju
    patient  = fields.Nested(PatientSchema, dump_only=True)
    eye_data = fields.Nested(EyeExaminationSchema, many=True, dump_only=True)


# ─────────────────────────────────────────────────────────────────────────────
# Progression Prediction Schema (Read-only)
# ─────────────────────────────────────────────────────────────────────────────
class ProgressionPredictionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProgressionPrediction
        load_instance = False # Predikcije pravi isključivo naš ML pipeline

    predicted_at = fields.DateTime(dump_only=True)


# ─────────────────────────────────────────────────────────────────────────────
# Singleton instance za rute
# ─────────────────────────────────────────────────────────────────────────────
patient_schema         = PatientSchema()
patients_schema        = PatientSchema(many=True)

eye_examination_schema = EyeExaminationSchema()
eye_examinations_schema = EyeExaminationSchema(many=True)

visit_schema           = VisitSchema()
visits_schema          = VisitSchema(many=True)

prediction_schema      = ProgressionPredictionSchema()
predictions_schema     = ProgressionPredictionSchema(many=True)