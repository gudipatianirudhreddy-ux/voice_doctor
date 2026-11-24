const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export type Doctor = {
  id: number;
  name: string;
  specialty: string;
  description?: string | null;
};

export type Appointment = {
  appointment_id: number;
  patient_name: string;
  doctor_id: number;
  doctor_name: string;
  specialty: string;
  slot_id: number;
  start_time: string;
  end_time: string;
  status: string;
  created_at: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ message: string }>("/"),
  doctors: () => request<Doctor[]>("/doctors/"),
  appointments: (limit = 100) => request<Appointment[]>(`/appointments/?limit=${limit}`),
  availability: (doctorId: number, date: string) =>
    request<{ doctor_id: number; requested_date: string; available_slots: unknown[] }>(
      `/doctors/${doctorId}/availability?requested_date=${encodeURIComponent(date)}`,
    ),
};
