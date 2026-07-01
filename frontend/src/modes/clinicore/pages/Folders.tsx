import { useState } from "react";
import { Link } from "react-router-dom";
import {
  FolderClosed, Folder, Plus, Share2, Lock, ShieldOff, X, Check,
  Stethoscope, Clock, Mail,
} from "lucide-react";
import { ClinHeader } from "../ClinHeader";

/**
 * Consultation folders + sharing — ported from clinicore-backend folder.py /
 * share.py. Folders organise consultations (coloured, optional zero-retention
 * mode). Sharing grants a named recipient (by clinical role) granular,
 * time-boxed access to a folder.
 */
interface Consult { id: string; patient: string; complaint: string; when: string }
interface FolderT { id: string; name: string; color: string; zeroRetention: boolean; consults: Consult[] }

const FOLDERS: FolderT[] = [
  { id: "f1", name: "Cardiology reviews", color: "var(--brand)", zeroRetention: false, consults: [
    { id: "c1", patient: "Anita R., 58F", complaint: "Exertional chest tightness", when: "Today" },
    { id: "c2", patient: "Vikram S., 64M", complaint: "Palpitations, HTN", when: "Yesterday" },
  ] },
  { id: "f2", name: "Second opinions", color: "var(--teal)", zeroRetention: true, consults: [
    { id: "c3", patient: "Fatima K., 41F", complaint: "Thyroid nodule — needs radiology", when: "2d ago" },
  ] },
  { id: "f3", name: "Diabetology", color: "var(--ochre)", zeroRetention: false, consults: [
    { id: "c4", patient: "Suresh M., 52M", complaint: "Poorly controlled T2DM", when: "3d ago" },
  ] },
];

export function Folders() {
  const [active, setActive] = useState("f1");
  const [share, setShare] = useState<FolderT | null>(null);
  const folder = FOLDERS.find((f) => f.id === active)!;

  return (
    <div>
      <ClinHeader icon={FolderClosed} title="Consultation Folders" subtitle="Organise cases into folders and share them securely with colleagues." />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
        {/* Folder list */}
        <div className="space-y-2">
          {FOLDERS.map((f) => (
            <button key={f.id} onClick={() => setActive(f.id)} className="w-full soft-card p-3 flex items-center gap-3 text-left transition-all"
              style={active === f.id ? { borderColor: f.color } : {}}>
              <div className="w-9 h-9 rounded-lg grid place-items-center text-white shrink-0" style={{ background: f.color }}><Folder className="w-4 h-4" /></div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{f.name}</div>
                <div className="text-[11px] text-muted-foreground">{f.consults.length} consultation{f.consults.length !== 1 ? "s" : ""}</div>
              </div>
              {f.zeroRetention && <Lock className="w-3.5 h-3.5 shrink-0" style={{ color: "var(--teal)" }} />}
            </button>
          ))}
          <button className="w-full soft-card p-3 flex items-center justify-center gap-2 text-sm font-medium text-brand border-dashed" style={{ borderStyle: "dashed" }}>
            <Plus className="w-4 h-4" /> New folder
          </button>
        </div>

        {/* Folder contents */}
        <div className="lg:col-span-3 soft-card p-5 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg grid place-items-center text-white" style={{ background: folder.color }}><Folder className="w-4 h-4" /></div>
              <h3 className="text-base font-semibold">{folder.name}</h3>
              {folder.zeroRetention && <span className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full" style={{ background: "color-mix(in oklab, var(--teal) 14%, white)", color: "color-mix(in oklab, var(--teal) 60%, black)" }}><ShieldOff className="w-3 h-3" /> zero-retention</span>}
            </div>
            <button onClick={() => setShare(folder)} className="flex items-center gap-1.5 text-sm font-semibold px-3 py-1.5 rounded-lg text-white" style={{ background: "var(--brand)" }}><Share2 className="w-4 h-4" /> Share folder</button>
          </div>

          {folder.zeroRetention && (
            <div className="rounded-lg p-2.5 mb-3 text-[11px]" style={{ background: "color-mix(in oklab, var(--teal) 8%, white)" }}>
              <strong>Zero-retention mode:</strong> messages in this folder are processed in memory and not persisted after the session closes.
            </div>
          )}

          <div className="space-y-2">
            {folder.consults.map((c) => (
              <Link key={c.id} to={`/clinicore/consultation/${c.id}`} className="flex items-center gap-3 p-3 rounded-lg border hover:shadow-md transition-shadow">
                <div className="w-9 h-9 rounded-lg grid place-items-center bg-chip text-brand shrink-0"><Stethoscope className="w-4 h-4" /></div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{c.patient}</div>
                  <div className="text-[11px] text-muted-foreground">{c.complaint}</div>
                </div>
                <span className="text-[11px] text-muted-foreground flex items-center gap-1"><Clock className="w-3 h-3" /> {c.when}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {share && <ShareDialog folder={share} onClose={() => setShare(null)} />}
    </div>
  );
}

function ShareDialog({ folder, onClose }: { folder: FolderT; onClose: () => void }) {
  const [perms, setPerms] = useState({ messages: true, images: true, comments: false, reshare: false });
  const [expiry, setExpiry] = useState(72);
  const [sent, setSent] = useState(false);

  const toggle = (k: keyof typeof perms) => setPerms((p) => ({ ...p, [k]: !p[k] }));

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="soft-card p-6 w-full max-w-md animate-fade-in" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2"><Share2 className="w-4 h-4 text-brand" /> Share "{folder.name}"</h3>
          <button onClick={onClose} className="w-8 h-8 grid place-items-center rounded-lg hover:bg-black/5"><X className="w-4 h-4" /></button>
        </div>

        {sent ? (
          <div className="text-center py-6">
            <div className="w-12 h-12 rounded-full grid place-items-center mx-auto mb-3" style={{ background: "color-mix(in oklab, var(--success) 14%, white)", color: "var(--success)" }}><Check className="w-6 h-6" /></div>
            <div className="font-medium">Secure share link created</div>
            <p className="text-xs text-muted-foreground mt-1">Expires in {expiry}h · access is audit-logged and revocable anytime.</p>
          </div>
        ) : (
          <>
            <div className="space-y-3">
              <input placeholder="Recipient name" className="w-full px-3.5 py-2.5 rounded-lg border bg-white outline-none text-sm" />
              <select className="w-full px-3.5 py-2.5 rounded-lg border bg-white outline-none text-sm">
                <option>Radiologist</option><option>Dermatologist</option><option>Cardiologist</option><option>Endocrinologist</option><option>General Physician</option>
              </select>
              <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-lg border bg-white">
                <Mail className="w-4 h-4 text-muted-foreground" />
                <input placeholder="Recipient email (optional)" className="flex-1 bg-transparent outline-none text-sm" />
              </div>
            </div>

            <div className="mt-4">
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Permissions</div>
              <div className="space-y-1.5">
                {([
                  { k: "messages", l: "Can view messages" },
                  { k: "images", l: "Can view images" },
                  { k: "comments", l: "Can add comments" },
                  { k: "reshare", l: "Can re-share" },
                ] as const).map((p) => (
                  <label key={p.k} className="flex items-center justify-between text-sm rounded-lg border p-2.5 cursor-pointer">
                    {p.l}
                    <button onClick={() => toggle(p.k)} className="w-9 h-5 rounded-full p-0.5 transition-colors" style={{ background: perms[p.k] ? "var(--brand)" : "var(--muted)" }}>
                      <span className="block w-4 h-4 rounded-full bg-white shadow-sm transition-transform" style={{ transform: perms[p.k] ? "translateX(16px)" : "none" }} />
                    </button>
                  </label>
                ))}
              </div>
            </div>

            <div className="mt-4">
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Link expiry</label>
              <div className="flex gap-2 mt-1.5">
                {[24, 72, 168].map((h) => (
                  <button key={h} onClick={() => setExpiry(h)} className="flex-1 py-2 rounded-lg border text-xs font-medium transition-all"
                    style={expiry === h ? { borderColor: "var(--brand)", color: "var(--brand)", background: "color-mix(in oklab, var(--brand) 6%, white)" } : {}}>
                    {h === 24 ? "24h" : h === 72 ? "3 days" : "1 week"}
                  </button>
                ))}
              </div>
            </div>

            <button onClick={() => setSent(true)} className="w-full mt-5 py-3 rounded-xl text-white font-semibold" style={{ background: "var(--brand)" }}>Create secure share link</button>
            <p className="text-[10px] text-muted-foreground text-center mt-2">Sharing is DPDP-consent-scoped, time-boxed, and every access is audit-logged.</p>
          </>
        )}
      </div>
    </div>
  );
}
