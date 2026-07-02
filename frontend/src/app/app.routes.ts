import { Routes } from '@angular/router';
import { Dashboard } from './components/dashboard/dashboard';
import { PatientDetail } from './components/patient-detail/patient-detail';
import { ExaminationForm } from './components/examination-form/examination-form';
import { NewPatientForm } from './components/new-patient-form/new-patient-form';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: Dashboard },
  { path: 'patient/:id', component: PatientDetail },
  // New exam for existing patient — patient_id comes from the dashboard row button
  { path: 'new-exam/:patientId', component: ExaminationForm },
  // New patient registration + first exam
  { path: 'new-patient', component: NewPatientForm },
  { path: '**', redirectTo: 'dashboard' },
];