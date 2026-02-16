'use client';

import { useState } from 'react';
import { HelpCircle, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';

interface MetricCardWithHelpProps {
  title: string;
  value: number | string;
  unit?: string;
  trend?: number; // positive or negative trend
  definition: string; // What the metric means
  healthyRange: string; // e.g., "0-30%"
  currentStatus: 'healthy' | 'warning' | 'critical';
  statusMessage: string;
  color?: string; // Main metric color
}

export default function MetricCardWithHelp({
  title,
  value,
  unit = '',
  trend,
  definition,
  healthyRange,
  currentStatus,
  statusMessage,
  color = '#6366f1',
}: MetricCardWithHelpProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  const getStatusStyles = (status: string) => {
    switch (status) {
      case 'healthy':
        return { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', dot: 'bg-emerald-500' };
      case 'warning':
        return { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', dot: 'bg-yellow-500' };
      case 'critical':
        return { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', dot: 'bg-red-500' };
      default:
        return { bg: 'bg-slate-50', border: 'border-slate-200', text: 'text-slate-700', dot: 'bg-slate-500' };
    }
  };

  const styles = getStatusStyles(currentStatus);
  const trendIsPositive = typeof trend === 'number' && trend > 0;

  return (
    <div className={`relative p-5 rounded-xl border ${styles.border} ${styles.bg} transition-all duration-300 hover:shadow-md`}>
      {/* Header: Title + Info Icon */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowTooltip(!showTooltip)}
            className="p-1.5 rounded-lg hover:bg-slate-200/50 transition-colors"
            aria-label={`Help for ${title}`}
          >
            <HelpCircle className="w-4 h-4 text-slate-500 hover:text-slate-700" />
          </button>

          {/* Tooltip */}
          {showTooltip && (
            <div
              className="absolute right-0 mt-2 w-72 bg-slate-900 text-white rounded-lg shadow-2xl p-4 z-50 animate-fade-in text-sm leading-relaxed"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                type="button"
                onClick={() => setShowTooltip(false)}
                className="absolute top-2 right-2 text-slate-400 hover:text-white"
              >
                ✕
              </button>
              
              {/* Tooltip Content */}
              <div className="space-y-3 pr-6">
                {/* Definition */}
                <div>
                  <p className="text-xs font-semibold text-slate-300 uppercase mb-1">Definition</p>
                  <p className="text-sm text-slate-200">{definition}</p>
                </div>

                {/* Healthy Range */}
                <div className="pt-2 border-t border-slate-700">
                  <p className="text-xs font-semibold text-slate-300 uppercase mb-1">Healthy Range</p>
                  <p className="text-sm text-slate-200">{healthyRange}</p>
                </div>

                {/* Current Status */}
                <div className="pt-2 border-t border-slate-700">
                  <p className="text-xs font-semibold text-slate-300 uppercase mb-1">Current Status</p>
                  <p className={`text-sm font-medium ${
                    currentStatus === 'healthy' ? 'text-emerald-300' : 
                    currentStatus === 'warning' ? 'text-yellow-300' : 
                    'text-red-300'
                  }`}>
                    {statusMessage}
                  </p>
                </div>

                {/* Recommendation */}
                <div className="pt-2 border-t border-slate-700 bg-slate-800/50 rounded p-2">
                  <p className="text-xs text-slate-300">
                    💡 <span className="font-semibold">Tip:</span> Monitor this metric regularly and investigate spikes above the healthy range.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Metric Value */}
      <div className="mb-4">
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold" style={{ color }}>{value}</span>
          {unit && <span className="text-sm font-medium text-slate-500">{unit}</span>}
        </div>
      </div>

      {/* Trend Indicator */}
      {typeof trend === 'number' && (
        <div className={`flex items-center gap-1.5 text-xs font-medium ${
          trendIsPositive ? 'text-red-600' : 'text-emerald-600'
        }`}>
          {trendIsPositive ? (
            <>
              <TrendingUp className="w-3.5 h-3.5" />
              <span>+{trend}% from last hour</span>
            </>
          ) : (
            <>
              <TrendingDown className="w-3.5 h-3.5" />
              <span>{trend}% from last hour</span>
            </>
          )}
        </div>
      )}

      {/* Status Badge */}
      <div className={`mt-3 flex items-center gap-2 text-xs font-semibold ${styles.text}`}>
        <div className={`w-2.5 h-2.5 rounded-full ${styles.dot} animate-pulse`} />
        <span className="capitalize">{currentStatus}</span>
        {currentStatus === 'critical' && <AlertCircle className="w-3 h-3 ml-auto" />}
      </div>
    </div>
  );
}
