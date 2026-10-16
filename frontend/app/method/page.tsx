const rows = [
  ["Source identity", "Requested URL and host; response origin stays explicitly unverified when transport data is unavailable", "Witness consensus"],
  ["Source content", "SHA-256 of the fetched response body and HTTP status", "Witness consensus"],
  ["Claim validity", "Six independent admissibility and support fields", "Witness consensus"],
  ["Closure record", "Manifest root, outcome, decisive IDs and basis digest", "Verdict consensus"],
  ["Economic path", "Escrow, bonds, pull credits, staged deadlines and accounting identity", "Deterministic state"],
];

export default function MethodPage() {
  return <div className="method-page"><section className="method-hero"><div className="kicker">Protocol field notes</div><h1>Consensus where judgment touches money.</h1><p className="lede">Noema separates source truth from decision sufficiency. Each stage independently replays the fields that can change settlement, while deterministic limits keep every dossier finite.</p><div className="protocol-map">{[["01","Sponsor frames terms"],["02","Baseline is witnessed"],["03","Researcher seals a lead"],["04","Source is attested"],["05","Verdict settles escrow"]].map(([n,t])=><div key={n}><span>{n}</span><strong>{t}</strong></div>)}</div></section>
    <section className="trust-table">{rows.map(([a,b,c])=><div className="trust-row" key={a}><strong>{a}</strong><p>{b}</p><span>{c}</span></div>)}</section>
  </div>;
}
