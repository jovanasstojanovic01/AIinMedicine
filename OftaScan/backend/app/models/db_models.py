
from datetime import datetime
from app.extensions import db



#Tabela pacijenata
class Pacijent(db.Model):
    __tablename__ = "table_patients"

    patient_id        = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name        = db.Column(db.String(100), nullable=False)
    last_name         = db.Column(db.String(100), nullable=False)
    gender            = db.Column(db.Enum("M", "F"), nullable=False)
    birth_date        = db.Column(db.Date, nullable=False)
    # Debljina rožnjače
    cct               = db.Column(db.Float)
    glaucoma_category = db.Column(db.Enum("None", "ACG", "OAG", name="glaucoma_categories"))

    
    pregledi = db.relationship("Pregled", back_populates="pacijent", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Pacijent {self.patient_id}: {self.first_name} {self.last_name}>"




#Tabela pregleda
class Pregled(db.Model):
    __tablename__ = "table_exams"

    exam_id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id           = db.Column(db.Integer, db.ForeignKey("table_patients.patient_id"), nullable=False)
    #Redni broj posete po pacijentu
    visit_number         = db.Column(db.Integer, nullable=False)
    exam_date            = db.Column(db.Date, nullable=False)

    # Intraokularni pritisak desnog oka
    od_iop                = db.Column(db.Float)
    #Dijagnoza desnog oka
    od_diagnosis=db.Column(db.Enum("Glaucoma Suspect / Positive","Healthy"), nullable=True)
    #VF matrica desnog oka
    od_vf_matrix = db.Column(db.Text, nullable=True)
    #Naziv originalnog XML fajl perimetrije desnog oka
    od_vf_file = db.Column(db.String(255), nullable=True)
    od_multimedia_id = db.Column(db.Integer, db.ForeignKey("table_multimedia.multimedia_id"), nullable=True)
    #Predikcija VF_mean za desno oko na sledećoj poseti
    od_next_vf_mean_pred = db.Column(db.Float, nullable=True)

    #Intraokularni pritisak levog oka
    os_iop                = db.Column(db.Float)
    #Dijagnoza levog oka
    os_diagnosis=db.Column(db.Enum("Glaucoma Suspect / Positive","Healthy"), nullable=True)
    #VF matrica levog oka
    os_vf_matrix = db.Column(db.Text, nullable=True)
    #Naziv originalnog XML fajl perimetrije levog oka
    os_vf_file = db.Column(db.String(255), nullable=True)
    os_multimedia_id = db.Column(db.Integer, db.ForeignKey("table_multimedia.multimedia_id"), nullable=True)

    #Predikcija VF_mean za levo oko na sledećoj poseti
    os_next_vf_mean_pred = db.Column(db.Float, nullable=True)

    
    physician_comment    = db.Column(db.Text)
    therapy              = db.Column(db.Text)

    
    pacijent    = db.relationship("Pacijent", back_populates="pregledi")
    od_multimedija = db.relationship("PregledMultimedija", foreign_keys=[od_multimedia_id], cascade="all, delete-orphan", single_parent=True)
    os_multimedija = db.relationship("PregledMultimedija", foreign_keys=[os_multimedia_id], cascade="all, delete-orphan", single_parent=True)
    def __repr__(self):
        return f"<Pregled {self.exam_id} pacijent={self.patient_id} poseta={self.visit_number}>"




#Fundus slike
class PregledMultimedija(db.Model):
    __tablename__ = "table_multimedia"

    multimedia_id      = db.Column(db.Integer, primary_key=True, autoincrement=True)
    image_path      = db.Column(db.String(255), nullable=True)
    #Klinicki parametri izvuceni UNet modelom
    vcdr            = db.Column(db.Float)
    hcdr            = db.Column(db.Float)
    acdr            = db.Column(db.Float)
    rim_area_pixels = db.Column(db.Float)