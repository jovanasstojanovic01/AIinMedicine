import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatSelectModule } from '@angular/material/select';
import { MatRadioModule } from '@angular/material/radio';
import { MatStepperModule, MatStepper } from '@angular/material/stepper';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

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
    MatRadioModule,
    MatStepperModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './new-patient-form.html',
  styleUrls: ['./new-patient-form.scss'],
})
export class NewPatientForm implements OnInit {

  @ViewChild('stepper') stepper!: MatStepper;

  patientForm!: FormGroup;
  savingPatient = false;
  patientError = '';
  patientId: number | null = null;

  iopForm!: FormGroup;
  savingIop = false;
  iopError = '';
  examId: number | null = null;

  imageODFile: File | null = null;
  imageODName = '';
  imageOSFile: File | null = null;
  imageOSName = '';
  savingImages = false;
  imagesError = '';

  vfODFile: File | null = null;
  vfODName = '';
  vfOSFile: File | null = null;
  vfOSName = '';
  savingVf = false;
  vfError = '';

  reviewForm!: FormGroup;
  savingReview = false;
  reviewError = '';
  examData: any = null;
  prikaziMasku = false;
  predOD: number | null = null;
  predOS: number | null = null;
  predLoading = false;
  mediaUrl = 'http://127.0.0.1:5000/api/media';

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private patientService: PatientService,
    private visitService: VisitService,
  ) {}

  ngOnInit(): void {
    this.patientForm = this.fb.group({
      first_name: ['', Validators.required],
      last_name:  ['', Validators.required],
      birth_date: ['', Validators.required],
      gender:     ['', Validators.required],
    });

    this.iopForm = this.fb.group({
      od_iop: ['', [Validators.required, Validators.min(0)]],
      os_iop: ['', [Validators.required, Validators.min(0)]],
    });

    this.reviewForm = this.fb.group({
      cct:               ['', [Validators.required, Validators.min(0)]],
      physician_comment: ['', Validators.required],
      glaucoma_category: ['None', Validators.required],
      therapy:           ['', Validators.required],
    });
  }

  submitPatient(): void {
    if (this.patientForm.invalid) return;
    this.savingPatient = true;
    this.patientError = '';

    this.patientService.createPatient(this.patientForm.value).subscribe({
      next: (res: any) => {
        this.patientId = res?.data?.patient_id ?? res?.patient_id;
        this.savingPatient = false;
        this.stepper.next();
      },
      error: () => {
        this.savingPatient = false;
        this.patientError = 'Failed to register patient. Please try again.';
      },
    });
  }

  submitIop(): void {
    if (this.iopForm.invalid) return;
    this.savingIop = true;
    this.iopError = '';

    this.visitService.createNewExam(this.patientId!, {
      od_iop: this.iopForm.value.od_iop,
      os_iop: this.iopForm.value.os_iop,
    }).subscribe({
      next: (res: any) => {
        this.examId = res?.data?.exam_id ?? res?.exam_id;
        this.savingIop = false;
        this.stepper.next();
      },
      error: () => {
        this.savingIop = false;
        this.iopError = 'Failed to save examination. Please try again.';
      },
    });
  }

  onImageSelected(event: any, eye: 'OD' | 'OS'): void {
    const file: File = event.target.files[0];
    if (!file) return;
    if (eye === 'OD') { this.imageODFile = file; this.imageODName = file.name; }
    else              { this.imageOSFile = file; this.imageOSName = file.name; }
  }

  submitImages(): void {
    if (!this.imageODFile && !this.imageOSFile) {
      this.stepper.next();
      return;
    }
    this.savingImages = true;
    this.imagesError = '';
    this.visitService.uploadImages(this.examId!, this.imageODFile, this.imageOSFile).subscribe({
      next: () => { this.savingImages = false; this.stepper.next(); },
      error: () => {
        this.savingImages = false;
        this.imagesError = 'Image upload failed. You can skip and retry later from the patient record.';
      },
    });
  }

  onVfSelected(event: any, eye: 'OD' | 'OS'): void {
    const file: File = event.target.files[0];
    if (!file) return;
    if (eye === 'OD') { this.vfODFile = file; this.vfODName = file.name; }
    else              { this.vfOSFile = file; this.vfOSName = file.name; }
    this.vfError = '';
  }

  submitVf(): void {
    const needOD = !!this.imageODFile;
    const needOS = !!this.imageOSFile;
    const neitherImage = !needOD && !needOS;

    if (needOD && !this.vfODFile) {
      this.vfError = 'You uploaded a fundus image for OD — VF XML for OD is required.';
      return;
    }
    if (needOS && !this.vfOSFile) {
      this.vfError = 'You uploaded a fundus image for OS — VF XML for OS is required.';
      return;
    }
    if (neitherImage && !this.vfODFile && !this.vfOSFile) {
      this.vfError = 'Please upload at least one Visual Field XML file (OD or OS).';
      return;
    }

    this.savingVf = true;
    this.vfError = '';
    this.visitService.uploadVfXml(this.examId!, this.vfODFile, this.vfOSFile).subscribe({
      next: () => {
        this.savingVf = false;
        this.loadExamAndPredict();
      },
      error: () => {
        this.savingVf = false;
        this.vfError = 'VF upload failed. Please try again.';
      },
    });
  }

  private loadExamAndPredict(): void {
    this.predLoading = true;

    this.visitService.getExam(this.examId!).subscribe({
      next: (res: any) => { this.examData = res?.data ?? res; },
    });

    Promise.all([
      new Promise<void>((resolve) =>
        this.visitService.predictProgression(this.examId!, 'OD').subscribe({
          next: (r: any) => { this.predOD = r?.data?.predicted_next_visit_vf_mean ?? null; resolve(); },
          error: () => resolve(),
        })
      ),
      new Promise<void>((resolve) =>
        this.visitService.predictProgression(this.examId!, 'OS').subscribe({
          next: (r: any) => { this.predOS = r?.data?.predicted_next_visit_vf_mean ?? null; resolve(); },
          error: () => resolve(),
        })
      ),
    ]).then(() => {
      this.predLoading = false;
      this.stepper.next();
    });
  }

  submitReview(): void {
    if (this.reviewForm.invalid) return;
    this.savingReview = true;
    this.reviewError = '';

    const v = this.reviewForm.value;

    Promise.all([
      new Promise<void>((resolve, reject) =>
        this.visitService.updateExam(this.examId!, {
          physician_comment: v.physician_comment,
          therapy: v.therapy,
        }).subscribe({ next: () => resolve(), error: reject })
      ),
      new Promise<void>((resolve, reject) =>
        this.patientService.updatePatient(this.patientId!, {
          cct: v.cct,
          glaucoma_category: v.glaucoma_category,
        }).subscribe({ next: () => resolve(), error: reject })
      ),
    ]).then(() => {
      this.savingReview = false;
      this.router.navigate(['/patient', this.patientId]);
    }).catch(() => {
      this.savingReview = false;
      this.reviewError = 'Failed to save. Please try again.';
    });
  }

  parseVf(matrix: string | null): number[] {
    if (!matrix) return [];
    try {
      const parsed = JSON.parse(matrix);
      if (Array.isArray(parsed)) {
        return parsed.map(v => (v === null || v === -1) ? -1 : Number(v));
      }
    } catch {}
    return matrix.split(',').map(v => {
      const t = v.trim();
      return (t === '' || t === '-1' || t === 'null') ? -1 : parseFloat(t);
    });
  }

  vfMean(matrix: string | null): number {
    const vals = this.parseVf(matrix).filter(v => v !== -1);
    if (vals.length === 0) return 0;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  }
}
