import Link from "next/link";
import { Mark } from "./Mark";
import { WalletButton } from "./WalletButton";

export function Chrome({ children }: { children: React.ReactNode }) {
  return <>
    <header className="topbar">
      <Link href="/"><Mark /></Link>
      <nav aria-label="Primary">
        <Link href="/field">Field</Link>
        <Link href="/method">Method</Link>
        <Link href="/vault">Vault</Link>
      </nav>
      <WalletButton />
    </header>
    <main>{children}</main>
    <footer><Mark compact /><p>Public claims, witnessed at the source.</p><span>GenLayer Studionet · 61999</span></footer>
  </>;
}
