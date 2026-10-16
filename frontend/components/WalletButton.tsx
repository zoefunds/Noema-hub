"use client";

import { useState } from "react";
import { connectWallet } from "@/lib/liveProtocol";

export function WalletButton() {
  const [address, setAddress] = useState("");
  const [error, setError] = useState("");
  async function connect() {
    try { setError(""); setAddress(await connectWallet()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Wallet connection failed"); }
  }
  return <div className="wallet-wrap">
    <button className="wallet" onClick={connect}>{address ? `${address.slice(0, 6)}…${address.slice(-4)}` : "Connect field wallet"}</button>
    {error && <span className="wallet-error" role="alert">{error}</span>}
  </div>;
}
