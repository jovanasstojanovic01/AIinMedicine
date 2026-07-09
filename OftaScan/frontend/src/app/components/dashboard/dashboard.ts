import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';

import { PatientService } from '../../core/http/patient.service';
import { Patient } from '../../core/models/patient.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    MatTableModule,
    MatButtonModule,
    MatInputModule,
    MatFormFieldModule,
    MatIconModule,
    MatCardModule,
  ],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.scss'],
})
export class Dashboard implements OnInit {
  // Kolone usklađene sa stvarnim Flask parametrima
  displayedColumns: string[] = [
    'imePrezime',
    'birth_date',
    'gender',
    'cct',
    'glaucoma_category',
    'akcija',
  ];

  // Lista pacijenata koja se vezuje za mat-table
  patients: Patient[] = [];

  // Dvosmerno vezivanje pretrage
  searchQuery: string = '';

  // ChangeDetectorRef za trenutno osvežavanje pogleda
  constructor(
    private patientService: PatientService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.ucitajPacijente();
  }

  // Povlačenje podataka sa backenda
  ucitajPacijente(): void {
    this.patientService.getAllPatients(this.searchQuery, 1).subscribe({
      next: (response: any) => {
        if (response && response.data && response.data.patients) {
          this.patients = response.data.patients;
        } else {
          this.patients = [];
        }

        // Detektovanje izmene niza i iscrtavanje tabele na ekranu
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Greška pri učitavanju pacijenata sa backenda:', err);
      },
    });
  }

  // Pokreće se kada lekar ukuca pojam ili klikne na ikonicu lupe
  onSearch(): void {
    this.ucitajPacijente();
  }
}
