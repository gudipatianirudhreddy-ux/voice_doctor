import { useEffect, useState } from "react";
import { Activity, CalendarDays, Clock3, HeartPulse, Mic, MicOff, Phone, ShieldCheck, Stethoscope, Users } from "lucide-react";
import { api } from "./lib/api";

type ApiState = "checking" | "online" | "offline";

export default function App() {
  const [apiState, setApiState] = useState<ApiState>("checking");
  const [apiMessage, setApiMessage] = useState("Checking backend connection…");

  useEffect(() => {
    let active = true;
    api.health()
      .then((result) => {
        if (!active) return;
        setApiState("online");
        setApiMessage(result.message);
      })
      .catch(() => {
        if (!active) return;
        setApiState("offline");
        setApiMessage("Start the FastAPI server to connect the dashboard.");
      });
    return () => { active = false; };
  }, []);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><HeartPulse size={22} /></span><span>voice<span className="brand-light">doctor</span><small>by NexovAI</small></span></div>
        <div className="sidebar-label">WORKSPACE</div>
        <a className="nav-item active"><Activity size={18} /> Overview</a>
        <a className="nav-item"><CalendarDays size={18} /> Appointments</a>
        <a className="nav-item"><Stethoscope size={18} /> Doctors</a>
        <div className="sidebar-bottom"><ShieldCheck size={17} /><span>Private by design<br/><small>Demo dashboard</small></span></div>
      </aside>

      <section className="main-content">
        <header className="topbar"><div><span className="eyebrow">YOUR HEALTH, SIMPLIFIED</span><h1>Good day <span>👋</span></h1><p>Manage appointments with a conversation.</p></div><div className={`api-pill ${apiState}`}><span className="status-dot" />{apiState === "online" ? "API connected" : apiState === "offline" ? "API offline" : "Connecting"}</div></header>

        <section className="welcome-card">
          <div className="welcome-copy"><div className="live-label"><span className="pulse-dot" /> VOICE ASSISTANT</div><h2>How can we help<br/>you feel better?</h2><p>Talk naturally to book, manage, or reschedule a doctor appointment.</p><div className="voice-actions"><button className="primary-button" disabled><Mic size={18}/> Start a voice call <span className="soon">Coming next</span></button><span className="secure-note"><ShieldCheck size={15}/> Your call stays private</span></div></div>
          <div className="voice-visual" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="voice-core"><Mic size={38}/></div><span className="wave wave-a"/><span className="wave wave-b"/><span className="wave wave-c"/></div>
        </section>

        <div className="section-heading"><div><h2>Your care at a glance</h2><p>A clear view of your appointment activity.</p></div><button className="text-button" disabled>View all <span>→</span></button></div>
        <div className="stats-grid"><article className="stat-card"><div className="stat-icon blue"><CalendarDays size={19}/></div><span className="stat-label">Appointments</span><strong>—</strong><small>Recent bookings</small></article><article className="stat-card"><div className="stat-icon green"><Users size={19}/></div><span className="stat-label">Doctors</span><strong>—</strong><small>Available specialists</small></article><article className="stat-card"><div className="stat-icon amber"><Clock3 size={19}/></div><span className="stat-label">Next visit</span><strong>—</strong><small>Your upcoming care</small></article></div>

        <section className="appointments-panel"><div className="panel-heading"><div><h2>Recent appointments</h2><p>Your latest appointment updates will appear here.</p></div><span className="panel-icon"><CalendarDays size={19}/></span></div><div className="empty-state"><div className="empty-icon"><CalendarDays size={24}/></div><strong>Nothing scheduled yet</strong><p>Once you book an appointment, you'll find the details here.</p></div></section>
        <footer><span>© 2026 NexovAI</span><span className="backend-status"><span className={`status-dot ${apiState}`}/>{apiMessage}</span></footer>
      </section>
    </main>
  );
}
