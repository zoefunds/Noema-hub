"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { DossierCard } from "./DossierCard";
import { listDossiers } from "@/lib/liveProtocol";
import type { Dossier } from "@/lib/types";

export function FieldLive({ compact = false }: { compact?: boolean }) {
  const [items, setItems] = useState<Dossier[]>([]); const [error, setError] = useState(""); const [loading, setLoading] = useState(true);
  useEffect(() => { listDossiers(0, compact ? 3 : 24).then((value) => setItems([...value].reverse()))
    .catch((reason) => setError(reason instanceof Error ? reason.message : "Studionet read failed")).finally(() => setLoading(false)); }, [compact]);
  if (loading) return <div className="vault-empty"><div><div className="eyebrow">Studionet</div><h2>Reading the live field…</h2></div></div>;
  if (error) return <div className="vault-empty"><div><div className="eyebrow">Network read failed</div><h2>{error}</h2><p>Confirm the production Hub address and Studionet availability.</p></div></div>;
  if (!items.length) return <div className="vault-empty"><div><div className="eyebrow">Field ready</div><h2>Awaiting the first production dossier.</h2><p>No illustrative market data is shown. Every dossier here comes from the deployed Hub.</p><Link className="button primary" href="/field/new">Open a dossier</Link></div></div>;
  return <div className="dossier-list">{items.map((dossier, index) => <DossierCard dossier={dossier} index={index} key={dossier.id} />)}</div>;
}
