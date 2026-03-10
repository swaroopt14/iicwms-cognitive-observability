'use client';

import { useParams, useRouter } from 'next/navigation';
import { AlertTriangle, ArrowLeft, ExternalLink } from 'lucide-react';

export default function AnomalyDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = typeof params?.id === 'string' ? params.id : Array.isArray(params?.id) ? params.id[0] : '';

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="icon-container icon-container-lg bg-gradient-to-br from-amber-500 to-orange-600 shadow-lg">
            <AlertTriangle className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="page-title">Anomaly Detail</h1>
            <p className="page-subtitle">This route is a placeholder in the current build. Use Anomaly Center for full detail.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn btn-secondary" onClick={() => router.push('/anomaly-center')}>
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <button className="btn btn-secondary" onClick={() => router.push('/audit')}>
            <ExternalLink className="w-4 h-4" />
            Open Audit
          </button>
        </div>
      </div>

      <div className="card p-6">
        <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider font-semibold">Anomaly ID</div>
        <div className="mt-2 text-sm font-mono text-[var(--color-text-primary)] break-all">{id || 'unknown'}</div>
        <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
          Go to <span className="font-semibold">Anomaly Center</span> to filter/search for this anomaly and view evidence.
        </p>
      </div>
    </div>
  );
}
