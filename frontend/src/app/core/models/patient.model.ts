// patient.model.ts
export interface Patient {
  id?: number;
  first_name: string;
  last_name: string;
  gender: 'M' | 'F';
  birth_date: string; // YYYY-MM-DD
  cct: number | null; // Central Corneal Thickness
  glaucoma_category: 'OAG' | 'ACG' | string | null; // Open-angle / Angle-closure glaucoma
}

export interface ProgressionPrediction {
  // Prilagodi polja strukturi koju tvoj GRU/XGBoost model vraća
  progression_risk: number;
  status: string;
}
