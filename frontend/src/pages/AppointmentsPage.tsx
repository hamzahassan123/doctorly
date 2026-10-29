import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, Check, Clock3, Stethoscope } from "lucide-react";
import { useState } from "react";
import { api, type AvailabilitySlot } from "../lib/api";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function AppointmentsPage() {
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState("");
  const slots = useQuery({ queryKey: ["slots"], queryFn: api.slots });
  const doctors = useQuery({ queryKey: ["doctors"], queryFn: api.doctors });
  const appointments = useQuery({ queryKey: ["appointments"], queryFn: api.appointments });
  const doctorById = new Map((doctors.data ?? []).map((doctor) => [doctor.id, doctor]));
  const bookSlot = useMutation({
    mutationFn: (slotId: string) => api.book(slotId),
    onSuccess: async () => {
      setNotice("Your appointment is booked.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["slots"] }),
        queryClient.invalidateQueries({ queryKey: ["appointments"] }),
      ]);
    },
    onError: (reason) => setNotice(reason instanceof Error ? reason.message : "Unable to book this slot."),
  });

  return (
    <section className="content-page">
      <header className="page-heading">
        <div>
          <p className="eyebrow">YOUR CARE</p>
          <h1>Appointments</h1>
          <p className="page-description">Choose a time that works for you and keep track of your visits.</p>
        </div>
        <div className="heading-icon"><CalendarDays size={22} /></div>
      </header>
      {notice && <div className={`alert ${notice.includes("booked") ? "alert-success" : "alert-error"}`} role="status">{notice}</div>}

      <section className="section-block">
        <div className="section-title"><div><p className="eyebrow">OPEN TIMES</p><h2>Available appointments</h2></div><span className="count-pill">{slots.data?.length ?? 0} available</span></div>
        {slots.isPending ? <div className="loading-card">Loading available times…</div> : slots.isError ? <div className="alert alert-error">{slots.error.message}</div> : slots.data.length === 0 ? (
          <div className="empty-card"><CalendarDays size={24} /><strong>No open appointments right now</strong><span>Check back later for newly available times.</span></div>
        ) : (
          <div className="slot-grid">
            {slots.data.map((slot: AvailabilitySlot) => (
              <article className="slot-card" key={slot.id}>
                <div className="slot-date-icon"><CalendarDays size={19} /></div>
                <div className="slot-info">
                  <strong>{formatDate(slot.starts_at)}</strong>
                  <span><Clock3 size={14} /> Ends {new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date(slot.ends_at))}</span>
                  <span><Stethoscope size={14} /> {doctorById.get(slot.doctor_id)?.display_name ?? "Doctor"}{doctorById.get(slot.doctor_id)?.specialty ? ` · ${doctorById.get(slot.doctor_id)?.specialty}` : ""}</span>
                </div>
                <button className="button button-outline" onClick={() => bookSlot.mutate(slot.id)} disabled={bookSlot.isPending}>
                  {bookSlot.isPending ? "Booking…" : "Book"} {!bookSlot.isPending && <Check size={15} />}
                </button>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="section-block">
        <div className="section-title"><div><p className="eyebrow">UPCOMING & PAST</p><h2>Your appointments</h2></div></div>
        {appointments.isPending ? <div className="loading-card">Loading your appointments…</div> : appointments.isError ? <div className="alert alert-error">{appointments.error.message}</div> : appointments.data.length === 0 ? (
          <div className="empty-card"><Clock3 size={24} /><strong>No appointments yet</strong><span>Appointments you book will appear here.</span></div>
        ) : (
          <div className="appointment-list">
            {appointments.data.map((appointment) => (
              <article className="appointment-card" key={appointment.id}>
                <div className="appointment-date"><span>{new Intl.DateTimeFormat(undefined, { month: "short" }).format(new Date(appointment.availability_slot.starts_at))}</span><strong>{new Intl.DateTimeFormat(undefined, { day: "2-digit" }).format(new Date(appointment.availability_slot.starts_at))}</strong></div>
                <div className="appointment-details"><strong>Doctor appointment</strong><span>{formatDate(appointment.availability_slot.starts_at)}</span></div>
                <span className={`status-pill status-${appointment.status}`}>{appointment.status.replace("_", " ")}</span>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
