# OftaScan 👁️

**Softverski sistem za podršku oftalmološkoj dijagnostici i praćenju glaukoma primenom dubokih neuronskih mreža**

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C?logo=pytorch)](https://pytorch.org)
[![Angular](https://img.shields.io/badge/Angular-17-DD0031?logo=angular)](https://angular.io)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📋 Sadržaj

- [O projektu](#o-projektu)
- [Arhitektura sistema](#arhitektura-sistema)
- [Struktura repozitorijuma](#struktura-repozitorijuma)
- [Instalacija i pokretanje](#instalacija-i-pokretanje)
  - [AI servis (Python)](#ai-servis-python)
  - [Backend (Flask)](#backend-flask)
  - [Frontend (Angular)](#frontend-angular)
- [Upotreba](#upotreba)
- [AI modeli](#ai-modeli)
  - [UNet — segmentacija fundus fotografija](#unet--segmentacija-fundus-fotografija)
  - [GRU — predikcija progresije vidnog polja](#gru--predikcija-progresije-vidnog-polja)
- [Dataseti](#dataseti)
- [Rezultati](#rezultati)

---

## O projektu

OftaScan je klinička web aplikacija koja integriše veštačku inteligenciju u oftalmološki dijagnostički tok za pacijente sa glaukomom. Sistem kombinuje dva AI modula:

1. **UNet** — konvoluciona neuralna mreža za automatsku segmentaciju optičkog diska (OD) i optičke šolje (OC) na fundus fotografijama, uz ekstrakciju kliničkih parametara (vCDR, hCDR, aCDR, rim area)
2. **GRU** — rekurentna neuralna mreža za longitudinalnu predikciju prosečne osetljivosti vidnog polja (VF_mean) na sledećoj kliničkoj poseti, na osnovu kompletne istorije pregleda pacijenta

Aplikacija podržava ceo klinički tok: registraciju pacijenta → merenje IOP → upload fundus fotografije → upload XML exporta perimetrije → prikaz AI predikcija lekaru.

---

## Arhitektura sistema

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Angular 17)                 │
│  Dashboard │ Registracija │ Pregled │ Karton pacijenta  │
└─────────────────────┬───────────────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────────────┐
│                   BACKEND (Flask)                        │
│         SQLAlchemy ORM │ REST endpoints                  │
│                                                          │
│  ┌─────────────────┐    ┌───────────────────────────┐   │
│  │  UNet Service   │    │      GRU Service           │   │
│  │ REFUGE2 model   │    │     GRAPE model            │   │
│  │ OD/OC segm.     │    │  VF_mean next-step pred.   │   │
│  └─────────────────┘    └───────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Struktura repozitorijuma

```
OftaScan/
│
├── AI service/                  # Pipeline za trening AI modela
│   ├── REFUGE2/                 # UNet model za segmentaciju
│   │   ├── src/
│   │   │   ├── model.py         # UNet arhitektura
│   │   │   ├── dataset.py       # Dataset loader
│   │   │   └── losses.py        # Dice + BCE loss
│   │   ├── train.py             # Trening UNet-a
│   │   ├── evaluate.py          # Evaluacija segmentacije
│   │   └── config.py            # Hiperparametri
│   │
│   ├── src/
│   │   ├── model.py             # GRU arhitektura
│   │   ├── dataset.py           # Temporal dataset loader
│   │   └── losses.py            # Maskirani MSE loss
│   │
│   ├── data_prep.py             # Priprema kliničkih podataka
│   ├── merge_grape_data.py      # Spajanje GRAPE tabela sa UNet parametrima
│   ├── create_gru_sequences.py  # Kreiranje sekvenci za GRU (next-step)
│   ├── extract_grape_features.py# Ekstrakcija UNet parametara iz GRAPE slika
│   ├── mask_generator.py        # Generisanje maski optičkog diska
│   ├── train.py                 # Trening GRU modela (GRAPE)
│   ├── cross_validate.py        # 5-fold cross-validacija GRU modela
│   └── config.py                # Hiperparametri (hidden_size, lr, epohe...)
│
├── backend/                     # Flask REST API
│   ├── app/
│   │   ├── ml/
│   │   │   ├── architectures/
│   │   │   │   ├── unet.py      # UNet arhitektura za inferensu
│   │   │   │   └── gru.py       # GRU arhitektura za inferensu
│   │   │   └── ml_service.py    # AI servis (segmentacija + predikcija)
│   │   ├── models/
│   │   │   ├── db_models.py     # SQLAlchemy modeli
│   │   │   └── schemas.py       # Marshmallow schemas
│   │   ├── routes/
│   │   │   ├── patients.py      # /api/patients
│   │   │   ├── visits.py        # /api/visits
│   │   │   └── media.py         # /api/media (slike, maske)
│   │   ├── utils/
│   │   │   ├── media_helpers.py
│   │   │   └── responses.py
│   │   ├── __init__.py          # Flask app factory
│   │   ├── config.py
│   │   └── extensions.py
│   ├── requirements.txt
│   └── run.py
│
└── frontend/                    # Angular 17 aplikacija
    └── src/app/
        ├── components/
        │   ├── dashboard/           # Lista pacijenata + pretraga
        │   ├── patient-detail/      # Karton pacijenta + istorija pregleda
        │   ├── examination-form/    # 4-koračni stepper za novi pregled
        │   └── new-patient-form/    # 5-koračni stepper za registraciju
        └── core/
            └── http/
                ├── patient.service.ts
                └── visit.service.ts
```

---

## Instalacija i pokretanje

### Preduslovi

- Python 3.10+
- Node.js 18+
- Angular CLI 17+

---

### AI servis (Python)

> Ovaj korak je potreban samo ako treniraš modele iznova. Ukoliko već imaš gotove checkpoint fajlove (`gru_best_overall.pth`, `scaler.pkl`, UNet checkpoint), pređi direktno na backend.

```bash
cd "AI service"
pip install -r requirements.txt
```

**Redosled pokretanja pipeline-a:**

```bash
# 1. Spajanje GRAPE tabela sa UNet-ekstrahovanim parametrima
python merge_grape_data.py

# 2. Ekstrakcija UNet parametara iz fundus slika (potreban GRAPE dataset)
python extract_grape_features.py

# 3. Kreiranje GRU sekvenci za trening (next-step VF_mean predikcija)
python create_gru_sequences.py

# 4. Trening GRU modela
python train.py
```

**Trening UNet modela (REFUGE2):**

```bash
cd REFUGE2
python train.py
```

Checkpoint-i se snimaju u `checkpoints/` folder.

---

### Backend (Flask)

```bash
cd backend
pip install -r requirements.txt
```

Pre pokretanja, postavi checkpoint putanje u `app/config.py`:

```python
GRU_MODEL_PATH   = "path/to/gru_best_overall.pth"
SCALER_PATH      = "path/to/scaler.pkl"
UNET_MODEL_PATH  = "path/to/unet_checkpoint.pth"
```

Pokreni server:

```bash
python run.py
```

Server se pokreće na `http://127.0.0.1:5000`.

---

### Frontend (Angular)

```bash
cd frontend
npm install
ng serve
```

Aplikacija se otvara na `http://localhost:4200`.

> API base URL je hardkodovan na `http://127.0.0.1:5000/api` u servisima. Ako backend radi na drugom portu, izmeni u `visit.service.ts` i `patient.service.ts`.

---

## Upotreba

### Registracija novog pacijenta

Kliknuti **"Register new patient"** na dashboardu. Registracija se odvija kroz **5 koraka**:

| Korak | Sadržaj |
|-------|---------|
| 1. Patient Info | Ime, prezime, datum rođenja, pol |
| 2. IOP | Intraokularni pritisak za OD i OS |
| 3. Fundus Images | Upload fundus fotografija (opciono) |
| 4. Visual Field | Upload XML exporta perimetrije (obavezno) |
| 5. Review & Notes | Pregled rezultata, CCT, kategorija glaukoma, komentar i terapija |

Na koraku 5 sistem automatski:
- Prikazuje fundus slike sa segmentacionom maskom (toggle)
- Prikazuje tabelu vrednosti vidnog polja (61 lokacija, kolorna kodiranost)
- Pokreće GRU predikciju i prikazuje očekivani VF_mean na sledećoj poseti

### Novi pregled za postojećeg pacijenta

Kliknuti ikonu **➕** pored pacijenta u tabeli. Pregled se odvija kroz **4 koraka**:

| Korak | Sadržaj |
|-------|---------|
| 1. IOP | Merenje pritiska |
| 2. Fundus Images | Upload fotografija (opciono) |
| 3. Visual Field | Upload XML perimetrije (obavezno za svako oko koje ima sliku) |
| 4. Review & Notes | AI predikcija, VF tabela, komentar lekara, terapija |

### Karton pacijenta

Otvara se klikom na ikonu **👤**. Prikazuje:
- Osnovne podatke pacijenta
- Listu svih pregleda (hronološki, najnoviji na vrhu)
- Za svaki selektovani pregled: slike, masku, parametre oka, VF tabelu i AI predikciju

---

## AI modeli

### UNet — segmentacija fundus fotografija

**Dataset:** [REFUGE2](https://refuge.grand-challenge.org/)

**Arhitektura:** Encoder-decoder sa skip konekcijama, 4 nivoa dubine

```
Ulaz: fundus fotografija (512×512)
Izlaz: maska (3 klase — pozadina / OD / OC)
```

**Ekstrahovani klinički parametri iz maske:**
- `vCDR` — vertikalni Cup-to-Disc Ratio
- `hCDR` — horizontalni Cup-to-Disc Ratio
- `aCDR` — površinski Cup-to-Disc Ratio
- `Rim_Area_Pixels` — površina neuroretinalnog ruba

---

### GRU — predikcija progresije vidnog polja

**Dataset:** [GRAPE](https://www.nature.com/articles/s41597-023-02424-4) — 263 oka, 1115 follow-up zapisa

**Arhitektura:** GRU sa `hidden_size=64`, `dropout=0.3`

**Zadatak:** Next-step predikcija — na osnovu istorije poseta `0..t`, model predviđa `VF_mean` na poseti `t+1`

**Feature-i po poseti (7 dimenzija):**

| Feature | Opis |
|---------|------|
| `IOP_corrected` | Korigovani intraokularni pritisak |
| `vCDR` | Vertikalni CDR (iz UNet segmentacije) |
| `hCDR` | Horizontalni CDR |
| `aCDR` | Površinski CDR |
| `Rim_Area_Pixels` | Površina neuroretinalnog ruba |
| `Interval_Years` | Vreme od prethodne posete (u godinama) |
| `VF_mean` | Prosečna VF senzitivnost te posete (proxy MD) |

**Izlaz:** Predviđeni `VF_mean` na sledećoj poseti (u dB-ekv.)

> **Napomena:** `VF_mean` je prosek sirovih VF senzitivnosti isključujući slepe tačke (vrednost −1 u GRAPE datasetu). Nije identičan sa kliničkim MD, koji bi zahtevao starosno-normirane TD vrednosti.

---

## Dataseti

| Dataset | Namena | Link |
|---------|--------|------|
| **REFUGE2** | Trening UNet modela | [grand-challenge.org](https://refuge.grand-challenge.org/) |
| **GRAPE** | Trening GRU modela | [Scientific Data](https://www.nature.com/articles/s41597-023-02424-4) |

Dataseti se **ne nalaze u repozitorijumu** zbog veličine. Preuzeti ih sa navedenih linkova i postaviti prema putanjama u `config.py`.

```python
# AI service/config.py
DATA_DIR  = "./data/GRAPE"    # GRAPE dataset
OUTPUT_DIR = "./outputs"
CHECKPOINT_DIR = "./checkpoints"
REFUGE_MODEL = "./REFUGE2/checkpoints"
```

---

## Rezultati

### GRU model — trening na GRAPE datasetu

| Metrika | Vrednost (best checkpoint, epoha 210) |
|---------|---------------------------------------|
| Val MSE | 3.1418 |
| Val MAE | 1.292 dB-ekv. |
| Val RMSE | 1.797 dB-ekv. |
| Val R² | 0.864 |
| Epoha zaustavljanja | 225 (early stopping, best: 210) |

Trening/validacija podela: **210 / 53 sekvence (oka)**

---

## Tehnički stack

| Komponenta | Tehnologija |
|------------|-------------|
| Frontend | Angular 17, Angular Material |
| Backend | Flask 3.x, SQLAlchemy |
| AI framework | PyTorch 2.x |
| Segmentacija | UNet (REFUGE2) |
| Predikcija | GRU (GRAPE) |
| Baza podataka | SQLite (razvoj) |

---

## Autori

**Jovana Stojanović**  i **Tijana Kvaić**  
Elektronski fakultet Niš  
Predmet: Veštačka inteligencija u medicini
