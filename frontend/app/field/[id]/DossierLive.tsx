"use client";

import { useEffect, useState } from "react";
import { getDossier, formatGen } from "@/lib/liveProtocol";
import type { Dossier } from "@/lib/types";
import { DisclosureForm } from "./DisclosureForm";

export function DossierLive({ id }: { id: string }) {
  const [dossier, setDossier] = useState<Dossier | null>(null); const [error, setError] = useState("");
  useEffect(() => { getDossier(id).then(setDossier).catch((reason) => setError(reason instanceof Error ? reason.message : "Dossier read failed")); }, [id]);
  if (error) return <section className="page-shell"><div className="vault-empty"><div><div className="eyebrow">Studionet read failed</div><h2>{error}</h2></div></div></section>;
  if (!dossier) return <section className="page-shell"><div className="vault-empty"><div><div className="eyebrow">Studionet</div><h2>Reading {id}…</h2></div></div></section>;
  return <>
    <section className="detail-head"><div><div className="eyebrow"><span className={`signal ${dossier.status === "RESOLVED" ? "resolved" : ""}`} />{dossier.status} · {dossier.id}</div><h1>{dossier.title}</h1><p className="lede">{dossier.question}</p>
      <div className="detail-meta"><div><span>Sponsor</span><strong>{dossier.sponsor}</strong></div><div><span>Evidence load</span><strong>{dossier.evidence.length} / 18 records</strong></div><div><span>Lifetime disclosures</span><strong>{dossier.submission_ids.length} / 72</strong></div><div><span>Active</span><strong>{dossier.active_ids.length}</strong></div></div></div>
      <aside className="reward-panel"><span>Decisive research reward</span><strong>{BigInt(dossier.reward_atto) > 0n ? `${formatGen(dossier.reward_atto)} GEN` : "Settled"}</strong><p>Bond: {formatGen(dossier.bond_atto)} GEN · returned after an attested disclosure.</p></aside></section>
    <section className="detail-grid"><aside className="detail-aside"><h2>Decision frame</h2><div className="rule-box">{dossier.decision_rule}</div><div className="position"><span>POSITION A</span><strong>{dossier.position_a}</strong></div><div className="position"><span>POSITION B</span><strong>{dossier.position_b}</strong></div><div className="position"><span>SOURCE POLICY</span><strong>{dossier.source_policy}</strong></div></aside>
      <div className="evidence-panel"><h2>Witnessed manifest</h2><p className="manifest">ROOT / {dossier.manifest_root || "pending baseline witness"}</p>
        {dossier.evidence.map((record) => <article className="evidence-item" key={record.id}><span className="ev-id">{record.id}</span><div className="ev-main"><div className="eyebrow">{record.publisher || record.source_host} · HTTP {record.http_status}</div><p>{record.claim}</p><div className="provenance"><span>host / {record.source_host}</span><span>content / {record.content_digest.slice(0, 12)}…</span><span>claim / {record.claim_digest.slice(0, 12)}…</span><span>observed / {record.observed_at.slice(0, 10)}</span></div></div></article>)}
        {dossier.status === "OPEN" ? <DisclosureForm dossier={dossier} /> : dossier.status === "RESOLVED" ? <div className="submission-box"><div className="eyebrow">Final resolution</div><h3>{dossier.resolution.replaceAll("_", " ")}</h3><p>{dossier.closure_basis}</p><p className="manifest">Decisive records / {dossier.decisive_ids.join(", ")}</p></div> : <div className="submission-box"><div className="eyebrow">Consensus stage</div><h3>{dossier.status.replaceAll("_", " ")}</h3><p>The Hub is waiting for the current finalized callback.</p></div>}
      </div></section>
  </>;
}
