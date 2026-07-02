import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NewPatientForm } from './new-patient-form';

describe('NewPatientForm', () => {
  let component: NewPatientForm;
  let fixture: ComponentFixture<NewPatientForm>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewPatientForm],
    }).compileComponents();

    fixture = TestBed.createComponent(NewPatientForm);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
