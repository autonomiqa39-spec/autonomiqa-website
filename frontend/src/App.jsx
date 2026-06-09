import ContactForm from "./ContactForm";

function App() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Header/Navbar mockup to look premium */}
      <header style={{
        background: "#FFFFFF",
        borderBottom: "1px solid #E5E1DA",
        padding: "20px 40px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center"
      }}>
        <div style={{
          fontFamily: "'Playfair Display', Georgia, serif",
          fontSize: "24px",
          fontWeight: 800,
          letterSpacing: "-0.02em",
          color: "#0A0F1E"
        }}>
          Autonomiqa<span style={{ color: "#F97316" }}>.</span>
        </div>
        <div style={{ display: "flex", gap: "24px", fontFamily: "'Outfit', sans-serif", fontSize: "14px", fontWeight: 500 }}>
          <a href="#platform" style={{ color: "#5B6278", textDecoration: "none" }}>Platform</a>
          <a href="#solutions" style={{ color: "#5B6278", textDecoration: "none" }}>Solutions</a>
          <a href="#contact" style={{ color: "#F97316", textDecoration: "none" }}>Contact</a>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ flex: 1 }}>
        <ContactForm apiUrl="http://localhost:8000/submit-form" />
      </main>

      {/* Footer mockup */}
      <footer style={{
        background: "#0A0F1E",
        color: "#9AA0B4",
        padding: "40px 40px",
        textAlign: "center",
        fontFamily: "'Outfit', sans-serif",
        fontSize: "13px",
        borderTop: "1px solid rgba(255,255,255,0.05)"
      }}>
        <div>&copy; {new Date().getFullYear()} Autonomiqa. All rights reserved.</div>
      </footer>
    </div>
  );
}

export default App;
