import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';

import { VisitService } from '../../core/http/visit.service';
import { PatientService } from '../../core/http/patient.service';

@Component({
  selector: 'app-examination-form',
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
  ],
  templateUrl: './examination-form.html',
  styleUrls: ['./examination-form.scss'],
})
export class ExaminationForm implements OnInit {
  pregledForm!: FormGroup;

  patientId!: number;
  patientName: string = '';

  // Slike (opciono)
  imageODFile: File | null = null;
  imageODName: string = '';
  imageOSFile: File | null = null;
  imageOSName: string = '';

  // VF XML fajlovi (opciono)
  vfODFile: File | null = null;
  vfODName: string = '';
  vfOSFile: File | null = null;
  vfOSName: string = '';

  saving = false;
  statusMsg = '';
  statusType: 'success' | 'error' = 'success';

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private visitService: VisitService,
    private patientService: PatientService,
  ) {}

  ngOnInit(): void {
    this.patientId = Number(this.route.snapshot.paramMap.get('patientId'));

    // Učitaj ime pacijenta da se prikaže u headeru forme
    this.patientService.getPatientById(this.patientId).subscribe({
      next: (res: any) => {
        const p = res?.data ?? res;
        this.patientName = `${p.first_name} ${p.last_name}`;
      },
    });

    this.pregledForm = this.fb.group({
      od_iop: ['', [Validators.required, Validators.min(0)]],
      os_iop: ['', [Validators.required, Validators.min(0)]],
      physician_comment: [''],
      therapy: [''],
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
    if (this.pregledForm.invalid) return;
    // VF XML je obavezan — bar jedno oko mora biti uploadovano
    if (!this.vfODFile && !this.vfOSFile) {
      this.statusMsg = 'Please upload at least one Visual Field XML file (OD or OS).';
      this.statusType = 'error';
      return;
    }
    this.saving = true;
    this.statusMsg = '';

    const body = {
      patient_id: this.patientId,
      od_iop: this.pregledForm.value.od_iop,
      os_iop: this.pregledForm.value.os_iop,
      physician_comment: this.pregledForm.value.physician_comment,
      therapy: this.pregledForm.value.therapy,
    };

    // Korak 1: kreiraj pregled (dobijamo exam_id)
    this.visitService.createNewExam(this.patientId, body).subscribe({
      next: (res: any) => {
        const examId: number = res?.data?.exam_id ?? res?.exam_id;
        // Korak 2 i 3 su opcioni — pokrećemo ih paralelno ako postoje fajlovi
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
            this.router.navigate(['/patient', this.patientId]);
          })
          .catch(() => {
            // Pregled je sačuvan, samo upload nije uspeo — ne blokiramo navigaciju
            this.saving = false;
            this.statusMsg = 'Examination saved, but file upload failed. You can retry from the patient record.';
            this.statusType = 'error';
            setTimeout(() => this.router.navigate(['/patient', this.patientId]), 3000);
          });
      },
      error: () => {
        this.saving = false;
        this.statusMsg = 'Failed to save examination. Please try again.';
        this.statusType = 'error';
      },
    });
  }
}