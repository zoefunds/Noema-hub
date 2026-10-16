import Link from "next/link";
import type { Dossier } from "@/lib/types";
import { formatGen } from "@/lib/liveProtocol";

export function DossierCard({ dossier, index }: { dossier: Dossier; index: number }) {
  const resolved = dossier.status === "RESOLVED";
  return <Link href={`/field/${dossier.id}`} className="dossier-card">
    <div className="card-index">{String(index + 1).padStart(2, "0")}</div>
    <div className="card-main">
      <div className="eyebrow"><span className={`signal ${resolved ? "resolved" : ""}`} />{dossier.status.replaceAll("_", " ")}</div>
      <h3>{dossier.title}</h3>
      <p>{dossier.question}</p>
    </div>
    <div className="card-facts">
      <div><span>reward</span><strong>{resolved ? "settled" : `${formatGen(dossier.reward_atto)} GEN`}</strong></div>
      <div><span>sources</span><strong>{dossier.evidence.length} / 18</strong></div>
      <div><span>sealed notes</span><strong>{dossier.submission_ids.length}</strong></div>
    </div>
    <span className="card-arrow">↗</span>
  </Link>;
}
