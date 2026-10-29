import { Activity, ArrowRight } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await register({
        full_name: fullName,
        email,
        password,
        ...(phone ? { phone_number: phone } : {}),
      });
      navigate("/chat");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to create account");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-brand-panel">
        <Link className="brand light-brand" to="/login">
          <span className="brand-mark"><Activity size={21} /></span>
          <span>doctorly<span className="brand-period">.</span></span>
        </Link>
        <div className="auth-promo">
          <div className="promo-icon"><Activity size={25} /></div>
          <p className="eyebrow light-eyebrow">YOUR CARE, IN ONE PLACE</p>
          <h1>A better way to manage your care.</h1>
          <p>Create your patient account to connect with support and manage appointments.</p>
        </div>
        <span className="auth-footer">Thoughtful care starts here.</span>
      </section>
      <section className="auth-form-panel">
        <div className="auth-form-wrap">
          <p className="eyebrow">GET STARTED</p>
          <h2>Create your account</h2>
          <p className="form-subtitle">A few details to set up your patient profile.</p>
          <form onSubmit={submit} className="form-stack">
            <label>Full name<input autoComplete="name" required maxLength={200} value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Your full name" /></label>
            <label>Email address<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label>
            <label>Phone number <span className="optional">(optional)</span><input type="tel" autoComplete="tel" maxLength={32} value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+92 300 0000000" /></label>
            <label>Password<input type="password" autoComplete="new-password" minLength={12} maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 12 characters" /></label>
            {error && <div className="alert alert-error" role="alert">{error}</div>}
            <button className="button button-primary button-wide" type="submit" disabled={busy}>
              {busy ? "Creating account…" : "Create account"} {!busy && <ArrowRight size={17} />}
            </button>
          </form>
          <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
        </div>
      </section>
    </main>
  );
}
