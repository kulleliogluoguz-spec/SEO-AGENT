'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Twitter, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

type Status = 'loading' | 'success' | 'error';

function XCallback() {
  const router = useRouter();
  const params = useSearchParams();
  const [status, setStatus] = useState<Status>('loading');
  const [message, setMessage] = useState('Connecting your X account...');
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    // OAuth 1.0a callback params from Twitter
    const oauthToken = params.get('oauth_token');
    const oauthVerifier = params.get('oauth_verifier');
    const denied = params.get('denied');
    const error = params.get('error');

    if (denied) {
      setStatus('error');
      setMessage('Authorization was cancelled.');
      return;
    }

    if (error) {
      setStatus('error');
      setMessage(error === 'access_denied' ? 'Authorization was cancelled.' : decodeURIComponent(error));
      return;
    }

    if (!oauthToken || !oauthVerifier) {
      setStatus('error');
      setMessage('Missing OAuth parameters. Please try connecting again from Connections.');
      return;
    }

    (async () => {
      try {
        const token = localStorage.getItem('access_token') ?? '';
        const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiBase}/api/v1/auth/x/callback`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            oauth_token: oauthToken,
            oauth_verifier: oauthVerifier,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'OAuth exchange failed');

        setStatus('success');
        setMessage(`Connected as @${data.username || 'your account'}${data.followers ? ` (${data.followers.toLocaleString()} followers)` : ''}. Redirecting...`);
        setTimeout(() => router.replace('/dashboard/connectors?connected=x'), 1800);
      } catch (err: unknown) {
        setStatus('error');
        setMessage(err instanceof Error ? err.message : 'Connection failed. Please try again.');
      }
    })();
  }, [params, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-10 flex flex-col items-center gap-5 w-full max-w-sm">
        <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center">
          <Twitter className="w-6 h-6 text-sky-400" />
        </div>

        {status === 'loading' && <Loader2 className="w-6 h-6 text-sky-400 animate-spin" />}
        {status === 'success' && <CheckCircle2 className="w-6 h-6 text-emerald-400" />}
        {status === 'error' && <XCircle className="w-6 h-6 text-red-400" />}

        <p className="text-sm text-gray-300 text-center">{message}</p>

        {status === 'error' && (
          <div className="flex flex-col items-center gap-2">
            <button
              onClick={() => router.replace('/dashboard/connectors')}
              className="text-xs text-sky-400 underline"
            >
              Back to Connections
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function XCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <Loader2 className="w-6 h-6 text-sky-400 animate-spin" />
      </div>
    }>
      <XCallback />
    </Suspense>
  );
}
