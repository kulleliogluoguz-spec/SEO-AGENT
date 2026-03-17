"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell } from "recharts";

/* ═══════════════════════════════════════════════════════════════
   AI GROWTH OS — MARKETING EXECUTION DASHBOARD
   Dark refined aesthetic · Bloomberg-meets-SaaS · Data-dense
   ═══════════════════════════════════════════════════════════════ */

const CHANNELS = {
  instagram: { label: "Instagram", icon: "◉", color: "#E1306C", bg: "rgba(225,48,108,.12)" },
  tiktok:    { label: "TikTok",    icon: "♪", color: "#00f2ea", bg: "rgba(0,242,234,.10)" },
  twitter:   { label: "Twitter/X", icon: "𝕏", color: "#71B7FF", bg: "rgba(113,183,255,.10)" },
  linkedin:  { label: "LinkedIn",  icon: "in", color: "#0A66C2", bg: "rgba(10,102,194,.12)" },
  meta_ads:  { label: "Meta Ads",  icon: "▲", color: "#1877F2", bg: "rgba(24,119,242,.10)" },
};

const STATUS_COLORS = {
  draft: "#6B7280", pending_approval: "#F59E0B", approved: "#10B981",
  scheduled: "#6366F1", published: "#22C55E", failed: "#EF4444",
  rejected: "#EF4444", archived: "#4B5563",
};

const RISK = {
  low: { color: "#10B981", bg: "rgba(16,185,129,.12)", label: "Low Risk" },
  medium: { color: "#F59E0B", bg: "rgba(245,158,11,.12)", label: "Medium" },
  high: { color: "#EF4444", bg: "rgba(239,68,68,.12)", label: "High Risk" },
  critical: { color: "#DC2626", bg: "rgba(220,38,38,.15)", label: "Critical" },
};

// ── Demo Data ─────────────────────────────────────────────────

const demoCampaigns = [
  { id: "c1", name: "Q1 Growth Sprint", status: "active", objective: "Brand Awareness", channels: ["instagram","linkedin","twitter"], budget: 5000, content_count: 42, impressions: 187500, engagement_rate: 4.7, start_date: "2026-01-15", end_date: "2026-03-31" },
  { id: "c2", name: "Product Hunt Launch", status: "planning", objective: "Conversions", channels: ["twitter","linkedin","meta_ads"], budget: 12000, content_count: 0, impressions: 0, engagement_rate: 0, start_date: "2026-04-01", end_date: "2026-04-30" },
  { id: "c3", name: "Summer Content Series", status: "planning", objective: "Engagement", channels: ["instagram","tiktok","twitter"], budget: 3500, content_count: 0, impressions: 0, engagement_rate: 0, start_date: "2026-06-01", end_date: "2026-08-31" },
  { id: "c4", name: "SEO → Social Pipeline", status: "active", objective: "Traffic", channels: ["linkedin","twitter"], budget: 2000, content_count: 18, impressions: 65200, engagement_rate: 5.1 },
];

const demoApprovals = [
  { id: "a1", channel: "instagram", title: "5 AI Growth Hacks for SaaS Founders", body: "Most SaaS founders are sleeping on AI-powered growth.\n\nHere are 5 strategies that 10x'd our pipeline:\n\n→ AI content repurposing\n→ Smart scheduling\n→ Compliance-first automation\n→ SEO-to-social pipelines\n→ Engagement optimization\n\nWhich one are you trying first?", risk_score: 0.08, risk_level: "low", decision: "pending", compliance: { no_spam: true, no_deceptive: true, platform_ok: true, brand_safe: true, tone_ok: true } },
  { id: "a2", channel: "twitter", title: "AI Marketing Thread", body: "Thread: The future of marketing isn't about doing more.\n\nIt's about doing smarter.\n\nHere's what I learned building an AI growth system →", risk_score: 0.12, risk_level: "low", decision: "pending", compliance: { no_spam: true, no_deceptive: true, platform_ok: true, brand_safe: true, tone_ok: true } },
  { id: "a3", channel: "linkedin", title: "Marketing Execution Insight", body: "I've been thinking about the gap between strategy and execution in marketing.\n\nMost teams have a strategy doc. Few have an execution engine.\n\nThe difference? Strategy tells you what to do. An execution engine actually does it — safely, compliantly, at scale.", risk_score: 0.05, risk_level: "low", decision: "pending", compliance: { no_spam: true, no_deceptive: true, platform_ok: true, brand_safe: true, tone_ok: true } },
  { id: "a4", channel: "meta_ads", title: "Retargeting Ad — Growth OS", body: "Still managing your marketing manually?", risk_score: 0.35, risk_level: "medium", decision: "pending", compliance: { no_spam: true, no_deceptive: true, platform_ok: true, brand_safe: true, tone_ok: false }, headline: "Automate Your Growth — Responsibly", description: "AI-powered marketing execution with human oversight." },
];

const demoPerf = {
  total_impressions: 284600, total_clicks: 9840, total_engagement: 14200,
  total_conversions: 412, avg_engagement_rate: 4.7, avg_ctr: 3.5,
  total_spend: 3200, total_revenue: 11200, overall_roas: 3.5,
  by_channel: {
    instagram: { impressions: 95000, engagement_rate: 5.8, posts: 28, clicks: 3200, color: "#E1306C" },
    twitter:   { impressions: 72000, engagement_rate: 2.9, posts: 52, clicks: 2800, color: "#71B7FF" },
    linkedin:  { impressions: 58000, engagement_rate: 6.4, posts: 14, clicks: 2100, color: "#0A66C2" },
    tiktok:    { impressions: 42000, engagement_rate: 8.2, posts: 8, clicks: 1200, color: "#00f2ea" },
    meta_ads:  { impressions: 17600, engagement_rate: 1.8, posts: 4, clicks: 540, color: "#1877F2" },
  },
};

const demoChartData = Array.from({ length: 14 }, (_, i) => {
  const d = new Date(2026, 2, 3 + i);
  return {
    date: `${d.getMonth()+1}/${d.getDate()}`,
    impressions: 12000 + Math.floor(Math.random() * 15000),
    engagement: 400 + Math.floor(Math.random() * 800),
    clicks: 200 + Math.floor(Math.random() * 500),
  };
});

const demoCalendar = (() => {
  const days = [];
  const channels = ["instagram","twitter","linkedin","tiktok"];
  const themes = ["educational","social_proof","behind_scenes","thought_leadership","product","engagement"];
  const times = { instagram: "09:00", twitter: "08:00", linkedin: "10:00", tiktok: "19:00" };
  for (let i = 0; i < 28; i++) {
    const d = new Date(2026, 2, 17 + i);
    const dayItems = [];
    channels.forEach(ch => {
      if (Math.random() > 0.4) {
        dayItems.push({ channel: ch, time: times[ch], theme: themes[Math.floor(Math.random() * themes.length)], status: i < 3 ? "published" : i < 7 ? "scheduled" : "planned" });
      }
    });
    days.push({ date: d.toISOString().split("T")[0], dow: d.toLocaleDateString("en",{weekday:"short"}), items: dayItems });
  }
  return days;
})();

const demoConnectors = [
  { channel: "instagram", connected: true, account: "@growthbrand", level: 1 },
  { channel: "twitter", connected: true, account: "@growthbrand", level: 1 },
  { channel: "linkedin", connected: true, account: "Growth Brand Inc.", level: 1 },
  { channel: "tiktok", connected: false, account: null, level: 0 },
  { channel: "meta_ads", connected: false, account: null, level: 0 },
];

const demoScheduled = [
  { id: "s1", channel: "instagram", title: "AI Growth Hacks", time: "2026-03-18T09:00:00Z", status: "scheduled", risk: "low" },
  { id: "s2", channel: "twitter", title: "Thread: Marketing Execution", time: "2026-03-18T08:00:00Z", status: "scheduled", risk: "low" },
  { id: "s3", channel: "linkedin", title: "Strategy vs Execution", time: "2026-03-18T10:00:00Z", status: "scheduled", risk: "low" },
  { id: "s4", channel: "instagram", title: "Founder Story", time: "2026-03-19T12:00:00Z", status: "scheduled", risk: "low" },
  { id: "s5", channel: "twitter", title: "SEO Insights Drop", time: "2026-03-19T17:00:00Z", status: "scheduled", risk: "low" },
];

const demoAds = [
  { id: "ad1", name: "Retargeting — Website Visitors", status: "active", objective: "conversions", daily_budget: 50, impressions: 17600, clicks: 540, ctr: 3.07, conversions: 28, roas: 3.2, spend: 680 },
  { id: "ad2", name: "Lookalike — Growth Audience", status: "paused", objective: "traffic", daily_budget: 30, impressions: 8200, clicks: 310, ctr: 3.78, conversions: 12, roas: 2.1, spend: 420 },
];

// ── Styles ─────────────────────────────────────────────────────

const S = {
  root: { fontFamily: "'DM Sans', 'Satoshi', -apple-system, BlinkMacSystemFont, sans-serif", background: "#0C0E14", color: "#E2E4EA", minHeight: "100vh", fontSize: 13 },
  sidebar: { width: 220, background: "#12141C", borderRight: "1px solid #1E2130", display: "flex", flexDirection: "column", position: "fixed", top: 0, left: 0, bottom: 0, zIndex: 100 },
  main: { marginLeft: 220, padding: "24px 28px", minHeight: "100vh" },
  card: { background: "#14161F", border: "1px solid #1E2130", borderRadius: 10, padding: "18px 20px", marginBottom: 16 },
  cardHover: { background: "#181A25" },
  stat: { display: "flex", flexDirection: "column", gap: 2 },
  statLabel: { fontSize: 11, color: "#6B7280", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 500 },
  statValue: { fontSize: 22, fontWeight: 700, color: "#F0F1F5", letterSpacing: "-0.02em" },
  badge: (color, bg) => ({ display: "inline-flex", alignItems: "center", padding: "2px 10px", borderRadius: 20, fontSize: 11, fontWeight: 600, color, background: bg, border: `1px solid ${color}22` }),
  btn: (accent) => ({ padding: "7px 16px", borderRadius: 7, border: "none", background: accent || "#6366F1", color: "#fff", fontSize: 12, fontWeight: 600, cursor: "pointer", transition: "all .15s", letterSpacing: "0.01em" }),
  btnGhost: { padding: "7px 14px", borderRadius: 7, border: "1px solid #2A2D3E", background: "transparent", color: "#A1A5B5", fontSize: 12, fontWeight: 500, cursor: "pointer" },
  input: { padding: "8px 12px", borderRadius: 7, border: "1px solid #2A2D3E", background: "#0F1118", color: "#E2E4EA", fontSize: 13, outline: "none", width: "100%" },
  grid: (cols) => ({ display: "grid", gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 14 }),
  tag: (c) => ({ display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px", borderRadius: 6, fontSize: 11, fontWeight: 600, color: CHANNELS[c]?.color || "#999", background: CHANNELS[c]?.bg || "#1a1a2e" }),
};

// ── Components ──────────────────────────────────────────────────

function MetricCard({ label, value, sub, accent }) {
  return (
    <div style={S.card}>
      <div style={S.statLabel}>{label}</div>
      <div style={{ ...S.statValue, color: accent || "#F0F1F5" }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: "#6B7280", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function ChannelBadge({ ch }) {
  const c = CHANNELS[ch];
  if (!c) return <span style={S.tag(ch)}>{ch}</span>;
  return <span style={S.tag(ch)}>{c.icon} {c.label}</span>;
}

function RiskBadge({ level }) {
  const r = RISK[level] || RISK.low;
  return <span style={S.badge(r.color, r.bg)}>{r.label}</span>;
}

function StatusDot({ status }) {
  const c = STATUS_COLORS[status] || "#6B7280";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
      <span style={{ width: 7, height: 7, borderRadius: "50%", background: c, display: "inline-block" }} />
      <span style={{ fontSize: 11, color: c, fontWeight: 600, textTransform: "capitalize" }}>{status?.replace("_"," ")}</span>
    </span>
  );
}

function SectionTitle({ children, sub }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <h2 style={{ fontSize: 19, fontWeight: 700, color: "#F0F1F5", margin: 0, letterSpacing: "-0.02em" }}>{children}</h2>
      {sub && <p style={{ fontSize: 12, color: "#6B7280", margin: "4px 0 0" }}>{sub}</p>}
    </div>
  );
}

function ComplianceChecks({ checks }) {
  const labels = { no_spam: "No Spam", no_deceptive: "No Deception", platform_ok: "Platform OK", brand_safe: "Brand Safe", tone_ok: "Tone" };
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {Object.entries(checks).map(([k, v]) => (
        <span key={k} style={S.badge(v ? "#10B981" : "#EF4444", v ? "rgba(16,185,129,.1)" : "rgba(239,68,68,.1)")}>
          {v ? "✓" : "✗"} {labels[k] || k}
        </span>
      ))}
    </div>
  );
}

function Tabs({ tabs, active, onChange }) {
  return (
    <div style={{ display: "flex", gap: 2, background: "#12141C", borderRadius: 8, padding: 3, marginBottom: 18, border: "1px solid #1E2130" }}>
      {tabs.map(t => (
        <button key={t.key} onClick={() => onChange(t.key)}
          style={{ padding: "7px 16px", borderRadius: 6, border: "none", background: active === t.key ? "#6366F1" : "transparent", color: active === t.key ? "#fff" : "#6B7280", fontSize: 12, fontWeight: 600, cursor: "pointer", transition: "all .15s" }}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

const chartTheme = { style: { fontSize: 10, fill: "#6B7280" } };

// ═══════════════════════════════════════════════════════════════
//  NAV ITEMS
// ═══════════════════════════════════════════════════════════════

const NAV = [
  { key: "overview",    icon: "◈", label: "Dashboard" },
  { key: "campaigns",   icon: "⚑", label: "Campaigns" },
  { key: "generate",    icon: "✦", label: "Generate" },
  { key: "calendar",    icon: "▦", label: "Calendar" },
  { key: "approvals",   icon: "◎", label: "Approvals" },
  { key: "scheduled",   icon: "◷", label: "Scheduled" },
  { key: "performance", icon: "◆", label: "Performance" },
  { key: "ads",         icon: "▲", label: "Ads" },
  { key: "connectors",  icon: "⚡", label: "Connectors" },
];

// ═══════════════════════════════════════════════════════════════
//  MAIN APP
// ═══════════════════════════════════════════════════════════════

export default function MarketingDashboard() {
  const [page, setPage] = useState("overview");
  const [genTopic, setGenTopic] = useState("");
  const [genChannels, setGenChannels] = useState(["instagram","twitter","linkedin"]);
  const [genTone, setGenTone] = useState("professional");
  const [genResults, setGenResults] = useState(null);
  const [genLoading, setGenLoading] = useState(false);
  const [approvalItems, setApprovalItems] = useState(demoApprovals);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleGenerate = () => {
    if (!genTopic.trim()) return;
    setGenLoading(true);
    setTimeout(() => {
      const results = genChannels.map(ch => {
        const hooks = {
          instagram: `Here's what nobody tells you about ${genTopic}...`,
          twitter: `${genTopic} is broken. Here's what's actually working →`,
          linkedin: `I spent 6 months studying ${genTopic}. Here's what I found.`,
          tiktok: `POV: You just discovered the truth about ${genTopic}`,
          meta_ads: `Still struggling with ${genTopic}?`,
        };
        const bodies = {
          instagram: `${hooks[ch]}\n\nMost people get this wrong. Here's the framework:\n\n→ Start with data, not assumptions\n→ Test in 2-week sprints\n→ Let AI handle distribution\n→ Focus on quality over volume\n→ Measure what matters\n\nSave this for later ↓\n\n#${genTopic.replace(/\s/g,'')} #growth #marketing #ai #strategy`,
          twitter: `${hooks[ch]}\n\nThread 🧵`,
          linkedin: `${hooks[ch]}\n\nAnd the results were surprising.\n\nHere's what actually moves the needle:\n\n1. Quality over quantity — always\n2. Distribution > creation\n3. AI-assisted, human-approved\n4. Compound content strategies\n5. Measure outcomes, not vanity metrics\n\nThe companies winning at ${genTopic} aren't working harder.\nThey're working smarter.\n\nWhat's your experience with ${genTopic}?\n\n#${genTopic.replace(/\s/g,'')} #growth`,
          tiktok: `HOOK (0-3s): ${hooks[ch]}\n\nBODY (3-20s): Here's the thing about ${genTopic} — everyone's overcomplicating it. The real framework is simple: data first, test fast, scale what works.\n\nCTA (20-25s): Follow for more growth insights.`,
          meta_ads: `${hooks[ch]}\n\nHeadline: Master ${genTopic} — The Smart Way\nDescription: AI-powered ${genTopic} strategies that actually work.\nCTA: Learn More`,
        };
        return {
          channel: ch, body: bodies[ch] || `Post about ${genTopic}`, hook: hooks[ch],
          risk_level: "low", risk_score: Math.random() * 0.2,
          compliance: { passed: true, warnings: [] },
          hashtags: ch === "instagram" ? [`#${genTopic.replace(/\s/g,'')}`, "#growth", "#marketing", "#ai"] : [],
        };
      });
      setGenResults(results);
      setGenLoading(false);
    }, 1500);
  };

  const handleApprove = (id) => {
    setApprovalItems(prev => prev.map(a => a.id === id ? { ...a, decision: "approved" } : a));
    showToast("Content approved and queued for scheduling");
  };
  const handleReject = (id) => {
    setApprovalItems(prev => prev.map(a => a.id === id ? { ...a, decision: "rejected" } : a));
    showToast("Content rejected", "error");
  };

  const toggleChannel = (ch) => {
    setGenChannels(prev => prev.includes(ch) ? prev.filter(c => c !== ch) : [...prev, ch]);
  };

  // ── Render ──

  return (
    <div style={S.root}>
      {/* Toast */}
      {toast && (
        <div style={{ position: "fixed", top: 20, right: 20, zIndex: 9999, padding: "10px 20px", borderRadius: 8, background: toast.type === "error" ? "#DC2626" : "#10B981", color: "#fff", fontSize: 13, fontWeight: 600, boxShadow: "0 8px 30px rgba(0,0,0,.4)", animation: "fadeIn .2s" }}>
          {toast.msg}
        </div>
      )}

      {/* Sidebar */}
      <div style={S.sidebar}>
        <div style={{ padding: "20px 18px 16px", borderBottom: "1px solid #1E2130" }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: "#F0F1F5", letterSpacing: "-0.03em" }}>
            <span style={{ color: "#6366F1" }}>◈</span> AI Growth OS
          </div>
          <div style={{ fontSize: 10, color: "#4B5563", marginTop: 3, textTransform: "uppercase", letterSpacing: "0.08em" }}>Marketing Execution</div>
        </div>
        <div style={{ padding: "10px 8px", flex: 1, overflowY: "auto" }}>
          {NAV.map(n => (
            <button key={n.key} onClick={() => setPage(n.key)}
              style={{ display: "flex", alignItems: "center", gap: 10, width: "100%", padding: "9px 12px", borderRadius: 7, border: "none", background: page === n.key ? "rgba(99,102,241,.12)" : "transparent", color: page === n.key ? "#818CF8" : "#6B7280", fontSize: 13, fontWeight: page === n.key ? 600 : 500, cursor: "pointer", textAlign: "left", marginBottom: 2, transition: "all .12s" }}>
              <span style={{ fontSize: 14, width: 18 }}>{n.icon}</span> {n.label}
            </button>
          ))}
        </div>
        <div style={{ padding: "14px 16px", borderTop: "1px solid #1E2130", fontSize: 10, color: "#4B5563" }}>
          <div>Autonomy: <span style={{ color: "#F59E0B" }}>Level 1 — Draft Only</span></div>
          <div style={{ marginTop: 3 }}>All content requires approval</div>
        </div>
      </div>

      {/* Main */}
      <div style={S.main}>

        {/* ═══════ OVERVIEW ═══════ */}
        {page === "overview" && (
          <div>
            <SectionTitle sub="Real-time marketing intelligence across all channels">Marketing Command Center</SectionTitle>

            <div style={S.grid(5)}>
              <MetricCard label="Total Impressions" value="284.6K" sub="↑ 18% vs last period" accent="#6366F1" />
              <MetricCard label="Engagement Rate" value="4.7%" sub="Industry avg: 2.8%" accent="#10B981" />
              <MetricCard label="Total Clicks" value="9,840" sub="CTR 3.5%" accent="#71B7FF" />
              <MetricCard label="Conversions" value="412" sub="CPA $7.77" accent="#F59E0B" />
              <MetricCard label="ROAS" value="3.5x" sub="$11.2K revenue" accent="#22C55E" />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16, marginTop: 4 }}>
              <div style={S.card}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#A1A5B5", marginBottom: 12 }}>Engagement Trend — 14 Days</div>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={demoChartData}>
                    <defs>
                      <linearGradient id="gEng" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#6366F1" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#6366F1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="date" tick={chartTheme} axisLine={false} tickLine={false} />
                    <YAxis tick={chartTheme} axisLine={false} tickLine={false} width={40} />
                    <Tooltip contentStyle={{ background: "#1A1D2B", border: "1px solid #2A2D3E", borderRadius: 8, fontSize: 12, color: "#E2E4EA" }} />
                    <Area type="monotone" dataKey="engagement" stroke="#6366F1" fill="url(#gEng)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div style={S.card}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#A1A5B5", marginBottom: 12 }}>Channel Mix</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {Object.entries(demoPerf.by_channel).map(([ch, d]) => (
                    <div key={ch}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                        <ChannelBadge ch={ch} />
                        <span style={{ fontSize: 12, color: "#A1A5B5", fontWeight: 600 }}>{(d.impressions/1000).toFixed(0)}K</span>
                      </div>
                      <div style={{ height: 5, background: "#1E2130", borderRadius: 3, overflow: "hidden" }}>
                        <div style={{ height: "100%", width: `${(d.impressions / 95000) * 100}%`, background: d.color, borderRadius: 3, transition: "width .5s" }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 4 }}>
              <div style={S.card}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#A1A5B5" }}>Pending Approvals</div>
                  <span style={S.badge("#F59E0B", "rgba(245,158,11,.1)")}>{approvalItems.filter(a=>a.decision==="pending").length} pending</span>
                </div>
                {approvalItems.filter(a=>a.decision==="pending").slice(0,3).map(a => (
                  <div key={a.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #1E2130" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <ChannelBadge ch={a.channel} />
                      <span style={{ fontSize: 12, color: "#E2E4EA" }}>{a.title}</span>
                    </div>
                    <RiskBadge level={a.risk_level} />
                  </div>
                ))}
                <button onClick={() => setPage("approvals")} style={{ ...S.btnGhost, marginTop: 10, width: "100%", textAlign: "center" }}>
                  View All Approvals →
                </button>
              </div>

              <div style={S.card}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#A1A5B5", marginBottom: 12 }}>Upcoming Scheduled</div>
                {demoScheduled.slice(0,4).map(s => (
                  <div key={s.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #1E2130" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <ChannelBadge ch={s.channel} />
                      <div>
                        <div style={{ fontSize: 12, color: "#E2E4EA" }}>{s.title}</div>
                        <div style={{ fontSize: 10, color: "#6B7280" }}>{new Date(s.time).toLocaleString("en", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</div>
                      </div>
                    </div>
                    <StatusDot status="scheduled" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ═══════ CAMPAIGNS ═══════ */}
        {page === "campaigns" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
              <SectionTitle sub="Plan, manage, and track multi-channel campaigns">Campaign Manager</SectionTitle>
              <button style={S.btn()}>+ New Campaign</button>
            </div>
            {demoCampaigns.map(c => (
              <div key={c.id} style={{ ...S.card, display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", alignItems: "center", gap: 16 }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: "#F0F1F5" }}>{c.name}</div>
                  <div style={{ fontSize: 11, color: "#6B7280", marginTop: 3 }}>{c.objective} · ${c.budget.toLocaleString()} budget</div>
                  <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
                    {c.channels.map(ch => <ChannelBadge key={ch} ch={ch} />)}
                  </div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <StatusDot status={c.status} />
                  <div style={{ fontSize: 11, color: "#6B7280", marginTop: 4 }}>{c.content_count} posts</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#F0F1F5" }}>{c.impressions > 0 ? `${(c.impressions/1000).toFixed(1)}K` : "—"}</div>
                  <div style={{ fontSize: 11, color: "#6B7280" }}>impressions</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: c.engagement_rate > 4 ? "#10B981" : "#F0F1F5" }}>{c.engagement_rate > 0 ? `${c.engagement_rate}%` : "—"}</div>
                  <div style={{ fontSize: 11, color: "#6B7280" }}>engagement</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ═══════ GENERATE ═══════ */}
        {page === "generate" && (
          <div>
            <SectionTitle sub="AI-powered content generation with compliance checking">Content Generation</SectionTitle>

            <div style={{ ...S.card, marginBottom: 20 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <div>
                  <label style={{ ...S.statLabel, marginBottom: 6, display: "block" }}>Topic / Brief</label>
                  <textarea value={genTopic} onChange={e => setGenTopic(e.target.value)}
                    placeholder="e.g. AI-powered marketing automation for SaaS companies..."
                    style={{ ...S.input, height: 80, resize: "vertical", fontFamily: "inherit" }} />
                </div>
                <div>
                  <label style={{ ...S.statLabel, marginBottom: 6, display: "block" }}>Tone</label>
                  <select value={genTone} onChange={e => setGenTone(e.target.value)} style={{ ...S.input, marginBottom: 12 }}>
                    <option value="professional">Professional</option>
                    <option value="casual">Casual</option>
                    <option value="bold">Bold / Provocative</option>
                    <option value="educational">Educational</option>
                    <option value="storytelling">Storytelling</option>
                  </select>
                  <label style={{ ...S.statLabel, marginBottom: 6, display: "block" }}>Target Channels</label>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {Object.entries(CHANNELS).map(([k, v]) => (
                      <button key={k} onClick={() => toggleChannel(k)}
                        style={{ ...S.tag(k), cursor: "pointer", opacity: genChannels.includes(k) ? 1 : 0.35, border: genChannels.includes(k) ? `1px solid ${v.color}44` : "1px solid transparent", transition: "all .15s" }}>
                        {v.icon} {v.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div style={{ marginTop: 16, display: "flex", gap: 10 }}>
                <button onClick={handleGenerate} disabled={genLoading || !genTopic.trim()} style={{ ...S.btn(), opacity: genLoading || !genTopic.trim() ? 0.5 : 1 }}>
                  {genLoading ? "◌ Generating..." : "✦ Generate Content"}
                </button>
                <button style={S.btnGhost}>Repurpose from URL</button>
              </div>
            </div>

            {genResults && (
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#A1A5B5", marginBottom: 12 }}>Generated {genResults.length} Posts — All in Draft Mode</div>
                {genResults.map((r, i) => (
                  <div key={i} style={{ ...S.card, borderLeft: `3px solid ${CHANNELS[r.channel]?.color || "#6366F1"}` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <ChannelBadge ch={r.channel} />
                        <StatusDot status="draft" />
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <RiskBadge level={r.risk_level} />
                        <span style={{ fontSize: 11, color: "#6B7280" }}>Score: {r.risk_score.toFixed(2)}</span>
                      </div>
                    </div>
                    <pre style={{ whiteSpace: "pre-wrap", fontFamily: "'DM Sans', sans-serif", fontSize: 13, color: "#D1D5DB", lineHeight: 1.6, margin: 0, background: "#0F1118", padding: 14, borderRadius: 8, border: "1px solid #1E2130" }}>
                      {r.body}
                    </pre>
                    <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                      <button style={S.btn("#10B981")} onClick={() => showToast("Sent to approval queue")}>Send to Approval →</button>
                      <button style={S.btnGhost}>Edit</button>
                      <button style={S.btnGhost}>Regenerate</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ═══════ CALENDAR ═══════ */}
        {page === "calendar" && (
          <div>
            <SectionTitle sub="Visual content calendar across all channels">Content Calendar</SectionTitle>
            <div style={{ overflowX: "auto" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 6, minWidth: 800 }}>
                {["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map(d => (
                  <div key={d} style={{ padding: "6px 0", textAlign: "center", fontSize: 11, fontWeight: 600, color: "#6B7280", textTransform: "uppercase" }}>{d}</div>
                ))}
                {demoCalendar.slice(0, 28).map((day, i) => (
                  <div key={i} style={{ ...S.card, padding: "8px 10px", minHeight: 90, marginBottom: 0 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#A1A5B5", marginBottom: 6 }}>
                      {new Date(day.date).getDate()}
                    </div>
                    {day.items.map((item, j) => (
                      <div key={j} style={{ ...S.tag(item.channel), marginBottom: 3, fontSize: 9, padding: "1px 5px" }}>
                        {CHANNELS[item.channel]?.icon} {item.time}
                      </div>
                    ))}
                    {day.items.length === 0 && <div style={{ fontSize: 10, color: "#3B3F52" }}>—</div>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ═══════ APPROVALS ═══════ */}
        {page === "approvals" && (
          <div>
            <SectionTitle sub="Review, approve, or reject content before it goes live">Approval Queue</SectionTitle>
            <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
              <span style={S.badge("#F59E0B", "rgba(245,158,11,.1)")}>{approvalItems.filter(a=>a.decision==="pending").length} Pending</span>
              <span style={S.badge("#10B981", "rgba(16,185,129,.1)")}>{approvalItems.filter(a=>a.decision==="approved").length} Approved</span>
              <span style={S.badge("#EF4444", "rgba(239,68,68,.1)")}>{approvalItems.filter(a=>a.decision==="rejected").length} Rejected</span>
            </div>
            {approvalItems.map(a => (
              <div key={a.id} style={{ ...S.card, borderLeft: `3px solid ${a.decision === "pending" ? "#F59E0B" : a.decision === "approved" ? "#10B981" : "#EF4444"}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <ChannelBadge ch={a.channel} />
                    <span style={{ fontSize: 14, fontWeight: 600, color: "#F0F1F5" }}>{a.title}</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <RiskBadge level={a.risk_level} />
                    <span style={{ fontSize: 11, color: "#6B7280" }}>Risk: {(a.risk_score * 100).toFixed(0)}%</span>
                  </div>
                </div>

                <pre style={{ whiteSpace: "pre-wrap", fontFamily: "'DM Sans', sans-serif", fontSize: 13, color: "#D1D5DB", lineHeight: 1.6, margin: "0 0 12px", background: "#0F1118", padding: 14, borderRadius: 8, border: "1px solid #1E2130" }}>
                  {a.body}
                </pre>

                {a.headline && (
                  <div style={{ marginBottom: 10, padding: "8px 12px", background: "#0F1118", borderRadius: 6, border: "1px solid #1E2130" }}>
                    <div style={{ fontSize: 11, color: "#6B7280", marginBottom: 4 }}>AD PREVIEW</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "#F0F1F5" }}>{a.headline}</div>
                    <div style={{ fontSize: 12, color: "#A1A5B5" }}>{a.description}</div>
                  </div>
                )}

                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: "#6B7280", marginBottom: 6, textTransform: "uppercase" }}>Compliance Checks</div>
                  <ComplianceChecks checks={a.compliance} />
                </div>

                {a.decision === "pending" ? (
                  <div style={{ display: "flex", gap: 8 }}>
                    <button style={S.btn("#10B981")} onClick={() => handleApprove(a.id)}>✓ Approve</button>
                    <button style={S.btn("#EF4444")} onClick={() => handleReject(a.id)}>✗ Reject</button>
                    <button style={S.btnGhost}>Request Revision</button>
                  </div>
                ) : (
                  <StatusDot status={a.decision} />
                )}
              </div>
            ))}
          </div>
        )}

        {/* ═══════ SCHEDULED ═══════ */}
        {page === "scheduled" && (
          <div>
            <SectionTitle sub="Content approved and queued for publishing">Scheduled Posts</SectionTitle>
            {demoScheduled.map(s => (
              <div key={s.id} style={{ ...S.card, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <div style={{ width: 40, height: 40, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", background: CHANNELS[s.channel]?.bg, color: CHANNELS[s.channel]?.color, fontSize: 18, fontWeight: 700 }}>
                    {CHANNELS[s.channel]?.icon}
                  </div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "#F0F1F5" }}>{s.title}</div>
                    <div style={{ fontSize: 11, color: "#6B7280" }}>
                      {new Date(s.time).toLocaleString("en", { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })} UTC
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <RiskBadge level={s.risk} />
                  <StatusDot status={s.status} />
                  <button style={S.btnGhost}>Reschedule</button>
                  <button style={{ ...S.btnGhost, color: "#EF4444", borderColor: "#EF444433" }}>Cancel</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ═══════ PERFORMANCE ═══════ */}
        {page === "performance" && (
          <div>
            <SectionTitle sub="Cross-channel performance analytics and AI insights">Performance Analytics</SectionTitle>

            <div style={S.grid(5)}>
              <MetricCard label="Impressions" value="284.6K" accent="#6366F1" />
              <MetricCard label="Engagement" value="14.2K" accent="#10B981" />
              <MetricCard label="Click Rate" value="3.5%" accent="#71B7FF" />
              <MetricCard label="Conversions" value="412" accent="#F59E0B" />
              <MetricCard label="ROAS" value="3.5x" accent="#22C55E" />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 4 }}>
              <div style={S.card}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#A1A5B5", marginBottom: 12 }}>Impressions Over Time</div>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={demoChartData}>
                    <XAxis dataKey="date" tick={chartTheme} axisLine={false} tickLine={false} />
                    <YAxis tick={chartTheme} axisLine={false} tickLine={false} width={45} />
                    <Tooltip contentStyle={{ background: "#1A1D2B", border: "1px solid #2A2D3E", borderRadius: 8, fontSize: 12, color: "#E2E4EA" }} />
                    <Bar dataKey="impressions" fill="#6366F1" radius={[3,3,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div style={S.card}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#A1A5B5", marginBottom: 12 }}>Clicks Over Time</div>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={demoChartData}>
                    <XAxis dataKey="date" tick={chartTheme} axisLine={false} tickLine={false} />
                    <YAxis tick={chartTheme} axisLine={false} tickLine={false} width={40} />
                    <Tooltip contentStyle={{ background: "#1A1D2B", border: "1px solid #2A2D3E", borderRadius: 8, fontSize: 12, color: "#E2E4EA" }} />
                    <Line type="monotone" dataKey="clicks" stroke="#71B7FF" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div style={S.card}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#A1A5B5", marginBottom: 14 }}>Channel Breakdown</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
                {Object.entries(demoPerf.by_channel).map(([ch, d]) => (
                  <div key={ch} style={{ background: "#0F1118", padding: 14, borderRadius: 8, border: "1px solid #1E2130", textAlign: "center" }}>
                    <div style={{ fontSize: 20, marginBottom: 6 }}>{CHANNELS[ch]?.icon}</div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: CHANNELS[ch]?.color }}>{CHANNELS[ch]?.label}</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: "#F0F1F5", margin: "6px 0" }}>{(d.impressions/1000).toFixed(0)}K</div>
                    <div style={{ fontSize: 11, color: "#6B7280" }}>{d.posts} posts · {d.engagement_rate}% ER</div>
                  </div>
                ))}
              </div>
            </div>

            <div style={S.card}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#A1A5B5", marginBottom: 10 }}>🤖 AI Performance Insights</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[
                  "LinkedIn posts with discussion questions get 2.3x more comments. Keep using them.",
                  "Instagram carousel content outperforms single-image by 3.1x. Increase carousel frequency.",
                  "Tuesday and Thursday mornings (8-10 AM) are your highest engagement windows.",
                  "Twitter threads > single tweets — 4.5x more impressions on average.",
                  "Consider increasing TikTok frequency — your 8.2% ER there is exceptional.",
                ].map((insight, i) => (
                  <div key={i} style={{ padding: "10px 14px", background: "#0F1118", borderRadius: 7, border: "1px solid #1E2130", fontSize: 12, color: "#D1D5DB", display: "flex", alignItems: "flex-start", gap: 8 }}>
                    <span style={{ color: "#6366F1", fontWeight: 800 }}>→</span> {insight}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ═══════ ADS ═══════ */}
        {page === "ads" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
              <SectionTitle sub="Manage Meta Ads campaigns with AI-generated copy">Ad Campaigns</SectionTitle>
              <button style={S.btn()}>+ Create Ad Campaign</button>
            </div>
            {demoAds.map(ad => (
              <div key={ad.id} style={S.card}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 700, color: "#F0F1F5" }}>{ad.name}</div>
                    <div style={{ fontSize: 11, color: "#6B7280", marginTop: 2 }}>Objective: {ad.objective} · Budget: ${ad.daily_budget}/day</div>
                  </div>
                  <StatusDot status={ad.status} />
                </div>
                <div style={S.grid(6)}>
                  <div style={S.stat}><span style={S.statLabel}>Impressions</span><span style={{ ...S.statValue, fontSize: 16 }}>{(ad.impressions/1000).toFixed(1)}K</span></div>
                  <div style={S.stat}><span style={S.statLabel}>Clicks</span><span style={{ ...S.statValue, fontSize: 16 }}>{ad.clicks}</span></div>
                  <div style={S.stat}><span style={S.statLabel}>CTR</span><span style={{ ...S.statValue, fontSize: 16 }}>{ad.ctr}%</span></div>
                  <div style={S.stat}><span style={S.statLabel}>Conversions</span><span style={{ ...S.statValue, fontSize: 16 }}>{ad.conversions}</span></div>
                  <div style={S.stat}><span style={S.statLabel}>Spend</span><span style={{ ...S.statValue, fontSize: 16 }}>${ad.spend}</span></div>
                  <div style={S.stat}><span style={S.statLabel}>ROAS</span><span style={{ ...S.statValue, fontSize: 16, color: ad.roas > 2.5 ? "#10B981" : "#F59E0B" }}>{ad.roas}x</span></div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ═══════ CONNECTORS ═══════ */}
        {page === "connectors" && (
          <div>
            <SectionTitle sub="Connect your social accounts. Manage automation levels.">Channel Connectors</SectionTitle>
            <div style={{ marginBottom: 16, padding: "12px 16px", background: "rgba(99,102,241,.08)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 8, fontSize: 12, color: "#A1A5B5" }}>
              <strong style={{ color: "#818CF8" }}>Safety Note:</strong> All connectors default to <strong>Level 1 — Draft Only</strong>. Content is never published without human approval.
            </div>
            <div style={S.grid(3)}>
              {demoConnectors.map(c => (
                <div key={c.channel} style={{ ...S.card, borderTop: `3px solid ${CHANNELS[c.channel]?.color}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ fontSize: 22, color: CHANNELS[c.channel]?.color }}>{CHANNELS[c.channel]?.icon}</span>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 700, color: "#F0F1F5" }}>{CHANNELS[c.channel]?.label}</div>
                        {c.account && <div style={{ fontSize: 11, color: "#6B7280" }}>{c.account}</div>}
                      </div>
                    </div>
                    <span style={S.badge(c.connected ? "#10B981" : "#6B7280", c.connected ? "rgba(16,185,129,.1)" : "rgba(107,114,128,.1)")}>
                      {c.connected ? "Connected" : "Not Connected"}
                    </span>
                  </div>

                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: 11, color: "#6B7280", marginBottom: 4 }}>Automation Level</div>
                    <div style={{ display: "flex", gap: 4 }}>
                      {[0,1,2,3].map(l => (
                        <div key={l} style={{ flex: 1, height: 5, borderRadius: 3, background: l <= c.level ? (l <= 1 ? "#10B981" : l === 2 ? "#F59E0B" : "#EF4444") : "#1E2130" }} />
                      ))}
                    </div>
                    <div style={{ fontSize: 10, color: "#6B7280", marginTop: 3 }}>
                      {["Analysis only","Draft only (default)","Approval-required","Low-risk auto"][c.level]}
                    </div>
                  </div>

                  {c.connected ? (
                    <button style={{ ...S.btnGhost, width: "100%", textAlign: "center" }}>Manage</button>
                  ) : (
                    <button style={{ ...S.btn(CHANNELS[c.channel]?.color), width: "100%", textAlign: "center" }}>Connect {CHANNELS[c.channel]?.label}</button>
                  )}
                </div>
              ))}
            </div>

            <div style={{ ...S.card, marginTop: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#A1A5B5", marginBottom: 10 }}>Autonomy Level Guide</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
                {[
                  { level: 0, name: "Analysis Only", desc: "Read-only intelligence. No content generated.", color: "#6B7280" },
                  { level: 1, name: "Draft Only", desc: "All output goes to human review queue. Default.", color: "#10B981" },
                  { level: 2, name: "Approval Required", desc: "Queued actions need explicit approval.", color: "#F59E0B" },
                  { level: 3, name: "Low-Risk Auto", desc: "Only low-risk, compliant content auto-runs. Strict limits.", color: "#EF4444" },
                ].map(l => (
                  <div key={l.level} style={{ padding: 12, background: "#0F1118", borderRadius: 8, border: "1px solid #1E2130" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                      <span style={{ width: 18, height: 18, borderRadius: 4, background: l.color + "22", color: l.color, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 800 }}>{l.level}</span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: "#F0F1F5" }}>{l.name}</span>
                    </div>
                    <div style={{ fontSize: 11, color: "#6B7280" }}>{l.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0C0E14; }
        ::-webkit-scrollbar-thumb { background: #2A2D3E; border-radius: 3px; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
        button:hover { filter: brightness(1.15); }
        textarea:focus, select:focus, input:focus { border-color: #6366F1 !important; }
      `}</style>
    </div>
  );
}
