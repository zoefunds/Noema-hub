"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { connectWallet, EXPLORER_URL, findLatestDossier, parseGen, submitHubWrite, waitForFinalization } from "@/lib/liveProtocol";

type Seed = { url: string; claim: string };

export function NewDossierForm() {
  const router = useRouter();
  const [title,setTitle]=useState(""); const [question,setQuestion]=useState(""); const [rule,setRule]=useState("");
  const [a,setA]=useState(""); const [b,setB]=useState(""); const [policy,setPolicy]=useState("");
  const [seeds,setSeeds]=useState<Seed[]>([{url:"",claim:""}]); const [reward,setReward]=useState(""); const [days,setDays]=useState("7");
  const [busy,setBusy]=useState(false); const [notice,setNotice]=useState("");
  function loadVerifiedExample(){
    setTitle("OpenAI Codex repository license");
    setQuestion("As of 16 October 2026, does the official openai/codex repository's default branch declare the Apache License 2.0?");
    setA("Apache-2.0 declared"); setB("Apache-2.0 not declared");
    setRule("Choose Position A only when the official LICENSE file served from the openai/codex main branch explicitly declares Apache License Version 2.0. Choose Position B only when that official LICENSE file explicitly declares a different license or explicitly states that no license applies. If the official evidence does not establish either condition, leave the dossier unresolved.");
    setPolicy("Accept only files served by raw.githubusercontent.com from the official openai/codex repository's main branch. Exclude mirrors, forks, reposts, social media, search snippets, and third-party summaries.");
    setSeeds([{url:"https://raw.githubusercontent.com/openai/codex/main/README.md",claim:"The official openai/codex README identifies Codex CLI as a coding agent from OpenAI that runs locally on a user's computer."}]);
    setReward("0.001"); setDays("1"); setNotice("Verified public-source example loaded. Review it, connect a funded Studionet wallet, then open the dossier.");
  }
  function seed(index:number,key:keyof Seed,value:string){setSeeds((items)=>items.map((item,i)=>i===index?{...item,[key]:value}:item));}
  async function submit(event:React.FormEvent){ event.preventDefault(); setBusy(true); setNotice("");
    try { const value=parseGen(reward); if(value<10n**15n||value>10n*10n**18n) throw new Error("Reward must be 0.001–10 GEN.");
      if(seeds.some((item)=>!item.url.startsWith("https://")||item.claim.trim().length<8)) throw new Error("Each baseline needs an HTTPS source and exact claim.");
      const account=await connectWallet(); const closesAt=BigInt(Math.floor(Date.now()/1000+Number(days)*86400));
      setNotice("Confirm the funded dossier in your wallet…");
      const hash=await submitHubWrite(account,"open_dossier",[title.trim(),question.trim(),rule.trim(),a.trim(),b.trim(),policy.trim(),JSON.stringify(seeds),closesAt],value);
      setNotice(`Submitted ${hash.slice(0,14)}… Waiting for Studionet finality. ${EXPLORER_URL}/tx/${hash}`); await waitForFinalization(hash);
      const id=await findLatestDossier(account); setNotice(`Finalized as ${id}. Baseline witnessing is now underway.`); router.push(`/field/${id}`);
    } catch(error){setNotice(error instanceof Error?error.message:"Dossier creation failed.");} finally{setBusy(false);} }
  return <form className="form-grid" style={{marginTop:45}} onSubmit={submit}><div className="wide example-loader"><div><span>Public test dossier</span><strong>Use a real OpenAI repository question and first-party evidence.</strong></div><button type="button" onClick={loadVerifiedExample}>Load verified example ↘</button></div><div className="wide form-note">Every baseline source is fetched and attested before the dossier can open. If the baseline already decides the question, your reward is returned as Hub credit.</div>
    <label className="wide">Working title<input required minLength={4} maxLength={96} value={title} onChange={(e)=>setTitle(e.target.value)} /></label>
    <label className="wide">Public question<textarea required minLength={20} maxLength={1800} value={question} onChange={(e)=>setQuestion(e.target.value)} /></label>
    <label>Position A<input required minLength={2} maxLength={90} value={a} onChange={(e)=>setA(e.target.value)} /></label><label>Position B<input required minLength={2} maxLength={90} value={b} onChange={(e)=>setB(e.target.value)} /></label>
    <label className="wide">Decision rule<textarea required minLength={30} maxLength={2600} value={rule} onChange={(e)=>setRule(e.target.value)} /></label>
    <label className="wide">Allowed source policy<textarea required minLength={15} maxLength={1600} value={policy} onChange={(e)=>setPolicy(e.target.value)} /></label>
    {seeds.map((item,index)=><div className="wide baseline-editor" key={index}><div className="eyebrow">Baseline {index+1}</div><label>HTTPS source<input type="url" required value={item.url} onChange={(e)=>seed(index,"url",e.target.value)} /></label><label>Exact claim established<textarea required value={item.claim} onChange={(e)=>seed(index,"claim",e.target.value)} /></label>{seeds.length>1&&<button type="button" className="chip" onClick={()=>setSeeds((items)=>items.filter((_,i)=>i!==index))}>Remove source</button>}</div>)}
    {seeds.length<4&&<button type="button" className="chip" onClick={()=>setSeeds((items)=>[...items,{url:"",claim:""}])}>+ Add baseline source</button>}
    <label>Reward in GEN<input type="text" inputMode="decimal" required value={reward} onChange={(e)=>setReward(e.target.value)} /></label><label>Research closes<select value={days} onChange={(e)=>setDays(e.target.value)}><option value="1">In 24 hours</option><option value="7">In 7 days</option><option value="14">In 14 days</option><option value="21">In 21 days</option></select></label>
    {notice&&<div className="wide form-note" role="status">{notice}</div>}<div className="wide form-actions"><button type="submit" disabled={busy}>{busy?"Finalizing on Studionet…":"Fund and open dossier →"}</button></div>
  </form>;
}
