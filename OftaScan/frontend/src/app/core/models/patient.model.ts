export interface Patient {
  id?: number;
  first_name: string;
  last_name: string;
  gender: 'M' | 'F';
  birth_date: string; // YYYY-MM-DD format
  cct: number | null; // debljina rožnjače
  glaucoma_category: 'OAG' | 'ACG' | string | null; // Open-angle / Angle-closure glaucoma
}

export interface ProgressionPrediction {
  progression_risk: number;
  status: string;
}
