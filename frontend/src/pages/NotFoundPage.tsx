import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <main className="not-found">
      <p className="eyebrow">404 · PAGE NOT FOUND</p>
      <h1>We can’t find that page.</h1>
      <p>The page may have moved, or the link may be incorrect.</p>
      <Link to="/" className="button button-primary">Return to your workspace</Link>
    </main>
  );
}
