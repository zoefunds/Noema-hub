"use client";

import { useState } from "react";
import type { Dossier } from "@/lib/types";
import { connectWallet, disclosureCommitment, HUB_ADDRESS, randomSalt, savePending, submitHubWrite,
  waitForFinalization, getSubmissionForCommitment, updatePending, EXPLORER_URL } from "@/lib/liveProtocol";

export function DisclosureForm({ dossier }: { dossier: Dossier }) {
  const [url, setUrl] = useState(""); const [claim, setClaim] = useState(""); const [notice, setNotice] = useState("");
  function loadVerifiedEvidence() {
    setUrl("https://raw.githubusercontent.com/openai/codex/main/LICENSE");
    setClaim("The official LICENSE file on the openai/codex main branch explicitly declares Apache License Version 2.0, January 2004, and contains its terms and conditions for use, reproduction, and distribution.");
    setNotice("First-party public evidence loaded. Use it only when it directly answers this dossier's question.");
  }
  async function prepare(event: React.FormEvent) {
    event.preventDefault();
    try {
      if (!HUB_ADDRESS) throw new Error("Deployment address is not configured. Add NEXT_PUBLIC_NOEMA_HUB_ADDRESS.");
      const account = await connectWallet(); const salt = randomSalt();
      const base = { dossierId: dossier.id, url: url.trim(), claim: claim.trim(), salt };
      const commitment = disclosureCommitment(base, HUB_ADDRESS, account);
      savePending({ ...base, commitment, createdAt: new Date().toISOString() });
      setNotice("Confirm the sealed disclosure in your wallet…");
      const hash = await submitHubWrite(account, "seal_disclosure", [dossier.id, commitment], BigInt(dossier.bond_atto));
      setNotice(`Seal submitted (${hash.slice(0, 12)}…). Waiting for finality…`);
      await waitForFinalization(hash);
      const submissionId = await getSubmissionForCommitment(commitment, false);
      if (!submissionId) throw new Error("Seal finalized but the Hub did not record the commitment.");
      updatePending(commitment, { submissionId });
      setNotice(`Seal finalized as ${submissionId}. Your claim and salt remain only in this browser. Open Vault to reveal. Explorer: ${EXPLORER_URL}/tx/${hash}`);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not prepare disclosure."); }
  }
  return <form className="submission-box" onSubmit={prepare}><div className="eyebrow">Research disclosure</div><h3>Bring the record that settles it.</h3><p>The claim and source stay local until your on-chain seal finalizes.</p><button type="button" className="autofill-dark" onClick={loadVerifiedEvidence}>Load real license evidence ↘</button><label htmlFor="url">Public HTTPS source</label><input id="url" type="url" required value={url} onChange={(e) => setUrl(e.target.value)} /><label htmlFor="claim">Exact fact established</label><textarea id="claim" required value={claim} onChange={(e) => setClaim(e.target.value)} /><button type="submit">Prepare sealed disclosure</button>{notice && <p role="status" className="manifest">{notice}</p>}</form>;
}
