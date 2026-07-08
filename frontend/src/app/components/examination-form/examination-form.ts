import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatStepperModule, MatStepper } from '@angular/material/stepper';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

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
    MatStepperModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './examination-form.html',
  styleUrls: ['./examination-form.scss'],
})
export class ExaminationForm implements OnInit {

  @ViewChild('stepper') stepper!: MatStepper;

  patientId!: number;
  patientName = '';

  // Korak 1 — IOP
  iopForm!: FormGroup;
  savingIop = false;
  iopError = '';
  examId: number | null = null;

  // Korak 2 — Slike (opciono)
  imageODFile: File | null = null;
  imageODName = '';
  imageOSFile: File | null = null;
  imageOSName = '';
  savingImages = false;
  imagesError = '';

  // Korak 3 — VF XML
  vfODFile: File | null = null;
  vfODName = '';
  vfOSFile: File | null = null;
  vfOSName = '';
  savingVf = false;
  vfError = '';

  // Korak 4 — Review
  notesForm!: FormGroup;
  savingNotes = false;
  notesError = '';
  examData: any = null;
  prikaziMasku = false;
  predOD: number | null = null;
  predOS: number | null = null;
  predLoading = false;
  mediaUrl = 'http://127.0.0.1:5000/api/media';

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private visitService: VisitService,
    private patientService: PatientService,
  ) {}

  ngOnInit(): void {
    this.patientId = Number(this.route.snapshot.paramMap.get('patientId'));

    this.patientService.getPatientById(this.patientId).subscribe({
      next: (res: any) => {
        const p = res?.data ?? res;
        this.patientName = `${p.first_name} ${p.last_name}`;
      },
    });

    this.iopForm = this.fb.group({
      od_iop: ['', [Validators.required, Validators.min(0)]],
      os_iop: ['', [Validators.required, Validators.min(0)]],
    });

    this.notesForm = this.fb.group({
      physician_comment: ['', Validators.required],
      therapy:           ['', Validators.required],
    });
  }

  // ── KORAK 1 ─────────────────────────────────────────────────────────
  submitIop(): void {
    if (this.iopForm.invalid) return;
    this.savingIop = true;
    this.iopError = '';

    this.visitService.createNewExam(this.patientId, {
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
        this.iopError = 'Failed to create examination. Please try again.';
      },
    });
  }

  // ── KORAK 2 ─────────────────────────────────────────────────────────
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

  // ── KORAK 3 ─────────────────────────────────────────────────────────
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

  // Učitava exam podatke i pokreće predikciju, pa prelazi na korak 4
  private loadExamAndPredict(): void {
    this.predLoading = true;

    this.visitService.getExam(this.examId!).subscribe({
      next: (res: any) => {
        this.examData = res?.data ?? res;
      },
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

  // ── KORAK 4 ─────────────────────────────────────────────────────────
  submitNotes(): void {
    if (this.notesForm.invalid) return;
    this.savingNotes = true;
    this.notesError = '';
    this.visitService.updateExam(this.examId!, {
      physician_comment: this.notesForm.value.physician_comment,
      therapy:           this.notesForm.value.therapy,
    }).subscribe({
      next: () => {
        this.savingNotes = false;
        this.router.navigate(['/patient', this.patientId]);
      },
      error: () => {
        this.savingNotes = false;
        this.notesError = 'Failed to save notes. Please try again.';
      },
    });
  }

  // Parsira vf_matrix iz backenda — sačuvan kao JSON niz ("[21,22,...]").
  // null i -1 u nizu su slepe tačke — normalizujemo ih na -1.
  parseVf(matrix: string | null): number[] {
    if (!matrix) return [];
    try {
      const parsed = JSON.parse(matrix);
      if (Array.isArray(parsed)) {
        return parsed.map(v => (v === null || v === -1) ? -1 : Number(v));
      }
    } catch {}
    // Fallback: CSV format
    return matrix.split(',').map(v => {
      const t = v.trim();
      return (t === '' || t === '-1' || t === 'null') ? -1 : parseFloat(t);
    });
  }

  // Prosek VF vrednosti za trenutni pregled, isključujući slepe tačke (-1)
  vfMean(matrix: string | null): number {
    const vals = this.parseVf(matrix).filter(v => v !== -1);
    if (vals.length === 0) return 0;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  }
}
