'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Instagram, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

type Status = 'loading' | 'success' | 'error';

function MetaCallback() {
  const router = useRouter();
  const params = useSearchParams();
  const [status, setStatus] = useState<Status>('loading');
  const [message, setMessage] = useState('Connecting your Meta account...');
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    const code = params.get('code');
    const state = params.get('state');
    const error = params.get('error');

    if (error || !code || !state) {
      setStatus('error');
      setMessage(error === 'access_denied' ? 'Authorization was cancelled.' : 'Missing OAuth parameters.');
      return;
    }

    (async () => {
      try {
        const res = await fetch('/api/v1/auth/meta/callback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ code, state }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'OAuth exchange failed');

        const accountSummary = [
          data.instagram_accounts?.length ? `${data.instagram_accounts.length} Instagram account(s)` : null,
          data.pages?.length ? `${data.pages.length} Facebook Page(s)` : null,
          data.ad_accounts?.length ? `${data.ad_accounts.length} ad account(s)` : null,
        ].filter(Boolean).join(', ');

        setStatus('success');
        setMessage(`Connected${accountSummary ? `: ${accountSummary}` : ''}. Redirecting...`);
        setTimeout(() => router.replace('/dashboard/connectors'), 1800);
      } catch (err: unknown) {
        setStatus('error');
        setMessage(err instanceof Error ? err.message : 'Connection failed. Please try again.');
      }
    })();
  }, [params, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-10 flex flex-col items-center gap-5 w-full max-w-sm">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
          <Instagram className="w-6 h-6 text-white" />
        </div>

        {status === 'loading' && <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />}
        {status === 'success' && <CheckCircle2 className="w-6 h-6 text-emerald-400" />}
        {status === 'error' && <XCircle className="w-6 h-6 text-red-400" />}

        <p className="text-sm text-gray-300 text-center">{message}</p>

        {status === 'error' && (
          <button onClick={() => router.replace('/dashboard/connectors')} className="text-xs text-purple-400 underline">
            Back to Connections
          </button>
        )}
      </div>
    </div>
  );
}

export default function MetaCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
      </div>
    }>
      <MetaCallback />
    </Suspense>
  );
}
