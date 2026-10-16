import Link from "next/link";
import { FieldLive } from "@/components/FieldLive";

export default function FieldPage() {
  return <section className="page-shell">
    <div className="page-title"><div><div className="kicker">Signal exchange</div><h1>Live inquiries</h1></div><p>Inspect bounded questions, trace their evidence state, or submit a source that lets independent witnesses close the record.</p></div>
    <div className="filter-row"><span className="chip active">Live Studionet</span><span className="chip">18 evidence slots</span><span className="chip">72 lifetime notes</span><Link className="chip" href="/field/new">+ New dossier</Link></div>
    <FieldLive />
  </section>;
}
