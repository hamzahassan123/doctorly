export const API_BASE_URL = "http://localhost:8000";
const TOKEN_KEY = "doctorly_access_token";

export type UserRole = "patient" | "staff";
export type AppointmentStatus =
  | "pending_approval"
  | "confirmed"
  | "cancelled"
  | "completed";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface Doctor {
  id: string;
  display_name: string;
  specialty: string;
  is_active: boolean;
}

export interface AvailabilitySlot {
  id: string;
  doctor_id: string;
  starts_at: string;
  ends_at: string;
  doctor?: Doctor;
}

export interface Appointment {
  id: string;
  patient_id: string;
  availability_slot_id: string;
  status: AppointmentStatus;
  is_flagged: boolean;
  created_at: string;
  updated_at: string;
  availability_slot: AvailabilitySlot;
  patient_profile?: {
    user_id: string;
    full_name: string;
    date_of_birth: string | null;
    phone_number: string | null;
  };
}

export interface ChatResult {
  intent: "faq" | "booking" | "emergency" | "clarifying";
  response: string;
  retrieved_context: Array<{ title: string; content: string; source: string }>;
  available_slots: Array<Record<string, string>>;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const tokenStorage = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((item) =>
          typeof item === "object" && item !== null && "msg" in item
            ? String(item.msg)
            : String(item),
        )
        .join(", ");
    }
    return `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = tokenStorage.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  login: (email: string, password: string) =>
    apiRequest<AuthToken>("/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (input: {
    email: string;
    password: string;
    full_name: string;
    phone_number?: string;
  }) =>
    apiRequest<User>("/register", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  me: () => apiRequest<User>("/me"),
  doctors: () => apiRequest<Doctor[]>("/doctors"),
  slots: () => apiRequest<AvailabilitySlot[]>("/slots"),
  appointments: () => apiRequest<Appointment[]>("/appointments"),
  book: (availabilitySlotId: string) =>
    apiRequest<Appointment>("/appointments", {
      method: "POST",
      body: JSON.stringify({ availability_slot_id: availabilitySlotId }),
    }),
  staffAppointments: () => apiRequest<Appointment[]>("/staff/appointments"),
  updateStaffAppointment: (
    id: string,
    changes: { status?: AppointmentStatus; is_flagged?: boolean },
  ) =>
    apiRequest<Appointment>(`/staff/appointments/${id}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    }),
};

function decodeSseFrame(
  frame: string,
): { event: string; data: string } | undefined {
  const lines = frame.split(/\r?\n/);
  let event = "message";
  const data: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  if (data.length === 0) return undefined;
  let value = data.join("\n");

  // Some SSE implementations encode an event frame inside the data field.
  if (value.startsWith("event:")) {
    const embedded = decodeSseFrame(value);
    if (embedded) return embedded;
  }
  if (value.startsWith("{")) {
    try {
      const payload = JSON.parse(value) as { event?: unknown; data?: unknown };
      if (typeof payload.event === "string" && "data" in payload) {
        event = payload.event;
        value =
          typeof payload.data === "string"
            ? payload.data
            : JSON.stringify(payload.data);
      }
    } catch {
      // The event payload may be plain text rather than JSON.
    }
  }
  return { event, data: value };
}

export async function streamChat(
  message: string,
  onToken: (token: string) => void,
  signal?: AbortSignal,
): Promise<ChatResult> {
  const token = tokenStorage.get();
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message }),
    signal,
  });
  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }
  if (!response.body) throw new Error("Chat stream response has no body");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: ChatResult | undefined;
  let accumulatedTokens = "";
  const emitToken = (text: string) => {
    accumulatedTokens += text;
    onToken(text);
  };

  const processFrame = (frame: string) => {
    const parsed = decodeSseFrame(frame);
    if (!parsed) return;
    if (parsed.event === "error") {
      let detail = parsed.data;
      try {
        const value = JSON.parse(parsed.data) as { detail?: string };
        detail = value.detail ?? detail;
      } catch {
        // Keep plain-text server error messages.
      }
      throw new Error(detail);
    }
    if (parsed.event === "token") {
      let tokenText = parsed.data;
      try {
        const value = JSON.parse(parsed.data) as
          | string
          | { token?: string; data?: string };
        tokenText =
          typeof value === "string"
            ? value
            : (value.token ?? value.data ?? tokenText);
      } catch {
        // Token events are commonly plain text.
      }
      emitToken(tokenText);
      return;
    }
    if (parsed.event === "message") {
      try {
        const payload = JSON.parse(parsed.data) as Partial<ChatResult>;
        if (typeof payload.response === "string") {
          result = {
            intent: payload.intent ?? "faq",
            response: payload.response,
            retrieved_context: payload.retrieved_context ?? [],
            available_slots: payload.available_slots ?? [],
          };
          if (!result.response.startsWith(accumulatedTokens)) {
            emitToken(result.response);
          }
        } else {
          emitToken(parsed.data);
        }
      } catch {
        emitToken(parsed.data);
      }
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let boundary = buffer.search(/\r?\n\r?\n/);
      while (boundary !== -1) {
        const separator = buffer.slice(boundary).match(/^\r?\n\r?\n/)?.[0] ?? "\n\n";
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + separator.length);
        processFrame(frame);
        boundary = buffer.search(/\r?\n\r?\n/);
      }
      if (done) break;
    }
    if (buffer.trim()) processFrame(buffer);
  } finally {
    reader.releaseLock();
  }

  return (
    result ?? {
      intent: "clarifying",
      response: accumulatedTokens,
      retrieved_context: [],
      available_slots: [],
    }
  );
}
