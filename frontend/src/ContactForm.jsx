import { useState } from "react";

const DEFAULT_SUBMIT_URL = "/submit-form";

// ── Design tokens matching Autonomiqa's CSS variables ──────────────────────
const C = {
  orange: "#F97316",
  midnight: "#0A0F1E",
  white: "#FFFFFF",
  smoke: "#F7F6F3",
  silk: "#F0EDE8",
  ink: "#111827",
  steel: "#5B6278",
  mist: "#9AA0B4",
  lo: "#FFF3E8",
  border: "#E5E1DA",
};

const styles = {
  section: {
    background: C.smoke,
    padding: "96px 0",
    fontFamily: "'Outfit', sans-serif",
  },
  wrap: {
    maxWidth: 1160,
    margin: "0 auto",
    padding: "0 40px",
  },
  eyebrow: {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: "0.13em",
    textTransform: "uppercase",
    color: C.orange,
    background: C.lo,
    border: `1px solid rgba(249,115,22,.18)`,
    padding: "6px 14px",
    borderRadius: 100,
    marginBottom: 16,
  },
  dot: {
    width: 6,
    height: 6,
    background: C.orange,
    borderRadius: "50%",
    display: "inline-block",
  },
  heading: {
    fontFamily: "'Playfair Display', Georgia, serif",
    fontSize: "clamp(32px, 4vw, 48px)",
    fontWeight: 800,
    lineHeight: 1.1,
    letterSpacing: "-0.03em",
    color: C.midnight,
    marginBottom: 12,
  },
  em: { color: C.orange, fontStyle: "normal" },
  sub: {
    fontSize: 16,
    fontWeight: 300,
    color: C.steel,
    lineHeight: 1.75,
    marginBottom: 48,
    maxWidth: 480,
  },
  card: {
    background: C.white,
    border: `1px solid ${C.border}`,
    borderRadius: 18,
    padding: "48px 48px 44px",
    boxShadow: "0 16px 64px rgba(10,15,30,.08)",
    position: "relative",
    overflow: "hidden",
    maxWidth: 640,
  },
  cardAccent: {
    position: "absolute",
    top: 0, left: 0, right: 0,
    height: 3,
    background: `linear-gradient(90deg, ${C.orange}, #FFAA60)`,
  },
  row: { display: "flex", gap: 20, marginBottom: 20 },
  fieldWrap: { display: "flex", flexDirection: "column", flex: 1 },
  label: {
    fontSize: 12,
    fontWeight: 600,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    color: C.steel,
    marginBottom: 7,
  },
  input: (hasError, focused) => ({
    fontFamily: "'Outfit', sans-serif",
    fontSize: 15,
    fontWeight: 400,
    color: C.ink,
    background: C.smoke,
    border: `1.5px solid ${hasError ? "#ef4444" : focused ? C.orange : C.border}`,
    borderRadius: 8,
    padding: "12px 16px",
    outline: "none",
    transition: "border-color .2s, box-shadow .2s",
    boxShadow: focused && !hasError ? `0 0 0 3px rgba(249,115,22,.12)` : "none",
    width: "100%",
  }),
  textarea: (hasError, focused) => ({
    fontFamily: "'Outfit', sans-serif",
    fontSize: 15,
    fontWeight: 400,
    color: C.ink,
    background: C.smoke,
    border: `1.5px solid ${hasError ? "#ef4444" : focused ? C.orange : C.border}`,
    borderRadius: 8,
    padding: "12px 16px",
    outline: "none",
    resize: "vertical",
    minHeight: 130,
    transition: "border-color .2s, box-shadow .2s",
    boxShadow: focused && !hasError ? `0 0 0 3px rgba(249,115,22,.12)` : "none",
    width: "100%",
  }),
  errorText: {
    fontSize: 12,
    color: "#ef4444",
    marginTop: 5,
    fontWeight: 500,
  },
  btn: (loading) => ({
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    fontFamily: "'Outfit', sans-serif",
    fontSize: 15,
    fontWeight: 500,
    padding: "14px 32px",
    borderRadius: 7,
    border: "none",
    cursor: loading ? "not-allowed" : "pointer",
    background: loading ? C.mist : C.orange,
    color: C.white,
    boxShadow: loading ? "none" : "0 4px 24px rgba(249,115,22,.3)",
    transition: "all .22s cubic-bezier(.22,.84,.44,1)",
    width: "100%",
    marginTop: 8,
  }),
  successBox: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    textAlign: "center",
    padding: "32px 0 16px",
    gap: 12,
  },
  successIcon: {
    width: 56,
    height: 56,
    borderRadius: "50%",
    background: "#dcfce7",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  successTitle: {
    fontFamily: "'Playfair Display', serif",
    fontSize: 26,
    fontWeight: 700,
    color: C.midnight,
  },
  successSub: {
    fontSize: 15,
    color: C.steel,
    fontWeight: 300,
    lineHeight: 1.7,
    maxWidth: 360,
  },
  apiError: {
    background: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: 8,
    padding: "12px 16px",
    fontSize: 14,
    color: "#dc2626",
    marginBottom: 16,
    fontWeight: 500,
  },
};

// ── Validation ──────────────────────────────────────────────────────────────
function validate(fields) {
  const errors = {};
  if (!fields.name.trim()) errors.name = "Name is required.";
  else if (fields.name.trim().length < 2) errors.name = "Name must be at least 2 characters.";

  if (!fields.email.trim()) errors.email = "Email is required.";
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fields.email)) errors.email = "Enter a valid email address.";

  if (!fields.message.trim()) errors.message = "Message is required.";
  else if (fields.message.trim().length < 10) errors.message = "Message must be at least 10 characters.";

  return errors;
}

// ── Component ───────────────────────────────────────────────────────────────
export default function ContactForm({ apiUrl = DEFAULT_SUBMIT_URL } = {}) {
  const [fields, setFields] = useState({ name: "", email: "", message: "" });
  const [errors, setErrors] = useState({});
  const [focused, setFocused] = useState({});
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [apiError, setApiError] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFields((f) => ({ ...f, [name]: value }));
    // Clear error on change
    if (errors[name]) setErrors((er) => ({ ...er, [name]: "" }));
  };

  const handleFocus = (name) => setFocused((f) => ({ ...f, [name]: true }));
  const handleBlur = (name) => {
    setFocused((f) => ({ ...f, [name]: false }));
    // Validate single field on blur
    const fieldErrors = validate(fields);
    if (fieldErrors[name]) setErrors((er) => ({ ...er, [name]: fieldErrors[name] }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const fieldErrors = validate(fields);
    if (Object.keys(fieldErrors).length > 0) {
      setErrors(fieldErrors);
      return;
    }

    setLoading(true);
    setApiError("");

    try {
      const res = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: fields.name.trim(),
          email: fields.email.trim(),
          message: fields.message.trim(),
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Server error: ${res.status}`);
      }

      setSubmitted(true);
    } catch (err) {
      setApiError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section style={styles.section} id="contact">
      <div style={styles.wrap}>
        {/* Header */}
        <div style={{ marginBottom: 40 }}>
          <div style={styles.eyebrow}>
            <span style={styles.dot} />
            Get In Touch
          </div>
          <h2 style={styles.heading}>
            Let's talk about your <em style={styles.em}>pipeline.</em>
          </h2>
          <p style={styles.sub}>
            Drop us a message and we'll get back to you within one business day.
          </p>
        </div>

        {/* Card */}
        <div style={styles.card}>
          <div style={styles.cardAccent} />

          {submitted ? (
            <div style={styles.successBox}>
              <div style={styles.successIcon}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <div style={styles.successTitle}>Message received.</div>
              <p style={styles.successSub}>
                Thanks for reaching out. We'll review your message and get back to you shortly.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              {apiError && <div style={styles.apiError}>{apiError}</div>}

              {/* Name + Email row */}
              <div style={styles.row}>
                <div style={styles.fieldWrap}>
                  <label style={styles.label}>Name</label>
                  <input
                    name="name"
                    type="text"
                    placeholder="Your full name"
                    value={fields.name}
                    onChange={handleChange}
                    onFocus={() => handleFocus("name")}
                    onBlur={() => handleBlur("name")}
                    style={styles.input(!!errors.name, focused.name)}
                    autoComplete="name"
                  />
                  {errors.name && <span style={styles.errorText}>{errors.name}</span>}
                </div>

                <div style={styles.fieldWrap}>
                  <label style={styles.label}>Work Email</label>
                  <input
                    name="email"
                    type="email"
                    placeholder="you@company.com"
                    value={fields.email}
                    onChange={handleChange}
                    onFocus={() => handleFocus("email")}
                    onBlur={() => handleBlur("email")}
                    style={styles.input(!!errors.email, focused.email)}
                    autoComplete="email"
                  />
                  {errors.email && <span style={styles.errorText}>{errors.email}</span>}
                </div>
              </div>

              {/* Message */}
              <div style={{ marginBottom: 24 }}>
                <label style={styles.label}>Message</label>
                <textarea
                  name="message"
                  placeholder="Tell us about your team size, current outreach setup, or what you're trying to solve…"
                  value={fields.message}
                  onChange={handleChange}
                  onFocus={() => handleFocus("message")}
                  onBlur={() => handleBlur("message")}
                  style={styles.textarea(!!errors.message, focused.message)}
                />
                {errors.message && <span style={styles.errorText}>{errors.message}</span>}
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                style={styles.btn(loading)}
              >
                {loading ? (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                      style={{ animation: "spin 1s linear infinite" }}>
                      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                    </svg>
                    Sending…
                  </>
                ) : (
                  <>
                    Send Message
                    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M3 7.5h9M8 3.5l4 4-4 4" />
                    </svg>
                  </>
                )}
              </button>

              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}
