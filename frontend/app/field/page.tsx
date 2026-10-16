import Link from "next/link";
import { FieldLive } from "@/components/FieldLive";

export default function FieldPage() {
  return <section className="page-shell">
    <div className="page-title"><div><div className="kicker">Research field</div><h1>Open dossiers</h1></div><p>Browse bounded public questions. Find a source that satisfies the rule, seal your lead, and let validators witness it.</p></div>
    <div className="filter-row"><span className="chip active">Live Studionet</span><span className="chip">18 evidence slots</span><span className="chip">72 lifetime notes</span><Link className="chip" href="/field/new">+ New dossier</Link></div>
    <FieldLive />
  </section>;
}
