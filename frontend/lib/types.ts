export type EvidenceRecord = {
  id: string;
  kind: "BASELINE" | "RESEARCH";
  requested_url: string;
  source_host: string;
  canonical_url: string;
  publisher: string;
  published_at: string;
  claim: string;
  claim_digest: string;
  content_digest: string;
  observed_at: string;
  http_status: number;
};

export type Dossier = {
  id: string;
  title: string;
  question: string;
  decision_rule: string;
  position_a: string;
  position_b: string;
  source_policy: string;
  sponsor: string;
  status: string;
  reward_atto: string;
  bond_atto: string;
  closes_at: string;
  evidence: EvidenceRecord[];
  manifest_root: string;
  submission_ids: string[];
  active_ids: string[];
  resolution: string;
  decisive_ids: string[];
  closure_basis: string;
};

export type PendingDisclosure = {
  dossierId: string;
  submissionId?: string;
  url: string;
  claim: string;
  salt: string;
  commitment: string;
  createdAt: string;
};

export type PendingPayout = {
  account: string;
  parentHash: string;
  amount: string;
  walletBefore: string;
  createdAt: string;
};
