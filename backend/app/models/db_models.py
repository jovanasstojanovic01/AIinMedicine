# app/models/models.py
from datetime import datetime
from app.extensions import db

# ─────────────────────────────────────────────────────────────────────────────
# Patient
# ─────────────────────────────────────────────────────────────────────────────
class Patient(db.Model):
    __tablename__ = "patients"

    id            = db.Column(db.Integer, primary_key=True)
    jmbg          = db.Column(db.String(13), unique=True, nullable=False, index=True) # Ključno za brzu pretragu
    first_name    = db.Column(db.String(100), nullable=False)
    last_name     = db.Column(db.String(100), nullable=False)
    birth_year    = db.Column(db.Integer, nullable=False) # Korisnik unosi godište
    gender        = db.Column(db.String(10))              # 'M' | 'F' | 'Other'
    family_history= db.Column(db.Text)                    # Porodična anamneza
    general_notes = db.Column(db.Text)                    # Opšte napomene
    
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    visits      = db.relationship("Visit", back_populates="patient", cascade="all, delete-orphan")
    predictions = db.relationship("ProgressionPrediction", back_populates="patient", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Patient {self.jmbg} - {self.first_name} {self.last_name}>"


# ─────────────────────────────────────────────────────────────────────────────
# Visit (Pregled - Inicijalni ili Kontrola)
# ─────────────────────────────────────────────────────────────────────────────
class Visit(db.Model):
    __tablename__ = "visits"

    id             = db.Column(db.Integer, primary_key=True)
    patient_id     = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    visit_type     = db.Column(db.String(20), nullable=False) # 'INITIAL' | 'CONTROL'
    visit_date     = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Lekarski unosi zajednički za ceo pregled
    clinical_conclusion = db.Column(db.Text) # Klinički zaključak lekara
    therapy             = db.Column(db.Text) # Terapija

    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    patient  = db.relationship("Patient", back_populates="visits")
    eye_data = db.relationship("EyeExamination", back_populates="visit", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Visit {self.id} type={self.visit_type} patient={self.patient_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# Eye Examination (Podaci o konkretnom oku unutar jednog pregleda)
# ─────────────────────────────────────────────────────────────────────────────
class EyeExamination(db.Model):
    __tablename__ = "eye_examinations"

    id            = db.Column(db.Integer, primary_key=True)
    visit_id      = db.Column(db.Integer, db.ForeignKey("visits.id"), nullable=False)
    laterality    = db.Column(db.String(2), nullable=False)  # 'OD' (Desno) | 'OS' (Levo)
    
    # Klinička merenja uneta ručno
    iop           = db.Column(db.Float)  # Intraokularni pritisak
    cfp_image_path = db.Column(db.String(512)) # Putanja do fundus slike

    # Parametri koje izvlači RefugeUNet iz slike automatski
    vcdr            = db.Column(db.Float)
    disc_mask_path  = db.Column(db.String(512))
    cup_mask_path   = db.Column(db.String(512))
    glaucoma_suspect = db.Column(db.Boolean) # Evaluacija modela (Ima/Nema)

    # Dodatni GRAPE/LSTM parametri (opciono, ako se unose)
    vf_data         = db.Column(db.Text)   # JSON string za visual field 61-point
    oct_rnfl_mean   = db.Column(db.Float)  # Iz trening fajlova

    # Relationships
    visit = db.relationship("Visit", back_populates="eye_data")

    __table_args__ = (
        db.UniqueConstraint("visit_id", "laterality", name="uq_visit_eye"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Progression Prediction (Rezultat LSTM+XGBoost ansambla)
# ─────────────────────────────────────────────────────────────────────────────
class ProgressionPrediction(db.Model):
    __tablename__ = "progression_predictions"

    id              = db.Column(db.Integer, primary_key=True)
    patient_id      = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    laterality      = db.Column(db.String(2), nullable=False) # Predikcija progresije za levo ili desno oko
    
    ensemble_prob   = db.Column(db.Float)  # Finalni skor (0.4 GRU + 0.6 XGB)
    predicted_label = db.Column(db.Integer) # 0 = stabilno, 1 = progresija
    num_visits_used = db.Column(db.Integer)
    predicted_at    = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", back_populates="predictions")