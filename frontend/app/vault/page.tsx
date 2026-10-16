import { VaultLive } from "./VaultLive";

export default function VaultPage() {
  return <section className="page-shell"><div className="page-title"><div><div className="kicker">Wallet vault</div><h1>Your research trail</h1></div><p>Recover pending reveals, inspect bonds and withdraw credited rewards from one place.</p></div><VaultLive /></section>;
}
