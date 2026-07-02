import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatSelectModule } from '@angular/material/select';

import { PatientService } from '../../core/http/patient.service';
import { VisitService } from '../../core/http/visit.service';

@Component({
  selector: 'app-new-patient-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatSelectModule,
  ],
  templateUrl: './new-patient-form.html',
  styleUrls: ['./new-patient-form.scss'],
})
export class NewPatientForm implements OnInit {
  form!: FormGroup;

  imageODFile: File | null = null;
  imageODName = '';
  imageOSFile: File | null = null;
  imageOSName = '';

  vfODFile: File | null = null;
  vfODName = '';
  vfOSFile: File | null = null;
  vfOSName = '';

  saving = false;
  statusMsg = '';
  statusType: 'success' | 'error' = 'success';

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private patientService: PatientService,
    private visitService: VisitService,
  ) {}

  ngOnInit(): void {
    this.form = this.fb.group({
      // Podaci o pacijentu
      first_name:        ['', Validators.required],
      last_name:         ['', Validators.required],
      birth_date:        ['', Validators.required],
      gender:            ['', Validators.required],
      cct:               ['', Validators.required],
      glaucoma_category: ['None', Validators.required],
      // Inicijalni pregled
      od_iop:            ['', [Validators.required, Validators.min(0)]],
      os_iop:            ['', [Validators.required, Validators.min(0)]],
      physician_comment: [''],
      therapy:           [''],
    });
  }

  onImageSelected(event: any, eye: 'OD' | 'OS'): void {
    const file: File = event.target.files[0];
    if (!file) return;
    if (eye === 'OD') { this.imageODFile = file; this.imageODName = file.name; }
    else              { this.imageOSFile = file; this.imageOSName = file.name; }
  }

  onVfSelected(event: any, eye: 'OD' | 'OS'): void {
    const file: File = event.target.files[0];
    if (!file) return;
    if (eye === 'OD') { this.vfODFile = file; this.vfODName = file.name; }
    else              { this.vfOSFile = file; this.vfOSName = file.name; }
  }

  sacuvaj(): void {
    if (this.form.invalid) return;
    this.saving = true;
    this.statusMsg = '';

    const v = this.form.value;

    // Korak 1: kreiraj pacijenta
    const patientBody = {
      first_name:        v.first_name,
      last_name:         v.last_name,
      birth_date:        v.birth_date,
      gender:            v.gender,
      cct:               v.cct,
      glaucoma_category: v.glaucoma_category,
    };

    this.patientService.createPatient(patientBody as any).subscribe({
      next: (res: any) => {
        const patientId: number = res?.data?.patient_id ?? res?.patient_id;

        // Korak 2: kreiraj inicijalni pregled za tog pacijenta
        const examBody = {
          patient_id:        patientId,
          od_iop:            v.od_iop,
          os_iop:            v.os_iop,
          physician_comment: v.physician_comment,
          therapy:           v.therapy,
        };

        this.visitService.createNewExam(patientId, examBody).subscribe({
          next: (examRes: any) => {
            const examId: number = examRes?.data?.exam_id ?? examRes?.exam_id;
            const uploads: Promise<void>[] = [];

            if (this.imageODFile || this.imageOSFile) {
              uploads.push(
                new Promise((resolve, reject) =>
                  this.visitService
                    .uploadImages(examId, this.imageODFile, this.imageOSFile)
                    .subscribe({ next: () => resolve(), error: reject })
                )
              );
            }

            if (this.vfODFile || this.vfOSFile) {
              uploads.push(
                new Promise((resolve, reject) =>
                  this.visitService
                    .uploadVfXml(examId, this.vfODFile, this.vfOSFile)
                    .subscribe({ next: () => resolve(), error: reject })
                )
              );
            }

            Promise.all(uploads)
              .then(() => {
                this.saving = false;
                this.router.navigate(['/patient', patientId]);
              })
              .catch(() => {
                this.saving = false;
                this.statusMsg = 'Patient and examination saved, but file upload failed. You can retry from the patient record.';
                this.statusType = 'error';
                setTimeout(() => this.router.navigate(['/patient', patientId]), 3000);
              });
          },
          error: () => {
            this.saving = false;
            this.statusMsg = 'Patient created but examination failed to save. Please try again from the patient record.';
            this.statusType = 'error';
          },
        });
      },
      error: () => {
        this.saving = false;
        this.statusMsg = 'Failed to register patient. Please try again.';
        this.statusType = 'error';
      },
    });
  }
}