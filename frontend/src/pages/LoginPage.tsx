import { Activity, ArrowRight, HeartPulse } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to sign in");
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
          <div className="promo-icon"><HeartPulse size={25} /></div>
          <p className="eyebrow light-eyebrow">CARE THAT CONNECTS</p>
          <h1>Your health journey, made simpler.</h1>
          <p>One calm place to find care, get answers, and stay on top of your appointments.</p>
        </div>
        <span className="auth-footer">Thoughtful care starts here.</span>
      </section>
      <section className="auth-form-panel">
        <div className="auth-form-wrap">
          <p className="eyebrow">WELCOME BACK</p>
          <h2>Sign in to Doctorly</h2>
          <p className="form-subtitle">Access your care workspace securely.</p>
          <form onSubmit={submit} className="form-stack">
            <label>Email address<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label>
            <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter your password" /></label>
            {error && <div className="alert alert-error" role="alert">{error}</div>}
            <button className="button button-primary button-wide" type="submit" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"} {!busy && <ArrowRight size={17} />}
            </button>
          </form>
          <p className="auth-switch">New to Doctorly? <Link to="/register">Create an account</Link></p>
        </div>
      </section>
    </main>
  );
}
