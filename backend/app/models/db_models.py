"""
Database models for the Glaucoma Detection & Progression Platform.

Entity relationships
────────────────────
Patient  1──* Eye  1──1 BaselineVisit  1──* FollowUpVisit
                                              └── each visit may have a CFP image
                                                  and stores extracted CDR / VF features
Patient  1──* ProgressionPrediction   (one prediction per eye, re-computed on demand)
"""

from datetime import datetime
from app.extensions import db


# ─────────────────────────────────────────────────────────────────────────────
# Patient
# ─────────────────────────────────────────────────────────────────────────────
class Patient(db.Model):
    __tablename__ = "patients"

    id            = db.Column(db.Integer, primary_key=True)
    first_name    = db.Column(db.String(100), nullable=False)
    last_name     = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender        = db.Column(db.String(10))          # 'M' | 'F' | 'Other'
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    eyes        = db.relationship("Eye", back_populates="patient",
                                  cascade="all, delete-orphan")
    predictions = db.relationship("ProgressionPrediction", back_populates="patient",
                                  cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Patient {self.id} {self.first_name} {self.last_name}>"


# ─────────────────────────────────────────────────────────────────────────────
# Eye  (OD = right / OS = left)
# ─────────────────────────────────────────────────────────────────────────────
class Eye(db.Model):
    __tablename__ = "eyes"

    id            = db.Column(db.Integer, primary_key=True)
    patient_id    = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    laterality    = db.Column(db.String(2), nullable=False)   # 'OD' | 'OS'
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    patient          = db.relationship("Patient", back_populates="eyes")
    baseline_visit   = db.relationship("BaselineVisit", back_populates="eye",
                                       uselist=False, cascade="all, delete-orphan")
    followup_visits  = db.relationship("FollowUpVisit", back_populates="eye",
                                       cascade="all, delete-orphan",
                                       order_by="FollowUpVisit.visit_number")
    predictions      = db.relationship("ProgressionPrediction", back_populates="eye",
                                       cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("patient_id", "laterality", name="uq_patient_eye"),
    )

    def __repr__(self):
        return f"<Eye patient={self.patient_id} {self.laterality}>"


# ─────────────────────────────────────────────────────────────────────────────
# Shared mixin: clinical + VF + CDR columns common to both visit types
# ─────────────────────────────────────────────────────────────────────────────
class VisitMixin:
    """Columns shared by BaselineVisit and FollowUpVisit."""

    # Clinical measurements
    iop           = db.Column(db.Float)           # intra-ocular pressure (mmHg)
    cfp_image_path = db.Column(db.String(512))    # relative path to uploaded CFP image

    # CDR values extracted by RefugeUNet from the CFP
    vcdr          = db.Column(db.Float)
    hcdr          = db.Column(db.Float)
    acdr          = db.Column(db.Float)
    rim_area_pixels = db.Column(db.Float)

    # Visual field — 61-point HFA 24-2 grid stored as a JSON array string
    # e.g. "[21, 22, 20, ...]"
    vf_data       = db.Column(db.Text)            # JSON array of 61 integers

    # Raw segmentation masks paths (optional; set after RefugeUNet runs)
    disc_mask_path = db.Column(db.String(512))
    cup_mask_path  = db.Column(db.String(512))

    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# Baseline Visit
# ─────────────────────────────────────────────────────────────────────────────
class BaselineVisit(VisitMixin, db.Model):
    __tablename__ = "baseline_visits"

    id             = db.Column(db.Integer, primary_key=True)
    eye_id         = db.Column(db.Integer, db.ForeignKey("eyes.id"), nullable=False, unique=True)

    # Extra baseline-only fields from the GRAPE dataset
    age            = db.Column(db.Float)
    cct            = db.Column(db.Float)           # central corneal thickness (µm)
    total_visits   = db.Column(db.Integer)
    progression_status = db.Column(db.String(20))  # ground-truth label (if known)
    glaucoma_category  = db.Column(db.String(100))
    oct_rnfl_mean  = db.Column(db.Float)
    oct_rnfl_s     = db.Column(db.Float)
    oct_rnfl_n     = db.Column(db.Float)
    oct_rnfl_i     = db.Column(db.Float)
    oct_rnfl_t     = db.Column(db.Float)
    acquisition_device = db.Column(db.String(200))
    image_resolution   = db.Column(db.String(50))

    # relationships
    eye = db.relationship("Eye", back_populates="baseline_visit")

    def __repr__(self):
        return f"<BaselineVisit eye={self.eye_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# Follow-up Visit
# ─────────────────────────────────────────────────────────────────────────────
class FollowUpVisit(VisitMixin, db.Model):
    __tablename__ = "followup_visits"

    id             = db.Column(db.Integer, primary_key=True)
    eye_id         = db.Column(db.Integer, db.ForeignKey("eyes.id"), nullable=False)
    visit_number   = db.Column(db.Integer, nullable=False)   # 1, 2, 3 …
    interval_years = db.Column(db.Float)                     # years since baseline
    acquisition_device = db.Column(db.String(200))
    image_resolution   = db.Column(db.String(50))

    # relationships
    eye = db.relationship("Eye", back_populates="followup_visits")

    __table_args__ = (
        db.UniqueConstraint("eye_id", "visit_number", name="uq_eye_visit"),
    )

    def __repr__(self):
        return f"<FollowUpVisit eye={self.eye_id} visit={self.visit_number}>"


# ─────────────────────────────────────────────────────────────────────────────
# Progression Prediction  (result produced by the LSTM+XGBoost ensemble)
# ─────────────────────────────────────────────────────────────────────────────
class ProgressionPrediction(db.Model):
    __tablename__ = "progression_predictions"

    id              = db.Column(db.Integer, primary_key=True)
    patient_id      = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    eye_id          = db.Column(db.Integer, db.ForeignKey("eyes.id"), nullable=False)

    # Ensemble probabilities
    lstm_prob       = db.Column(db.Float)          # LSTM sigmoid output
    xgb_prob        = db.Column(db.Float)          # XGBoost predict_proba output
    ensemble_prob   = db.Column(db.Float)          # (lstm + xgb) / 2
    predicted_label = db.Column(db.Integer)        # 0 = stable, 1 = progressing
    threshold_used  = db.Column(db.Float, default=0.5)

    # How many time-steps were available when this prediction was made
    num_visits_used = db.Column(db.Integer)
    predicted_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    patient = db.relationship("Patient", back_populates="predictions")
    eye     = db.relationship("Eye",     back_populates="predictions")

    def __repr__(self):
        return (f"<ProgressionPrediction eye={self.eye_id} "
                f"prob={self.ensemble_prob:.3f} label={self.predicted_label}>")