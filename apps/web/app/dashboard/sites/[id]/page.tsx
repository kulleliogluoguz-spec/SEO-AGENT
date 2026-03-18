"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost";

export default function SiteDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [site, setSite] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("access_token") || "";
    if (!token || !id) return;
    fetch(API + "/api/v1/sites/" + id, {
      headers: { Authorization: "Bearer " + token },
    })
      .then(function(r) { if (!r.ok) throw new Error("Failed"); return r.json(); })
      .then(setSite)
      .catch(function(e) { setError(e.message); });
  }, [id]);

  const runAnalysis = async function(engine: string, message: string) {
    setAnalyzing(true);
    setAnalysis(null);
    try {
      const r = await fetch(API + "/api/v1/ai/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message, engine: engine, max_tokens: 2048 }),
      });
      setAnalysis(await r.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setAnalyzing(false);
    }
  };

  if (error && !site) return <div style={{padding:"2rem",color:"red"}}>Error: {error}</div>;
  if (!site) return <div style={{padding:"2rem",color:"#888"}}>Loading...</div>;

  var desc = site.product_summary || "";
  var url = site.url || "";
  var name = site.name || "";

  var buttons = [
    {label:"SEO Audit",engine:"reasoning",color:"#2563eb",msg:"Perform a technical SEO audit for " + url + ". Give 5 prioritized recommendations."},
    {label:"Content Strategy",engine:"content_strategy",color:"#9333ea",msg:"Create a content strategy for " + url + ". Include topic clusters and keywords."},
    {label:"Competitor Analysis",engine:"competitor_reasoning",color:"#ea580c",msg:"Identify top 3 competitors for " + url + " and compare SEO strategies."},
    {label:"AI Visibility",engine:"visibility_reasoning",color:"#0d9488",msg:"Analyze AI visibility for " + url + ". Give improvement tips."},
    {label:"Recommendations",engine:"recommendation",color:"#059669",msg:"Generate 5 growth recommendations for " + url + "."},
    {label:"Social Content",engine:"social_adaptation",color:"#db2777",msg:"Create social media plan for " + url + " for LinkedIn, Twitter, Instagram."},
  ];

  return (
    <div style={{padding:"2rem",maxWidth:"900px",margin:"0 auto"}}>
      <div style={{background:"white",borderRadius:"8px",border:"1px solid #e5e7eb",padding:"1.5rem",marginBottom:"1.5rem"}}>
        <h1 style={{fontSize:"1.5rem",fontWeight:"bold",margin:0}}>{name}</h1>
        <a href={url} target="_blank" style={{color:"#2563eb",fontSize:"0.875rem"}}>{url}</a>
        <span style={{marginLeft:"1rem",padding:"4px 12px",borderRadius:"999px",fontSize:"0.75rem",background:site.status==="active"?"#d1fae5":"#fef3c7"}}>{site.status}</span>
      </div>

      <div style={{background:"white",borderRadius:"8px",border:"1px solid #e5e7eb",padding:"1.5rem",marginBottom:"1.5rem"}}>
        <h2 style={{fontSize:"1.125rem",fontWeight:600,marginBottom:"1rem"}}>AI Analysis</h2>
        <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:"0.75rem"}}>
          {buttons.map(function(b) { return (
            <button key={b.label} onClick={function() { runAnalysis(b.engine,b.msg); }} disabled={analyzing}
              style={{padding:"12px",background:b.color,color:"white",border:"none",borderRadius:"8px",cursor:analyzing?"not-allowed":"pointer",opacity:analyzing?0.5:1,fontSize:"0.875rem",fontWeight:500}}>
              {b.label}
            </button>
          ); })}
        </div>
      </div>

      {analyzing && (
        <div style={{background:"white",borderRadius:"8px",border:"1px solid #e5e7eb",padding:"2rem",textAlign:"center",marginBottom:"1.5rem"}}>
          <p>AI is analyzing... This may take 1-2 minutes.</p>
          <p style={{color:"#9ca3af",fontSize:"0.75rem"}}>Running on local Qwen3 model (free, private)</p>
        </div>
      )}

      {analysis && (
        <div style={{background:"white",borderRadius:"8px",border:"1px solid #e5e7eb",padding:"1.5rem"}}>
          <div style={{display:"flex",justifyContent:"space-between",marginBottom:"1rem"}}>
            <h2 style={{fontSize:"1.125rem",fontWeight:600}}>Results</h2>
            <span style={{fontSize:"0.75rem",color:"#9ca3af"}}>
              {analysis.model_used} | {Math.round((analysis.latency_ms||0)/1000)}s | ${analysis.cost_usd}
            </span>
          </div>
          {analysis.success ? (
            <pre style={{whiteSpace:"pre-wrap",fontFamily:"inherit",fontSize:"0.875rem",lineHeight:"1.6",color:"#374151"}}>{analysis.raw_content}</pre>
          ) : (
            <div style={{color:"red",padding:"1rem",background:"#fef2f2",borderRadius:"6px"}}>Error: {analysis.error}</div>
          )}
        </div>
      )}
    </div>
  );
}
