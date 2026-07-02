import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class VisitService {
  private baseUrl = 'http://127.0.0.1:5000/api/visits';

  constructor(private http: HttpClient) {}

  // POST /api/visits — kreira pregled, prima ceo body sa IOP, komentarom...
  createNewExam(patientId: number, body: any): Observable<any> {
    return this.http.post<any>(this.baseUrl, { ...body, patient_id: patientId });
  }

  // GET /api/visits/patient/:id
  getExamsByPatient(patientId: number): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/patient/${patientId}`);
  }

  // GET /api/visits/:id
  getExam(id: number): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/${id}`);
  }

  // POST /api/visits/:id/upload-images — multipart, image_OD i/ili image_OS
  uploadImages(examId: number, imageOD: File | null, imageOS: File | null): Observable<any> {
    const formData = new FormData();
    if (imageOD) formData.append('image_OD', imageOD, imageOD.name);
    if (imageOS) formData.append('image_OS', imageOS, imageOS.name);
    return this.http.post<any>(`${this.baseUrl}/${examId}/upload-images`, formData);
  }

  // POST /api/visits/:id/upload-perimetry — multipart, file_OD i/ili file_OS (XML)
  uploadVfXml(examId: number, fileOD: File | null, fileOS: File | null): Observable<any> {
    const formData = new FormData();
    if (fileOD) formData.append('file_OD', fileOD, fileOD.name);
    if (fileOS) formData.append('file_OS', fileOS, fileOS.name);
    return this.http.post<any>(`${this.baseUrl}/${examId}/upload-perimetry`, formData);
  }

  // POST /api/visits/:id/predict-progression?eye=OD|OS
  predictProgression(examId: number, eye: 'OD' | 'OS'): Observable<any> {
    return this.http.post<any>(
      `${this.baseUrl}/${examId}/predict-progression?eye=${eye}`, {}
    );
  }
}