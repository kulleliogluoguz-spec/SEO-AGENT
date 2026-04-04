'use client';

import { useState, useEffect, useCallback } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

// ─── Reusable Components ────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    healthy: 'bg-emerald-100 text-emerald-800',
    unhealthy: 'bg-red-100 text-red-800',
    unconfigured: 'bg-yellow-100 text-yellow-800',
    operational: 'bg-emerald-100 text-emerald-800',
    error: 'bg-red-100 text-red-800',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-800'}`}>
      {status}
    </span>
  );
}

function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-semibold text-gray-900">{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  );
}

function SectionHeader({ title, description }: { title: string; description?: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      {description && <p className="text-sm text-gray-500 mt-0.5">{description}</p>}
    </div>
  );
}

// ─── Tab Navigation ─────────────────────────────────────────────

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'models', label: 'Models' },
  { id: 'providers', label: 'Providers' },
  { id: 'routing', label: 'Routing' },
  { id: 'prompts', label: 'Prompts' },
  { id: 'engines', label: 'Engines' },
  { id: 'traces', label: 'Traces' },
  { id: 'evals', label: 'Evals' },
  { id: 'training', label: 'Training' },
  { id: 'playground', label: 'Playground' },
];

// ─── Main Page ──────────────────────────────────────────────────

export default function AIAdminPage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [data, setData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const endpoints: Record<string, string> = {
        status: '/api/v1/ai/status',
        models: '/api/v1/ai/models',
        providers: '/api/v1/ai/providers/health',
        routing: '/api/v1/ai/router/policy',
        prompts: '/api/v1/ai/prompts',
        engines: '/api/v1/ai/engines',
        traces: '/api/v1/ai/traces?limit=30',
        metrics: '/api/v1/ai/metrics',
        evals: '/api/v1/ai/evals/suites',
        evalRuns: '/api/v1/ai/evals/runs',
        training: '/api/v1/ai/training/stats',
        guardrails: '/api/v1/ai/guardrails/stats',
        cost: '/api/v1/ai/metrics/cost',
        roles: '/api/v1/ai/models/roles',
      };

      const results: Record<string, any> = {};
      const promises = Object.entries(endpoints).map(async ([key, url]) => {
        try {
          const res = await fetch(`${API_BASE}${url}`);
          if (res.ok) results[key] = await res.json();
        } catch (e) {
          // Individual endpoint failures are ok
        }
      });
      await Promise.all(promises);
      setData(results);
    } catch (e: any) {
      setError(e.message || 'Failed to load AI system data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">AI Control Center</h1>
            <p className="text-sm text-gray-500">Custom AI Subsystem Management</p>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={data.status?.status || 'loading'} />
            <button
              onClick={fetchData}
              className="px-3 py-1.5 text-sm bg-gray-900 text-white rounded-md hover:bg-gray-800"
            >
              Refresh
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mt-4 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 text-sm rounded-md whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
            {error}
          </div>
        )}

        {loading && !Object.keys(data).length ? (
          <div className="text-center py-12 text-gray-500">Loading AI system data...</div>
        ) : (
          <>
            {activeTab === 'overview' && <OverviewTab data={data} />}
            {activeTab === 'models' && <ModelsTab data={data} onRefresh={fetchData} />}
            {activeTab === 'providers' && <ProvidersTab data={data} />}
            {activeTab === 'routing' && <RoutingTab data={data} />}
            {activeTab === 'prompts' && <PromptsTab data={data} />}
            {activeTab === 'engines' && <EnginesTab data={data} />}
            {activeTab === 'traces' && <TracesTab data={data} />}
            {activeTab === 'evals' && <EvalsTab data={data} />}
            {activeTab === 'training' && <TrainingTab data={data} />}
            {activeTab === 'playground' && <PlaygroundTab />}
          </>
        )}
      </div>
    </div>
  );
}

// ─── Overview Tab ───────────────────────────────────────────────

function OverviewTab({ data }: { data: any }) {
  const status = data.status || {};
  const metrics = data.metrics || {};
  const cost = data.cost || {};

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Total AI Calls" value={metrics.total_calls || 0} />
        <MetricCard label="Error Rate" value={`${((metrics.error_rate || 0) * 100).toFixed(1)}%`} />
        <MetricCard label="Total Cost" value={`$${(cost.total_cost_usd || 0).toFixed(4)}`} />
        <MetricCard
          label="Models Active"
          value={`${status.models?.enabled || 0} / ${status.models?.total || 0}`}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MetricCard label="Self-Hosted Calls" value={cost.self_hosted_calls || 0} sub="Free (local/vLLM)" />
        <MetricCard label="API Calls" value={cost.api_calls || 0} sub="Paid (Anthropic fallback)" />
      </div>

      {/* Provider Status */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <SectionHeader title="Provider Status" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {Object.entries(data.providers?.providers || {}).map(([name, info]: [string, any]) => (
            <div key={name} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
              <span className="font-medium text-sm">{name}</span>
              <StatusBadge status={info.status} />
            </div>
          ))}
        </div>
      </div>

      {/* Engine Stats */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <SectionHeader title="Engine Activity" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {(data.engines?.engines || []).filter((e: any) => e.calls > 0).map((engine: any) => (
            <div key={engine.engine} className="text-center p-2 bg-gray-50 rounded">
              <div className="text-xs text-gray-500">{engine.engine}</div>
              <div className="text-lg font-semibold">{engine.calls}</div>
              <div className="text-xs text-gray-400">{engine.errors} errors</div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Errors */}
      {metrics.recent_errors?.length > 0 && (
        <div className="bg-white rounded-lg border border-red-200 p-4">
          <SectionHeader title="Recent Errors" />
          <div className="space-y-2">
            {metrics.recent_errors.slice(0, 5).map((trace: any, i: number) => (
              <div key={i} className="text-sm p-2 bg-red-50 rounded">
                <span className="font-medium">{trace.engine}</span>
                <span className="text-gray-500"> → {trace.model_used}</span>
                <span className="text-red-600 ml-2">{trace.error}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Models Tab ─────────────────────────────────────────────────

function ModelsTab({ data, onRefresh }: { data: any; onRefresh: () => void }) {
  const models = data.models?.models || [];

  const toggleModel = async (modelId: string, enabled: boolean) => {
    await fetch(`${API_BASE}/api/v1/ai/models/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_id: modelId, enabled }),
    });
    onRefresh();
  };

  return (
    <div className="space-y-4">
      <SectionHeader title="Model Registry" description="All registered AI models and their configuration" />
      <div className="space-y-3">
        {models.map((model: any) => (
          <div key={model.id} className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-900">{model.name}</span>
                  {model.is_fallback && (
                    <span className="px-1.5 py-0.5 bg-orange-100 text-orange-700 text-xs rounded">fallback</span>
                  )}
                  {model.shadow_mode && (
                    <span className="px-1.5 py-0.5 bg-purple-100 text-purple-700 text-xs rounded">shadow</span>
                  )}
                </div>
                <div className="text-sm text-gray-500 mt-0.5">
                  {model.provider} · {model.family} · {model.context_length.toLocaleString()} ctx
                </div>
              </div>
              <button
                onClick={() => toggleModel(model.id, !model.enabled)}
                className={`px-3 py-1 text-xs rounded-md ${
                  model.enabled
                    ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                    : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                }`}
              >
                {model.enabled ? 'Enabled' : 'Disabled'}
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {model.capabilities.map((cap: string) => (
                <span key={cap} className="px-1.5 py-0.5 bg-blue-50 text-blue-700 text-xs rounded">
                  {cap}
                </span>
              ))}
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {model.roles.map((role: string) => (
                <span key={role} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                  {role}
                </span>
              ))}
            </div>
            <div className="mt-2 text-xs text-gray-400 flex gap-4">
              <span>~{model.avg_latency_ms}ms latency</span>
              <span>{model.gpu_memory_gb > 0 ? `${model.gpu_memory_gb}GB VRAM` : 'API'}</span>
              <span>{model.cost_per_1k_input > 0 ? `$${model.cost_per_1k_input}/1K in` : 'Free'}</span>
              {model.quantization && <span>{model.quantization}</span>}
              {model.supports_lora && <span>LoRA ✓</span>}
            </div>
          </div>
        ))}
      </div>

      {/* Role Assignments */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <SectionHeader title="Role → Model Assignments" />
        <div className="space-y-2">
          {Object.entries(data.roles?.role_assignments || {}).map(([role, info]: [string, any]) => (
            <div key={role} className="flex items-center justify-between text-sm p-2 bg-gray-50 rounded">
              <span className="font-medium text-gray-700">{role}</span>
              <div className="flex gap-2">
                <span className="text-emerald-600">{info.primary || 'none'}</span>
                {info.fallback && <span className="text-orange-500">fb: {info.fallback}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Providers Tab ──────────────────────────────────────────────

function ProvidersTab({ data }: { data: any }) {
  const providers = data.providers?.providers || {};
  const metrics = data.metrics?.provider_breakdown || {};

  return (
    <div className="space-y-4">
      <SectionHeader title="Provider Health & Metrics" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(providers).map(([name, info]: [string, any]) => (
          <div key={name} className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="font-semibold">{name}</span>
              <StatusBadge status={info.status} />
            </div>
            {metrics[name] && (
              <div className="space-y-1 text-sm text-gray-600">
                <div>Calls: {metrics[name].count}</div>
                <div>Errors: {metrics[name].errors}</div>
                <div>Avg Latency: {metrics[name].avg_latency_ms}ms</div>
                <div>Cost: ${metrics[name].total_cost_usd}</div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Routing Tab ────────────────────────────────────────────────

function RoutingTab({ data }: { data: any }) {
  const routing = data.routing || {};
  const policy = routing.policy || {};
  const stats = routing.stats || {};

  return (
    <div className="space-y-4">
      <SectionHeader title="Routing Policy" description="Configure how AI requests are routed to models" />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Profile" value={policy.profile || 'local'} />
        <MetricCard label="Prefer Free" value={policy.prefer_free ? 'Yes' : 'No'} />
        <MetricCard label="Fallback Enabled" value={policy.enable_fallback ? 'Yes' : 'No'} />
        <MetricCard label="Shadow Mode" value={policy.enable_shadow ? 'On' : 'Off'} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Total Calls" value={stats.total_calls || 0} />
        <MetricCard label="Errors" value={stats.error_count || 0} />
        <MetricCard label="Fallbacks" value={stats.fallback_count || 0} />
        <MetricCard label="Total Cost" value={`$${(stats.total_cost_usd || 0).toFixed(4)}`} />
      </div>

      {Object.keys(policy.role_overrides || {}).length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <SectionHeader title="Role Overrides" />
          {Object.entries(policy.role_overrides).map(([role, model]: [string, any]) => (
            <div key={role} className="flex justify-between text-sm p-2">
              <span>{role}</span>
              <span className="font-mono text-gray-600">{model}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Prompts Tab ────────────────────────────────────────────────

function PromptsTab({ data }: { data: any }) {
  const prompts = data.prompts?.prompts || [];

  return (
    <div className="space-y-4">
      <SectionHeader title="Prompt Registry" description="Versioned prompt templates for all AI operations" />
      <div className="space-y-2">
        {prompts.map((p: any) => (
          <div key={p.id} className="bg-white rounded-lg border border-gray-200 p-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="font-medium text-sm">{p.name}</span>
                <span className="text-xs text-gray-400 ml-2">{p.id}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 text-xs rounded">{p.category}</span>
                <span className="text-xs text-gray-500">v{p.active_version}</span>
              </div>
            </div>
            <div className="mt-1 text-xs text-gray-500 flex gap-3">
              <span>{p.variables?.length || 0} variables</span>
              <span>{p.example_count || 0} examples</span>
              <span>Format: {p.output_format || 'text'}</span>
              <span className="font-mono">{p.fingerprint}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Engines Tab ────────────────────────────────────────────────

function EnginesTab({ data }: { data: any }) {
  const engines = data.engines?.engines || [];

  return (
    <div className="space-y-4">
      <SectionHeader title="AI Engines" description="15 logical AI engines mapped to physical models" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {engines.map((e: any) => (
          <div key={e.engine} className="bg-white rounded-lg border border-gray-200 p-3">
            <div className="font-medium text-sm">{e.engine}</div>
            <div className="text-xs text-gray-500">Role: {e.role}</div>
            <div className="mt-2 flex justify-between text-xs">
              <span>Calls: {e.calls}</span>
              <span className={e.errors > 0 ? 'text-red-600' : 'text-emerald-600'}>
                Errors: {e.errors}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Traces Tab ─────────────────────────────────────────────────

function TracesTab({ data }: { data: any }) {
  const traces = data.traces?.traces || [];

  return (
    <div className="space-y-4">
      <SectionHeader title="AI Traces" description="Recent AI operation traces with full metadata" />
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
              <tr>
                <th className="px-3 py-2 text-left">Engine</th>
                <th className="px-3 py-2 text-left">Model</th>
                <th className="px-3 py-2 text-left">Provider</th>
                <th className="px-3 py-2 text-right">Latency</th>
                <th className="px-3 py-2 text-right">Tokens</th>
                <th className="px-3 py-2 text-right">Cost</th>
                <th className="px-3 py-2 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {traces.map((t: any, i: number) => (
                <tr key={i} className={t.success ? '' : 'bg-red-50'}>
                  <td className="px-3 py-2">{t.engine}</td>
                  <td className="px-3 py-2 font-mono text-xs">{t.model_used}</td>
                  <td className="px-3 py-2">{t.provider}</td>
                  <td className="px-3 py-2 text-right">{t.latency_ms}ms</td>
                  <td className="px-3 py-2 text-right">{t.input_tokens + t.output_tokens}</td>
                  <td className="px-3 py-2 text-right">${t.cost_usd}</td>
                  <td className="px-3 py-2 text-center">
                    {t.success ? '✓' : <span className="text-red-600" title={t.error}>✗</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Evals Tab ──────────────────────────────────────────────────

function EvalsTab({ data }: { data: any }) {
  const suites = data.evals?.suites || [];
  const runs = data.evalRuns?.runs || [];

  return (
    <div className="space-y-4">
      <SectionHeader title="Evaluation Suites" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {suites.map((s: any) => (
          <div key={s.id} className="bg-white rounded-lg border border-gray-200 p-3">
            <div className="font-medium text-sm">{s.name}</div>
            <div className="text-xs text-gray-500">
              Engine: {s.engine} · Cases: {s.case_count}
            </div>
            <div className="mt-1 flex gap-1">
              {s.tags.map((t: string) => (
                <span key={t} className="px-1.5 py-0.5 bg-gray-100 text-xs rounded">{t}</span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {runs.length > 0 && (
        <>
          <SectionHeader title="Recent Eval Runs" />
          <div className="space-y-2">
            {runs.map((r: any) => (
              <div key={r.id} className="bg-white rounded-lg border border-gray-200 p-3 flex justify-between">
                <div>
                  <span className="text-sm font-medium">{r.suite_id}</span>
                  <span className="text-xs text-gray-500 ml-2">{r.model}</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <span className={r.pass_rate >= 0.8 ? 'text-emerald-600' : 'text-red-600'}>
                    {(r.pass_rate * 100).toFixed(0)}% pass
                  </span>
                  <span className="text-gray-500">{r.passed}/{r.total_cases}</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ─── Training Tab ───────────────────────────────────────────────

function TrainingTab({ data }: { data: any }) {
  const stats = data.training || {};

  return (
    <div className="space-y-4">
      <SectionHeader title="Training Data Collection" description="Dataset statistics for future fine-tuning" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="SFT Examples" value={stats.sft_examples || 0} />
        <MetricCard label="Preference Pairs" value={stats.preference_examples || 0} />
        <MetricCard label="Recommendation Examples" value={stats.recommendation_examples || 0} />
        <MetricCard label="Content Examples" value={stats.content_examples || 0} />
      </div>

      {stats.sft_by_quality && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <SectionHeader title="SFT Quality Distribution" />
          <div className="grid grid-cols-4 gap-2 text-center text-sm">
            {Object.entries(stats.sft_by_quality).map(([q, count]: [string, any]) => (
              <div key={q} className="p-2 bg-gray-50 rounded">
                <div className="font-medium">{count}</div>
                <div className="text-xs text-gray-500">{q}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <SectionHeader title="Training Roadmap" />
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-emerald-500 rounded-full"></span>
            <span className="font-medium">Stage 1: Prompt + Routing</span>
            <span className="text-emerald-600 text-xs">ACTIVE</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-gray-300 rounded-full"></span>
            <span>Stage 2: Retrieval + Few-Shot (50+ examples needed)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-gray-300 rounded-full"></span>
            <span>Stage 3: LoRA Adapters (500+ examples needed)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-gray-300 rounded-full"></span>
            <span>Stage 4: SFT (2000+ gold examples needed)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-gray-300 rounded-full"></span>
            <span>Stage 5: DPO (1000+ preference pairs needed)</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Playground Tab ─────────────────────────────────────────────

function PlaygroundTab() {
  const [engine, setEngine] = useState('reasoning');
  const [message, setMessage] = useState('');
  const [result, setResult] = useState<any>(null);
  const [running, setRunning] = useState(false);

  const engines = [
    'reasoning', 'structured_output', 'content_strategy', 'recommendation',
    'competitor_reasoning', 'visibility_reasoning', 'social_adaptation',
    'ad_copy', 'report_synthesis', 'guardrail', 'routing',
  ];

  const run = async () => {
    if (!message.trim()) return;
    setRunning(true);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/ai/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, engine }),
      });
      setResult(await res.json());
    } catch (e: any) {
      setResult({ error: e.message });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      <SectionHeader title="AI Playground" description="Test AI engines directly" />

      <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
        <div className="flex gap-3">
          <select
            value={engine}
            onChange={(e) => setEngine(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-md text-sm"
          >
            {engines.map((e) => (
              <option key={e} value={e}>{e}</option>
            ))}
          </select>
          <button
            onClick={run}
            disabled={running || !message.trim()}
            className="px-4 py-2 bg-gray-900 text-white text-sm rounded-md hover:bg-gray-800 disabled:opacity-50"
          >
            {running ? 'Running...' : 'Run'}
          </button>
        </div>

        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Enter your task or question..."
          rows={4}
          className="w-full px-3 py-2 border border-gray-200 rounded-md text-sm"
        />
      </div>

      {result && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
          <div className="flex justify-between text-sm">
            <div className="flex gap-3 text-gray-500">
              <span>Engine: {result.engine}</span>
              <span>Model: {result.model_used}</span>
              <span>Provider: {result.provider_used}</span>
            </div>
            <div className="flex gap-3 text-gray-500">
              <span>{result.latency_ms}ms</span>
              <span>{result.input_tokens + result.output_tokens} tokens</span>
              <span>${result.cost_usd}</span>
            </div>
          </div>

          {result.error ? (
            <div className="p-3 bg-red-50 text-red-800 rounded text-sm">{result.error}</div>
          ) : (
            <pre className="p-3 bg-gray-50 rounded text-sm whitespace-pre-wrap overflow-auto max-h-96">
              {typeof result.data === 'object'
                ? JSON.stringify(result.data, null, 2)
                : result.raw_content || result.data}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
