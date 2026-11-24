import { useEffect, useRef, useState } from "react";
import {
  Activity, CalendarDays, Clock3, HeartPulse, Mic, PhoneOff,
  ShieldCheck, Stethoscope, Users, Wifi, WifiOff,
} from "lucide-react";
import {
  PipecatClient,
  type BotLLMTextData,
  type Participant,
  type TranscriptData,
  type TransportState,
} from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";
import { api, type Appointment, type Doctor } from "./lib/api";

type ApiState = "checking" | "online" | "offline";
type VoiceState = "idle" | "connecting" | "connected" | "error";
type TranscriptLine = { id: number; speaker: "You" | "Voice Doctor"; text: string };
type Page = "overview" | "appointments" | "doctors";
type AppointmentFilter = "all" | "upcoming" | "completed" | "cancelled";


function formatAppointmentDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "numeric", minute: "2-digit", hour12: true,
  }).format(date);
}

function formatPatientName(value: string) {
  return value.replace(/[_]+/g, " ").replace(/\s+/g, " ").trim();
}

function appointmentMatchesFilter(item: Appointment, filter: AppointmentFilter) {
  const status = item.status.toLowerCase();
  if (filter === "cancelled") return status === "cancelled";
  if (filter === "completed") {
    return status !== "cancelled" && new Date(item.end_time).getTime() < Date.now();
  }
  if (filter === "upcoming") {
    return status !== "cancelled" && new Date(item.start_time).getTime() >= Date.now();
  }
  return true;
}

function cleanTranscript(text: string) {
  return text
    .replace(/\\*\\*(.*?)\\*\\*/g, "$1")
    .replace(/^\\s*(?:\\d+[.)]|[-*])\\s*/gm, "")
    .replace(/\\s+/g, " ")
    .trim();
}

function addTranscriptLine(
  lines: TranscriptLine[],
  speaker: TranscriptLine["speaker"],
  rawText: string,
  nextId: () => number,
) {
  const text = cleanTranscript(rawText);
  if (!text) return lines;
  const last = lines[lines.length - 1];
  if (last?.speaker === speaker) {
    if (text.startsWith(last.text)) {
      return [...lines.slice(0, -1), { ...last, text }];
    }
    if (last.text.endsWith(text)) return lines;
    const separator = /[\\s.,!?;:]$/.test(last.text) ? "" : " ";
    return [...lines.slice(0, -1), { ...last, text: last.text + separator + text }];
  }
  return [...lines, { id: nextId(), speaker, text }];
}

const PIPECAT_URL = (import.meta.env.VITE_PIPECAT_BASE_URL ?? "http://localhost:7860").replace(/\/$/, "");

export default function App() {
  const [apiState, setApiState] = useState<ApiState>("checking");
  const [apiMessage, setApiMessage] = useState("Checking backend connection…");
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceError, setVoiceError] = useState("");
  const [transportState, setTransportState] = useState("disconnected");
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [page, setPage] = useState<Page>("overview");
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [dataLoading, setDataLoading] = useState(false);
  const [dataError, setDataError] = useState("");
  const [appointmentFilter, setAppointmentFilter] = useState<AppointmentFilter>("all");

  const clientRef = useRef<PipecatClient | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lineId = useRef(0);

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

  async function refreshDashboard() {
    setDataLoading(true);
    setDataError("");
    try {
      const [appointmentRows, doctorRows] = await Promise.all([
        api.appointments(),
        api.doctors(),
      ]);
      setAppointments(appointmentRows);
      setDoctors(doctorRows);
    } catch (error) {
      setDataError(error instanceof Error ? error.message : "Could not load dashboard data.");
    } finally {
      setDataLoading(false);
    }
  }

  useEffect(() => {
    if (apiState === "online") void refreshDashboard();
  }, [apiState]);


  function getClient() {
    if (clientRef.current) return clientRef.current;
    const client = new PipecatClient({
      transport: new SmallWebRTCTransport(),
      enableMic: true,
      enableCam: false,
      callbacks: {
        onTransportStateChanged: (state: TransportState) => {
          setTransportState(String(state));
        },
        onConnected: () => setVoiceState("connected"),
        onBotReady: () => setVoiceState("connected"),
        onDisconnected: () => {
          setVoiceState("idle");
          setTransportState("disconnected");
        },
        onError: (error) => {
          setVoiceError(typeof error === "string" ? error : "The voice connection encountered an error.");
          setVoiceState("error");
        },
        onUserTranscript: (data: TranscriptData) => {
          if (data.final && data.text.trim()) {
            setTranscript((lines) => addTranscriptLine(lines, "You", data.text, () => ++lineId.current));
          }
        },
        onBotTranscript: (data: BotLLMTextData) => {
          if (data.text.trim()) {
            setTranscript((lines) => addTranscriptLine(lines, "Voice Doctor", data.text, () => ++lineId.current));
          }
        },
        onTrackStarted: (track: MediaStreamTrack, participant?: Participant) => {
          if (track.kind === "audio" && !participant?.local && audioRef.current) {
            audioRef.current.srcObject = new MediaStream([track]);
            void audioRef.current.play().catch(() => undefined);
          }
        },
      },
    });
    clientRef.current = client;
    return client;
  }

  async function startVoiceCall() {
    setVoiceError("");
    setTranscript([]);
    setVoiceState("connecting");
    try {
      const client = getClient();
      await client.initDevices();
      await client.startBotAndConnect({
        endpoint: `${PIPECAT_URL}/start`,
        requestData: {
          transport: "webrtc",
          enableDefaultIceServers: true,
        },
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not start the voice session.";
      setVoiceError(message);
      setVoiceState("error");
      await clientRef.current?.disconnect().catch(() => undefined);
    }
  }

  async function endVoiceCall() {
    await clientRef.current?.disconnect();
    setVoiceState("idle");
    setTransportState("disconnected");
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><HeartPulse size={22} /></span><span>voice<span className="brand-light">doctor</span><small>by NexovAI</small></span></div>
        <div className="sidebar-label">WORKSPACE</div>
        <button className={`nav-item ${page === "overview" ? "active" : ""}`} onClick={() => setPage("overview")} aria-current={page === "overview" ? "page" : undefined}><Activity size={18} /> Overview</button>
        <button className={`nav-item ${page === "appointments" ? "active" : ""}`} onClick={() => setPage("appointments")} aria-current={page === "appointments" ? "page" : undefined}><CalendarDays size={18} /> Appointments</button>
        <button className={`nav-item ${page === "doctors" ? "active" : ""}`} onClick={() => setPage("doctors")} aria-current={page === "doctors" ? "page" : undefined}><Stethoscope size={18} /> Doctors</button>
        <div className="sidebar-bottom"><ShieldCheck size={17} /><span>Private by design<br/><small>Voice session demo</small></span></div>
      </aside>

      <section className="main-content">
        <header className="topbar"><div><span className="eyebrow">YOUR HEALTH, SIMPLIFIED</span><h1>Good day <span>👋</span></h1><p>Manage appointments with a conversation.</p></div><div className={`api-pill ${apiState}`}><span className="status-dot" />{apiState === "online" ? "API connected" : apiState === "offline" ? "API offline" : "Connecting"}</div></header>

        <section className={`welcome-card ${voiceState === "connected" ? "voice-active" : ""}`}>
          <div className="welcome-copy"><div className="live-label"><span className="pulse-dot" /> {voiceState === "connected" ? "VOICE SESSION LIVE" : voiceState === "connecting" ? "CONNECTING TO ASSISTANT" : "VOICE ASSISTANT"}</div><h2>{voiceState === "connected" ? <>You're connected.<br/>How can I help?</> : <>How can we help<br/>you feel better?</>}</h2><p>Talk naturally to book, manage, or reschedule a doctor appointment.</p><div className="voice-actions">{voiceState === "connected" || voiceState === "connecting" ? <button className="primary-button hangup" onClick={() => void endVoiceCall()}><PhoneOff size={18}/> End call</button> : <button className="primary-button" onClick={() => void startVoiceCall()} disabled={apiState !== "online"}><Mic size={18}/> Start a voice call</button>}<span className="secure-note"><ShieldCheck size={15}/> Microphone permission required</span></div>{voiceError && <p className="voice-error" role="alert">{voiceError}</p>}</div>
          <div className="voice-visual" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="voice-core"><Mic size={38}/></div><span className="wave wave-a"/><span className="wave wave-b"/><span className="wave wave-c"/></div>
        </section>
        <audio ref={audioRef} autoPlay playsInline />

        {transcript.length > 0 && <section className="appointments-panel transcript-panel"><div className="panel-heading"><div><h2>Conversation</h2><p>Live transcript from your voice session.</p></div><span className="panel-icon"><Mic size={19}/></span></div><div className="transcript-list" aria-live="polite">{transcript.map((line) => <div className={`transcript-line ${line.speaker === "You" ? "user-line" : "bot-line"}`} key={line.id}><strong>{line.speaker}</strong><p>{line.text}</p></div>)}</div></section>}

        {page === "overview" && <>
        <div className="section-heading"><div><h2>Your care at a glance</h2><p>A clear view of your appointment activity.</p></div><button className="text-button" onClick={() => setPage("appointments")}>View all <span>→</span></button></div>
        <div className="stats-grid"><article className="stat-card"><div className="stat-icon blue"><CalendarDays size={19}/></div><span className="stat-label">Appointments</span><strong>{appointments.length}</strong><small>Recent bookings</small></article><article className="stat-card"><div className="stat-icon green"><Users size={19}/></div><span className="stat-label">Doctors</span><strong>{doctors.length}</strong><small>Available specialists</small></article><article className="stat-card"><div className="stat-icon amber"><Clock3 size={19}/></div><span className="stat-label">Next visit</span><strong>{appointments.filter((item) => item.status.toLowerCase() !== "cancelled" && new Date(item.start_time).getTime() >= Date.now()).sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())[0] ? formatAppointmentDateTime(appointments.filter((item) => item.status.toLowerCase() !== "cancelled" && new Date(item.start_time).getTime() >= Date.now()).sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())[0].start_time).split(",")[0] : "—"}</strong><small>Your upcoming care</small></article></div>

        <section className="appointments-panel"><div className="panel-heading"><div><h2>Recent appointments</h2><p>Your latest appointment updates will appear here.</p></div><button className="icon-button" onClick={() => void refreshDashboard()} disabled={dataLoading} aria-label="Refresh recent appointments"><CalendarDays size={19}/></button></div>{dataError && <p className="data-error" role="alert">{dataError}</p>}{dataLoading ? <p className="data-message">Loading appointments…</p> : appointments.length === 0 ? <div className="empty-state"><div className="empty-icon"><CalendarDays size={24}/></div><strong>Nothing scheduled yet</strong><p>Once you book an appointment, you'll find the details here.</p></div> : <div className="data-list">{appointments.slice(0,4).map((item) => <article className="data-row" key={item.appointment_id}><div><strong>{formatPatientName(item.patient_name)}</strong><p>{item.doctor_name} · {item.specialty}</p><small>{formatAppointmentDateTime(item.start_time)}</small></div><span className={`appointment-status ${item.status.toLowerCase()}`}>{item.status}</span></article>)}</div>}</section>
        </>}

        {page === "appointments" && <section className="appointments-panel page-panel">
          <div className="panel-heading"><div><h2>Appointments</h2><p>Your appointment history and upcoming visits.</p></div><button className="icon-button" onClick={() => void refreshDashboard()} disabled={dataLoading} aria-label="Refresh appointments"><Activity size={17}/></button></div>
          <div className="appointment-filters" role="group" aria-label="Filter appointments">
            {(["all", "upcoming", "completed", "cancelled"] as AppointmentFilter[]).map((filter) => <button key={filter} type="button" className={appointmentFilter === filter ? "filter-chip active" : "filter-chip"} aria-pressed={appointmentFilter === filter} onClick={() => setAppointmentFilter(filter)}>{filter === "all" ? "All" : filter[0].toUpperCase() + filter.slice(1)}</button>)}
          </div>
          {dataError && <p className="data-error" role="alert">{dataError}</p>}
          {dataLoading ? <p className="data-message">Loading appointments…</p> : appointments.length === 0 ? <div className="empty-state"><div className="empty-icon"><CalendarDays size={24}/></div><strong>No appointments found</strong><p>Appointments booked through Voice Doctor will appear here.</p></div> :
            appointments.filter((item) => appointmentMatchesFilter(item, appointmentFilter)).length === 0 ? <div className="empty-state compact-empty"><strong>No {appointmentFilter} appointments</strong><p>Try another filter to see your appointment activity.</p></div> :
            <div className="data-list">{appointments.filter((item) => appointmentMatchesFilter(item, appointmentFilter)).sort((a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime()).map((item) => <article className="data-row" key={item.appointment_id}><div><strong>{formatPatientName(item.patient_name)}</strong><p>{item.doctor_name} · {item.specialty}</p><small>{formatAppointmentDateTime(item.start_time)}</small></div><span className={`appointment-status ${item.status.toLowerCase()}`}>{item.status}</span></article>)}</div>}
        </section>}

        {page === "doctors" && <section className="appointments-panel page-panel">
          <div className="panel-heading"><div><h2>Doctors</h2><p>Browse available specialists.</p></div><button className="icon-button" onClick={() => void refreshDashboard()} disabled={dataLoading} aria-label="Refresh doctors"><Activity size={17}/></button></div>
          {dataError && <p className="data-error" role="alert">{dataError}</p>}
          {dataLoading ? <p className="data-message">Loading doctors…</p> : doctors.length === 0 ? <div className="empty-state"><div className="empty-icon"><Stethoscope size={24}/></div><strong>No doctors available</strong><p>Check back when the doctor directory is populated.</p></div> :
            <div className="doctor-grid">{doctors.map((doctor) => <article className="doctor-card" key={doctor.id}><div className="doctor-avatar"><Stethoscope size={20}/></div><div><strong>{doctor.name}</strong><p>{doctor.specialty}</p>{doctor.description && <small>{doctor.description}</small>}</div></article>)}</div>}
        </section>}

        <footer><span>© 2026 NexovAI</span><span className="backend-status"><span className={`status-dot ${apiState}`}/>{apiMessage}</span><span className="backend-status"><Wifi size={12}/>{transportState}</span></footer>
      </section>
    </main>
  );
}
