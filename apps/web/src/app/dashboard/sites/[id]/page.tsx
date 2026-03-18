'use client';

import { useState, useEffect, use } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost';

export default function SiteDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [site, setSite] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [token, setToken] = useState('');

  useEffect(() => {
    const t = document.cookie.split(';').find(c => c.trim().startsWith('token='))?.split('=')[1]
      || localStorage.getItem('token') || '';
    setToken(t);
  }, []);

  useEffect(() => {
    if (!token) return;
    fetch(`${API}/api/v1/sites/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(setSite)
      .catch(e => setError(e.message));
  }, [id, token]);

  const runAnalysis = async (engine: string, message: string) => {
    setAnalyzing(true);
    setAnalysis(null);
    try {
      const r = await fetch(`${API}/api/v1/ai/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, engine, max_tokens: 2048 }),
      });
      const data = await r.json();
      setAnalysis(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setAnalyzing(false);
    }
  };

  if (error && !site) return <div className="p-8 text-red-600">Error: {error}</div>;
  if (!site) return <div className="p-8 text-gray-500">Loading site...</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto space-y-6">

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{site.name}</h1>
              <a href={site.url} target="_blank" className="text-blue-600 text-sm hover:underline">
                {site.url}
              </a>
            </div>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              site.status === 'active' ? 'bg-emerald-100 text-emerald-800' :
              site.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {site.status}
            </span>
          </div>
          {site.product_summary && (
            <p className="mt-3 text-gray-600 text-sm">{site.product_summary}</p>
          )}
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">AI Analysis</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <button
              onClick={() => runAnalysis('reasoning',
                `Perform a technical SEO audit for ${site.url} (${site.name}). ${site.product_summary || ''}. Give 5 prioritized recommendations with severity levels.`
              )}
              disabled={analyzing}
              className="px-4 py-3 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              SEO Audit
            </button>
            <button
              onClick={() => runAnalysis('content_strategy',
                `Create a content strategy for ${site.url} (${site.name}). ${site.product_summary || ''}. Include topic clusters, keyword targets, and content types.`
              )}
              disabled={analyzing}
              className="px-4 py-3 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 disabled:opacity-50"
            >
              Content Strategy
            </button>
            <button
              onClick={() => runAnalysis('competitor_reasoning',
                `Identify top 3 competitors for ${site.url} (${site.name}). ${site.product_summary || ''}. Compare their SEO strategies and find gaps.`
              )}
              disabled={analyzing}
              className="px-4 py-3 bg-orange-600 text-white text-sm rounded-lg hover:bg-orange-700 disabled:opacity-50"
            >
              Competitor Analysis
            </button>
            <button
              onClick={() => runAnalysis('visibility_reasoning',
                `Analyze AI visibility (GEO/AEO) for ${site.url} (${site.name}). ${site.product_summary || ''}. How well would this site appear in AI search results? Give specific improvement recommendations.`
              )}
              disabled={analyzing}
              className="px-4 py-3 bg-teal-600 text-white text-sm rounded-lg hover:bg-teal-700 disabled:opacity-50"
            >
              AI Visibility
            </button>
            <button
              onClick={() => runAnalysis('recommendation',
                `Generate 5 prioritized growth recommendations for ${site.url} (${site.name}). ${site.product_summary || ''}. Include impact estimate, effort, and evidence for each.`
              )}
              disabled={analyzing}
              className="px-4 py-3 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700 disabled:opacity-50"
            >
              Recommendations
            </button>
            <button
              onClick={() => runAnalysis('social_adaptation',
                `Create social media content plan for ${site.url} (${site.name}). ${site.product_summary || ''}. Adapt for LinkedIn, Twitter, and Instagram.`
              )}
              disabled={analyzing}
              className="px-4 py-3 bg-pink-600 text-white text-sm rounded-lg hover:bg-pink-700 disabled:opacity-50"
            >
              Social Content
            </button>
          </div>
        </div>

        {analyzing && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 text-center">
            <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-3"></div>
            <p className="text-gray-600">AI is analyzing... This may take 1-2 minutes.</p>
            <p className="text-gray-400 text-sm mt-1">Running on local Qwen3 model (free, private)</p>
          </div>
        )}

        {analysis && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Analysis Results</h2>
              <div className="flex gap-3 text-xs text-gray-400">
                <span>Model: {analysis.model_used}</span>
                <span>Latency: {Math.round(analysis.latency_ms / 1000)}s</span>
                <span>Cost: ${analysis.cost_usd}</span>
                <span>Engine: {analysis.engine}</span>
              </div>
            </div>

            {analysis.success ? (
              <div className="prose prose-sm max-w-none">
                <div className="whitespace-pre-wrap text-gray-700 leading-relaxed"
                     dangerouslySetInnerHTML={{
                       __html: (analysis.raw_content || '')
                         .replace(/### (.*)/g, '<h3 class="text-base font-semibold mt-4 mb-2">$1</h3>')
                         .replace(/## (.*)/g, '<h2 class="text-lg font-bold mt-5 mb-2">$1</h2>')
                         .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                         .replace(/\*(.*?)\*/g, '<em>$1</em>')
                         .replace(/---/g, '<hr class="my-4">')
                         .replace(/\n/g, '<br>')
                     }}
                />
              </div>
            ) : (
              <div className="text-red-600 p-4 bg-red-50 rounded">
                Error: {analysis.error}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
