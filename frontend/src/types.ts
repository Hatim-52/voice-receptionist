export interface Doctor {
  id: number;
  name: string;
  speciality: string;
  experience: string;
  room: string;
  bio?: string;
  available_dates?: string[];
  slots_by_date?: Record<string, string[]>;
  today_slots?: string[];
  tomorrow_slots?: string[];
}

export interface Appointment {
  id: number;
  phone: string;
  patient_name: string;
  doctor_id: number;
  doctor_name: string;
  date: string;
  time: string;
  status: 'confirmed' | 'cancelled';
  created_at?: string;
  // Transient UI flag for row highlighting animation
  _justUpdated?: 'booked' | 'cancelled';
}

export interface TranscriptItem {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  timestamp: string;
}

export type CallState = 'idle' | 'ringing' | 'connected' | 'ended' | 'error';
