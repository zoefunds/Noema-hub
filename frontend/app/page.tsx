import Link from "next/link";
import { FieldLive } from "@/components/FieldLive";

export default function Home() {
  return <>
    <section className="hero grid-paper">
      <div className="hero-copy">
        <div className="kicker">A public research settlement protocol</div>
        <h1>Fund the fact<br /><em>that changes the record.</em></h1>
        <p className="lede">Noema turns unresolved public questions into bounded research dossiers. Sources are fetched by independent validators. The first disclosure that makes the rule decidable earns the reward.</p>
        <div className="hero-actions"><Link className="button primary" href="/field/new">Open a dossier</Link><Link className="button text" href="/field">Enter the field <span>→</span></Link></div>
      </div>
      <div className="hero-instrument" aria-label="Protocol stages">
        <div className="orbit o1" /><div className="orbit o2" />
        <div className="instrument-center"><span>network state</span><strong>LIVE</strong><small>Studionet · 61999</small></div>
        {[["01", "Frame"], ["02", "Witness"], ["03", "Resolve"]].map(([n, label], i) =>
          <div className={`instrument-node n${i + 1}`} key={n}><b>{n}</b><span>{label}</span></div>)}
      </div>
      <div className="hero-rail"><span>CONSENSUS FIELD / 61999</span><i /><span>SCROLL TO OBSERVE</span></div>
    </section>

    <section className="dispatch">
      <div className="section-heading"><span className="section-no">01</span><div><p>Current dispatches</p><h2>Questions still looking for their last fact.</h2></div><Link href="/field">View all dossiers ↗</Link></div>
      <FieldLive compact />
    </section>

    <section className="method-strip">
      <div className="section-heading inverse"><span className="section-no">02</span><div><p>The method</p><h2>Every economic decision leaves a proof trail.</h2></div></div>
      <div className="method-grid">
        <article><span>α</span><h3>Seal the lead</h3><p>A private commitment reserves a source and claim before either becomes visible.</p></article>
        <article><span>β</span><h3>Witness the source</h3><p>Validators fetch independently and bind the publisher, content digest, canonical location, time and six validity checks.</p></article>
        <article><span>γ</span><h3>Resolve the dossier</h3><p>A separate engine compares the exact evidence manifest, decisive IDs and closure basis before settlement.</p></article>
      </div>
      <Link href="/method" className="method-link">Read the protocol field notes <span>↗</span></Link>
    </section>

    <section className="limits">
      <div><span>18</span><p>attested records maximum per dossier</p></div>
      <div><span>72</span><p>lifetime disclosures maximum per dossier</p></div>
      <div><span>0</span><p>admin overrides or mutable adjudicators</p></div>
      <blockquote>“A conclusion is only as durable as the trail that produced it.”</blockquote>
    </section>
  </>;
}
