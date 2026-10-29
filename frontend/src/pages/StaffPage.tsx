import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CalendarDays, Check, Flag, UserRound } from "lucide-react";
import { useState } from "react";
import { api, type Appointment, type AppointmentStatus } from "../lib/api";

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

export default function StaffPage() {
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState("");
  const appointments = useQuery({
    queryKey: ["staff-appointments"],
    queryFn: api.staffAppointments,
  });
  const update = useMutation({
    mutationFn: ({
      id,
      changes,
    }: {
      id: string;
      changes: { status?: AppointmentStatus; is_flagged?: boolean };
    }) => api.updateStaffAppointment(id, changes),
    onSuccess: async () => {
      setNotice("Appointment updated.");
      await queryClient.invalidateQueries({ queryKey: ["staff-appointments"] });
    },
    onError: (reason) =>
      setNotice(reason instanceof Error ? reason.message : "Unable to update appointment."),
  });

  return (
    <section className="content-page">
      <header className="page-heading">
        <div>
          <p className="eyebrow">CARE TEAM</p>
          <h1>Staff dashboard</h1>
          <p className="page-description">Review the appointment queue and manage patient visits.</p>
        </div>
        <div className="heading-icon"><CalendarDays size={22} /></div>
      </header>
      {notice && <div className={`alert ${notice === "Appointment updated." ? "alert-success" : "alert-error"}`} role="status">{notice}</div>}
      <section className="section-block">
        <div className="section-title">
          <div><p className="eyebrow">SCHEDULING</p><h2>All appointments</h2></div>
          <span className="count-pill">{appointments.data?.length ?? 0} total</span>
        </div>
        {appointments.isPending ? <div className="loading-card">Loading appointments…</div> : appointments.isError ? <div className="alert alert-error">{appointments.error.message}</div> : appointments.data.length === 0 ? (
          <div className="empty-card"><CalendarDays size={24} /><strong>No appointments to review</strong><span>New patient bookings will show up here.</span></div>
        ) : (
          <div className="staff-table-wrap">
            <table className="staff-table">
              <thead><tr><th>Patient</th><th>Appointment</th><th>Status</th><th>Flag</th><th>Actions</th></tr></thead>
              <tbody>
                {appointments.data.map((appointment: Appointment) => (
                  <tr key={appointment.id}>
                    <td><div className="table-patient"><span className="table-avatar"><UserRound size={16} /></span><span><strong>{appointment.patient_profile?.full_name ?? "Patient"}</strong><small>{appointment.patient_profile?.phone_number ?? "No phone provided"}</small></span></div></td>
                    <td><span className="table-date">{formatDate(appointment.availability_slot.starts_at)}</span><small className="table-subtext">ID {appointment.id.slice(0, 8)}</small></td>
                    <td><span className={`status-pill status-${appointment.status}`}>{appointment.status.replace("_", " ")}</span></td>
                    <td>{appointment.is_flagged ? <span className="flagged-label"><Flag size={14} /> Flagged</span> : <span className="muted">—</span>}</td>
                    <td><div className="table-actions">
                      <button className="icon-action" title={appointment.is_flagged ? "Remove flag" : "Flag appointment"} aria-label={appointment.is_flagged ? "Remove flag" : "Flag appointment"} onClick={() => update.mutate({ id: appointment.id, changes: { is_flagged: !appointment.is_flagged } })} disabled={update.isPending}><Flag size={16} /></button>
                      {appointment.status === "confirmed" || appointment.status === "pending_approval" ? (
                        <button className="cancel-action" onClick={() => update.mutate({ id: appointment.id, changes: { status: "cancelled" } })} disabled={update.isPending}><AlertCircle size={15} /> Cancel</button>
                      ) : appointment.status === "cancelled" ? (
                        <span className="muted">Cancelled</span>
                      ) : (
                        <span className="completed-label"><Check size={15} /> Complete</span>
                      )}
                    </div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}
