'use client';

import { X, AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react';
import type { RiskDataPoint } from '@/lib/api';

interface RiskDetailModalProps {
  point: RiskDataPoint | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function RiskDetailModal({ point, isOpen, onClose }: RiskDetailModalProps) {
  if (!isOpen || !point) return null;

  const getRiskColor = (score: number) => {
    if (score > 70) return { text: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' };
    if (score > 50) return { text: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200' };
    if (score > 30) return { text: 'text-yellow-600', bg: 'bg-yellow-50', border: 'border-yellow-200' };
    return { text: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' };
  };

  const colors = getRiskColor(point.risk_score);
  const timestamp = new Date(
    typeof point.timestamp === 'string' ? point.timestamp : point.timestamp * 1000
  ).toLocaleString();

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 z-50 bg-white rounded-2xl shadow-2xl border border-slate-200 animate-fade-in">
        {/* Header */}
        <div className={`flex items-center justify-between p-6 border-b ${colors.border} ${colors.bg}`}>
          <h2 className={`text-lg font-bold ${colors.text}`}>Risk Snapshot</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white/50 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">
          {/* Main Risk Score */}
          <div className={`p-4 rounded-xl border ${colors.border} ${colors.bg}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-slate-600">Current Risk Score</span>
              <span className={`text-3xl font-bold ${colors.text}`}>{Math.round(point.risk_score)}</span>
            </div>
            <p className={`text-xs ${colors.text}`}>State: {point.risk_state || 'NORMAL'}</p>
          </div>

          {/* Timestamp */}
          <div className="px-4 py-2 bg-slate-50 rounded-lg border border-slate-200">
            <p className="text-xs font-semibold text-slate-500 mb-1">Timestamp</p>
            <p className="text-sm font-mono text-slate-700">{timestamp}</p>
          </div>

          {/* Risk Breakdown - Three Columns */}
          <div className="grid grid-cols-3 gap-3">
            {/* Workflow Risk */}
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-xs font-semibold text-blue-900 mb-1">Workflow</p>
              <p className="text-2xl font-bold text-blue-600">{Math.round(point.workflow_risk)}</p>
              <div className="flex items-center gap-1 mt-1 text-xs">
                {point.workflow_risk > 50 ? (
                  <>
                    <TrendingUp className="w-3 h-3 text-red-500" />
                    <span className="text-red-600">High</span>
                  </>
                ) : (
                  <>
                    <TrendingDown className="w-3 h-3 text-emerald-500" />
                    <span className="text-emerald-600">Acceptable</span>
                  </>
                )}
              </div>
            </div>

            {/* Resource Risk */}
            <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
              <p className="text-xs font-semibold text-emerald-900 mb-1">Resource</p>
              <p className="text-2xl font-bold text-emerald-600">{Math.round(point.resource_risk)}</p>
              <div className="flex items-center gap-1 mt-1 text-xs">
                {point.resource_risk > 50 ? (
                  <>
                    <TrendingUp className="w-3 h-3 text-red-500" />
                    <span className="text-red-600">High</span>
                  </>
                ) : (
                  <>
                    <TrendingDown className="w-3 h-3 text-emerald-500" />
                    <span className="text-emerald-600">Healthy</span>
                  </>
                )}
              </div>
            </div>

            {/* Compliance Risk */}
            <div className="p-3 bg-violet-50 rounded-lg border border-violet-200">
              <p className="text-xs font-semibold text-violet-900 mb-1">Compliance</p>
              <p className="text-2xl font-bold text-violet-600">{Math.round(point.compliance_risk)}</p>
              <div className="flex items-center gap-1 mt-1 text-xs">
                {point.compliance_risk > 50 ? (
                  <>
                    <AlertTriangle className="w-3 h-3 text-red-500" />
                    <span className="text-red-600">Issues</span>
                  </>
                ) : (
                  <>
                    <TrendingDown className="w-3 h-3 text-emerald-500" />
                    <span className="text-emerald-600">Good</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Contributing Factors */}
          {point.contributions && point.contributions.length > 0 && (
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                Contributing Factors
              </h3>
              <div className="space-y-2">
                {point.contributions.slice(0, 5).map((contrib, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 bg-white rounded border border-slate-200">
                    <span className="text-xs font-medium text-slate-700">{contrib.agent}</span>
                    <span
                      className={`text-xs font-bold ${
                        contrib.contribution > 0 ? 'text-red-600' : 'text-emerald-600'
                      }`}
                    >
                      {contrib.contribution > 0 ? '+' : ''}{contrib.contribution}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Close Button */}
          <button
            onClick={onClose}
            className="w-full py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-medium rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </>
  );
}
