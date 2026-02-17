'use client';

import { useQuery } from '@tanstack/react-query';
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  GitMerge,
  X,
  ChevronRight,
  ExternalLink,
  Info,
  Zap,
  AlertTriangle,
  ArrowRight,
  Camera,
  Download,
  Network,
  Activity,
  TrendingUp,
  Clock,
  FileText,
} from 'lucide-react';
import { fetchCausalLinks, fetchWorkflows, type CausalLink } from '@/lib/api';
import { formatTime } from '@/lib/utils';
import { DonutChart } from '@/components/Charts';

// Helper: shorten a node label like "NETWORK_LATENCY_SPIKE (vm_api_01)" → "NET LATENCY\nvm_api_01"
function shortenLabel(raw: string): string[] {
  // Extract parenthetical
  const match = raw.match(/^(.+?)\s*\((.+)\)$/);
  const main = match ? match[1] : raw;
  const sub = match ? match[2] : '';

  // Abbreviate the main part
  const abbreviated = main
    .replace(/_/g, ' ')
    .replace(/NETWORK/i, 'NET')
    .replace(/LATENCY/i, 'LAT')
    .replace(/SPIKE/i, 'SPK')
    .replace(/WORKFLOW/i, 'WF')
    .replace(/SATURATION/i, 'SAT')
    .replace(/CONCURRENT/i, 'CONC')
    .replace(/CONTENTION/i, 'CONT')
    .replace(/DEGRADATION/i, 'DEGRAD')
    .replace(/COMPLIANCE/i, 'COMPL')
    .replace(/VIOLATION/i, 'VIOL')
    .replace(/APPROVAL/i, 'APPR')
    .replace(/PRESSURE/i, 'PRESS')
    .replace(/TIMEOUT/i, 'TMO')
    .replace(/CLUSTER/i, 'CLSTR')
    .replace(/UNKNOWN/i, 'UNK')
    .replace(/LOCATION/i, 'LOC')
    .replace(/MEMORY/i, 'MEM')
    .replace(/SLOWDOWN/i, 'SLOW')
    .replace(/RESOURCE/i, 'RES')
    .replace(/WORKLOAD/i, 'WKLD')
    .replace(/AFTER HOURS/i, 'AH')
    .replace(/ACCESS/i, 'ACC');

  if (sub) return [abbreviated.trim(), sub];
  // Split long labels
  const words = abbreviated.trim().split(' ');
  if (words.length > 2) {
    return [words.slice(0, 2).join(' '), words.slice(2).join(' ')];
  }
  return [abbreviated.trim()];
}

// Node color based on label category
function nodeColor(label: string): string {
  const l = label.toLowerCase();
  if (l.includes('cpu') || l.includes('memory') || l.includes('resource') || l.includes('gc')) return '#10b981';
  if (l.includes('workflow') || l.includes('deploy') || l.includes('retry') || l.includes('build') || l.includes('api')) return '#6366f1';
  if (l.includes('compliance') || l.includes('violation') || l.includes('approval') || l.includes('sla')) return '#ef4444';
  if (l.includes('network') || l.includes('latency') || l.includes('timeout')) return '#f59e0b';
  if (l.includes('access') || l.includes('vpn') || l.includes('location') || l.includes('hours')) return '#8b5cf6';
  if (l.includes('surge') || l.includes('workload') || l.includes('concurrent')) return '#06b6d4';
  return '#64748b';
}

// Causal Graph Canvas
function CausalGraph({
  links,
  selectedLink,
  onLinkSelect,
}: {
  links: CausalLink[];
  selectedLink: CausalLink | null;
  onLinkSelect: (link: CausalLink) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    const centerX = width / 2;
    const centerY = height / 2;

    ctx.clearRect(0, 0, width, height);

    // Background
    const bgGradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, Math.max(width, height) / 2);
    bgGradient.addColorStop(0, '#fafbfe');
    bgGradient.addColorStop(1, '#f1f5f9');
    ctx.fillStyle = bgGradient;
    ctx.fillRect(0, 0, width, height);

    // Subtle grid
    ctx.strokeStyle = '#f0f0f5';
    ctx.lineWidth = 0.5;
    for (let gx = 0; gx < width; gx += 40) {
      ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, height); ctx.stroke();
    }
    for (let gy = 0; gy < height; gy += 40) {
      ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(width, gy); ctx.stroke();
    }

    if (links.length === 0) {
      ctx.fillStyle = '#94a3b8';
      ctx.font = '14px Inter, system-ui';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('No causal links to display', centerX, centerY);
      return;
    }

    // Unique nodes
    const nodesSet = new Set<string>();
    links.forEach((link) => { nodesSet.add(link.cause); nodesSet.add(link.effect); });
    const nodes = Array.from(nodesSet);

    // Circular layout with padding
    const nodePositions = new Map<string, { x: number; y: number }>();
    const layoutRadius = Math.min(width, height) * 0.37;
    const NODE_R = 32;

    nodes.forEach((node, i) => {
      const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
      nodePositions.set(node, {
        x: centerX + Math.cos(angle) * layoutRadius,
        y: centerY + Math.sin(angle) * layoutRadius,
      });
    });

    // Draw links
    links.forEach((link) => {
      const from = nodePositions.get(link.cause);
      const to = nodePositions.get(link.effect);
      if (!from || !to) return;

      const isSelected = selectedLink?.cause === link.cause && selectedLink?.effect === link.effect;
      const alpha = link.confidence / 100;
      const linkColor = link.confidence > 70 ? '#10b981' : link.confidence > 40 ? '#f59e0b' : '#ef4444';

      const dx = to.x - from.x;
      const dy = to.y - from.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const curvature = dist * 0.15;
      const perpX = (-dy / dist) * curvature;
      const perpY = (dx / dist) * curvature;
      const midX = (from.x + to.x) / 2 + perpX;
      const midY = (from.y + to.y) / 2 + perpY;

      // Draw curved line
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.quadraticCurveTo(midX, midY, to.x, to.y);
      ctx.strokeStyle = isSelected ? linkColor : `rgba(99, 102, 241, ${alpha * 0.5})`;
      ctx.lineWidth = isSelected ? 3.5 : 1.5;
      if (!isSelected) { ctx.setLineDash([4, 4]); } else { ctx.setLineDash([]); }
      ctx.stroke();
      ctx.setLineDash([]);

      // Arrow near target
      const arrowAngle = Math.atan2(to.y - midY, to.x - midX);
      const arrowDist = NODE_R + 6;
      const ax = to.x - Math.cos(arrowAngle) * arrowDist;
      const ay = to.y - Math.sin(arrowAngle) * arrowDist;
      const arrowSize = isSelected ? 10 : 7;

      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(ax - arrowSize * Math.cos(arrowAngle - Math.PI / 7), ay - arrowSize * Math.sin(arrowAngle - Math.PI / 7));
      ctx.lineTo(ax - arrowSize * Math.cos(arrowAngle + Math.PI / 7), ay - arrowSize * Math.sin(arrowAngle + Math.PI / 7));
      ctx.closePath();
      ctx.fillStyle = isSelected ? linkColor : `rgba(99, 102, 241, ${alpha * 0.7})`;
      ctx.fill();

      // Confidence label on selected link
      if (isSelected) {
        const labelX = midX;
        const labelY = midY - 12;
        ctx.fillStyle = '#fff';
        ctx.beginPath();
        const tw = ctx.measureText(`${link.confidence}%`).width + 12;
        const rr = (x: number, y: number, w: number, h: number, r: number) => {
          ctx.beginPath(); ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
          ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
          ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
          ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
        };
        rr(labelX - tw / 2, labelY - 9, tw, 18, 4);
        ctx.fillStyle = linkColor;
        ctx.fill();
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 10px Inter, system-ui';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${link.confidence}%`, labelX, labelY);
      }
    });

    // Draw nodes
    nodes.forEach((node) => {
      const pos = nodePositions.get(node);
      if (!pos) return;

      const isSelected = selectedLink?.cause === node || selectedLink?.effect === node;
      const nColor = nodeColor(node);
      const lines = shortenLabel(node);

      // Glow
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, NODE_R + 10, 0, Math.PI * 2);
        const glow = ctx.createRadialGradient(pos.x, pos.y, NODE_R, pos.x, pos.y, NODE_R + 10);
        glow.addColorStop(0, `${nColor}40`);
        glow.addColorStop(1, `${nColor}00`);
        ctx.fillStyle = glow;
        ctx.fill();
      }

      // Shadow
      ctx.shadowColor = 'rgba(0,0,0,0.08)';
      ctx.shadowBlur = 8;
      ctx.shadowOffsetY = 3;

      // Circle
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, NODE_R, 0, Math.PI * 2);
      ctx.fillStyle = isSelected ? '#fff' : '#fff';
      ctx.fill();
      ctx.strokeStyle = isSelected ? nColor : '#e2e8f0';
      ctx.lineWidth = isSelected ? 2.5 : 1.5;
      ctx.stroke();

      ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;

      // Colored top stripe
      ctx.save();
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, NODE_R - 1, -Math.PI, 0); // top semicircle clip
      ctx.lineTo(pos.x + NODE_R - 1, pos.y - NODE_R + 8);
      ctx.arc(pos.x, pos.y, NODE_R - 1, 0, -Math.PI, true);
      ctx.closePath();
      ctx.clip();
      ctx.fillStyle = `${nColor}18`;
      ctx.fillRect(pos.x - NODE_R, pos.y - NODE_R, NODE_R * 2, 14);
      ctx.restore();

      // Labels
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      if (lines.length === 1) {
        ctx.fillStyle = isSelected ? nColor : '#475569';
        ctx.font = `${isSelected ? 'bold ' : ''}9px Inter, system-ui`;
        ctx.fillText(lines[0].substring(0, 14), pos.x, pos.y);
      } else {
        ctx.fillStyle = isSelected ? nColor : '#475569';
        ctx.font = `${isSelected ? 'bold ' : ''}8.5px Inter, system-ui`;
        ctx.fillText(lines[0].substring(0, 14), pos.x, pos.y - 6);
        ctx.fillStyle = isSelected ? nColor : '#94a3b8';
        ctx.font = `${isSelected ? 'bold ' : ''}8px Inter, system-ui`;
        ctx.fillText(lines[1].substring(0, 14), pos.x, pos.y + 7);
      }
    });
  }, [links, selectedLink]);

  useEffect(() => {
    draw();
    const handleResize = () => draw();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [draw]);

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const layoutRadius = Math.min(rect.width, rect.height) * 0.37;

    const nodesSet = new Set<string>();
    links.forEach((link) => { nodesSet.add(link.cause); nodesSet.add(link.effect); });
    const nodes = Array.from(nodesSet);

    const nodePositions = new Map<string, { x: number; y: number }>();
    nodes.forEach((node, i) => {
      const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
      nodePositions.set(node, {
        x: centerX + Math.cos(angle) * layoutRadius,
        y: centerY + Math.sin(angle) * layoutRadius,
      });
    });

    // Check if clicked on a node first
    for (const link of links) {
      for (const nodeKey of [link.cause, link.effect]) {
        const pos = nodePositions.get(nodeKey);
        if (!pos) continue;
        if (Math.sqrt((x - pos.x) ** 2 + (y - pos.y) ** 2) < 35) {
          // Find a link involving this node
          const found = links.find(l => l.cause === nodeKey || l.effect === nodeKey);
          if (found) { onLinkSelect(found); return; }
        }
      }
    }

    // Check link midpoints
    for (const link of links) {
      const from = nodePositions.get(link.cause);
      const to = nodePositions.get(link.effect);
      if (!from || !to) continue;
      const midX = (from.x + to.x) / 2;
      const midY = (from.y + to.y) / 2;
      if (Math.sqrt((x - midX) ** 2 + (y - midY) ** 2) < 30) {
        onLinkSelect(link);
        return;
      }
    }
  };

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full cursor-pointer"
      onClick={handleClick}
    />
  );
}

// Helper: truncate a causal label
function truncateLabel(label: string, max: number = 24): string {
  const match = label.match(/^(.+?)\s*\((.+)\)$/);
  if (match) {
    const main = match[1].replace(/_/g, ' ');
    return main.length > max ? main.substring(0, max) + '...' : `${main} (${match[2]})`;
  }
  const clean = label.replace(/_/g, ' ');
  return clean.length > max ? clean.substring(0, max) + '...' : clean;
}

// Causal Link Card
function CausalLinkCard({
  link,
  isSelected,
  onClick,
}: {
  link: CausalLink;
  isSelected: boolean;
  onClick: () => void;
}) {
  const confidenceColor = link.confidence > 70 ? '#10b981' : link.confidence > 40 ? '#f59e0b' : '#ef4444';
  const causeColor = nodeColor(link.cause);
  const effectColor = nodeColor(link.effect);

  return (
    <div
      className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
        isSelected
          ? 'bg-indigo-50 border-indigo-300 shadow-md'
          : 'bg-white border-[var(--color-border)] hover:border-indigo-200 hover:shadow-sm'
      }`}
      onClick={onClick}
    >
      {/* Cause */}
      <div className="flex items-center gap-2 mb-1.5">
        <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: causeColor }} />
        <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate" title={link.cause}>
          {truncateLabel(link.cause, 28)}
        </span>
      </div>
      {/* Arrow + confidence */}
      <div className="flex items-center gap-2 ml-1 mb-1.5">
        <ArrowRight className="w-3 h-3 text-indigo-400" />
        <div className="flex-1 h-px bg-gradient-to-r from-indigo-200 to-transparent" />
        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ backgroundColor: `${confidenceColor}15`, color: confidenceColor }}>
          {link.confidence}%
        </span>
      </div>
      {/* Effect */}
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: effectColor }} />
        <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate" title={link.effect}>
          {truncateLabel(link.effect, 28)}
        </span>
      </div>
      {link.easy_summary && (
        <div className="mt-2 text-[11px] text-[var(--color-text-muted)]">
          {link.easy_summary}
        </div>
      )}
    </div>
  );
}

// Snapshot Modal
function SnapshotModal({ link, allLinks, onClose }: { link: CausalLink; allLinks: CausalLink[]; onClose: () => void }) {
  const snapshotTime = new Date().toLocaleString();
  const totalConfidence = allLinks.length > 0 ? Math.round(allLinks.reduce((a, l) => a + l.confidence, 0) / allLinks.length) : 0;

  return (
    <>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[60] flex items-center justify-center p-4" onClick={onClose}>
        <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-hidden animate-scale-in" onClick={(e) => e.stopPropagation()}>
          <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between bg-gradient-to-r from-indigo-50 to-violet-50">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center shadow-md">
                <Camera className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="font-semibold text-lg text-[var(--color-text-primary)]">Causal Analysis Snapshot</h2>
                <p className="text-xs text-[var(--color-text-muted)]">Captured at {snapshotTime}</p>
              </div>
            </div>
            <button onClick={onClose} className="p-2 rounded-xl hover:bg-slate-100 transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="p-5 space-y-5 overflow-y-auto max-h-[calc(85vh-140px)]">
            {/* Summary Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 rounded-xl border border-indigo-200 bg-indigo-50 text-center">
                <div className="text-2xl font-bold text-indigo-600">{allLinks.length}</div>
                <div className="text-xs text-indigo-700 font-medium">Causal Links</div>
              </div>
              <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50 text-center">
                <div className="text-2xl font-bold text-emerald-600">{totalConfidence}%</div>
                <div className="text-xs text-emerald-700 font-medium">Avg Confidence</div>
              </div>
              <div className="p-4 rounded-xl border border-amber-200 bg-amber-50 text-center">
                <div className="text-2xl font-bold text-amber-600">{new Set(allLinks.flatMap(l => [l.cause, l.effect])).size}</div>
                <div className="text-xs text-amber-700 font-medium">Unique Nodes</div>
              </div>
            </div>

            {/* Selected Link Highlight */}
            <div className="p-4 rounded-xl border-2 border-indigo-300 bg-gradient-to-r from-indigo-50 to-violet-50">
              <div className="text-xs text-indigo-600 font-semibold uppercase tracking-wider mb-2">Selected Relationship</div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-bold text-[var(--color-text-primary)]">{link.cause}</span>
                <ArrowRight className="w-4 h-4 text-indigo-400" />
                <span className="text-sm font-bold text-[var(--color-text-primary)]">{link.effect}</span>
                <span className="ml-auto text-sm font-bold text-indigo-600">{link.confidence}%</span>
              </div>
            </div>

            {/* Full Chain Table */}
            <div>
              <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-3 font-semibold">All Causal Relationships</div>
              <div className="border border-[var(--color-border)] rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-slate-50 border-b border-[var(--color-border)]">
                      <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--color-text-muted)]">Cause</th>
                      <th className="px-3 py-2 text-center text-xs font-semibold text-[var(--color-text-muted)]"></th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--color-text-muted)]">Effect</th>
                      <th className="px-3 py-2 text-right text-xs font-semibold text-[var(--color-text-muted)]">Conf.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allLinks.map((l, i) => (
                      <tr key={i} className={`border-b border-[var(--color-border)] last:border-0 ${l.cause === link.cause && l.effect === link.effect ? 'bg-indigo-50' : ''}`}>
                        <td className="px-3 py-2 text-xs font-medium">{l.cause}</td>
                        <td className="px-1 py-2 text-center"><ArrowRight className="w-3 h-3 text-slate-400 mx-auto" /></td>
                        <td className="px-3 py-2 text-xs font-medium">{l.effect}</td>
                        <td className="px-3 py-2 text-right text-xs font-bold" style={{ color: l.confidence > 70 ? '#10b981' : l.confidence > 40 ? '#f59e0b' : '#ef4444' }}>{l.confidence}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Export Buttons */}
            <div className="flex gap-3 pt-2">
              <button className="btn btn-primary flex-1" onClick={() => {
                const blob = new Blob([JSON.stringify({ snapshot_time: snapshotTime, selected_link: link, all_links: allLinks }, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a'); a.href = url; a.download = `causal-snapshot-${Date.now()}.json`; a.click();
              }}>
                <Download className="w-4 h-4" />
                Export JSON
              </button>
              <button className="btn btn-secondary flex-1" onClick={onClose}>Close</button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// Insight Detail Panel
function InsightDetailPanel({ link, allLinks, onClose, onNavigate }: { link: CausalLink; allLinks: CausalLink[]; onClose: () => void; onNavigate: (path: string) => void }) {
  const [showSnapshot, setShowSnapshot] = useState(false);
  const confidenceColor = link.confidence > 70 ? '#10b981' : link.confidence > 40 ? '#f59e0b' : '#ef4444';

  // Impact analysis data
  const impactAnalysis = {
    directEffects: allLinks.filter(l => l.cause === link.effect).length,
    upstreamCauses: allLinks.filter(l => l.effect === link.cause).length,
    blastRadius: new Set(allLinks.filter(l => l.cause === link.cause || l.cause === link.effect).map(l => l.effect)).size,
  };

  const competingCauses = allLinks.filter(
    (l) => l.effect === link.effect && l.cause !== link.cause
  ).length;
  const easyActions = (link.recommended_actions && link.recommended_actions.length > 0)
    ? link.recommended_actions
    : [
        'Contain impact immediately (throttle, isolate, or rollback).',
        'Fix upstream cause, then retry affected workflow steps.',
        'Verify two healthy cycles before closing incident.',
      ];
  const checklist = link.checklist ?? {
    do_now: [
      { owner: 'DevOps', action: easyActions[0] || 'Contain impact immediately.' },
    ],
    do_next: [
      { owner: 'SDE', action: easyActions[1] || 'Fix upstream cause and retry safely.' },
    ],
    verify: [
      { owner: 'Security', action: easyActions[2] || 'Verify stable recovery and compliance.' },
    ],
  };
  const ownerStyles: Record<string, string> = {
    DevOps: 'bg-blue-100 text-blue-700',
    SDE: 'bg-indigo-100 text-indigo-700',
    Security: 'bg-emerald-100 text-emerald-700',
  };

  // Root cause path (find the full chain ending at this link's effect)
  const rootCausePath: string[] = [];
  let current = link.cause;
  const visited = new Set<string>();
  while (current && !visited.has(current)) {
    visited.add(current);
    rootCausePath.unshift(current);
    const parent = allLinks.find(l => l.effect.includes(current.split(' ')[0]) || l.effect === current);
    if (parent && parent.cause !== current) {
      current = parent.cause;
    } else break;
  }
  rootCausePath.push(link.effect);

  return (
    <>
      <div className="card border border-[var(--color-border)] overflow-hidden">
        <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between bg-gradient-to-r from-slate-50 to-white">
          <div className="flex items-center gap-3">
            <div className="icon-container icon-container-md bg-gradient-to-br from-indigo-500 to-violet-500 shadow-md">
              <GitMerge className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-lg text-[var(--color-text-primary)]">Causal Relationship</h2>
              <p className="text-sm text-[var(--color-text-muted)]">{link.link_id} · Evidence-backed reasoning</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-slate-100 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          {/* Cause -> Effect */}
          <div className="p-5 bg-gradient-to-r from-indigo-50 to-violet-50 rounded-xl border border-indigo-200">
            <div className="flex items-center justify-center gap-4">
              <div className="text-center">
                <div className="w-16 h-16 rounded-2xl bg-white shadow-md flex items-center justify-center mx-auto mb-2 border border-indigo-200">
                  <AlertTriangle className="w-8 h-8 text-amber-500" />
                </div>
                <span className="text-sm font-semibold text-[var(--color-text-primary)]">{link.cause}</span>
                <div className="text-xs text-[var(--color-text-muted)]">Cause</div>
              </div>
              <div className="flex items-center gap-2 px-4">
                <ArrowRight className="w-6 h-6 text-indigo-400" />
                <div className="text-center">
                  <DonutChart value={link.confidence} total={100} color={confidenceColor} size={48} strokeWidth={5} />
                </div>
                <ArrowRight className="w-6 h-6 text-indigo-400" />
              </div>
              <div className="text-center">
                <div className="w-16 h-16 rounded-2xl bg-white shadow-md flex items-center justify-center mx-auto mb-2 border border-indigo-200">
                  <Zap className="w-8 h-8 text-red-500" />
                </div>
                <span className="text-sm font-semibold text-[var(--color-text-primary)]">{link.effect}</span>
                <div className="text-xs text-[var(--color-text-muted)]">Effect</div>
              </div>
            </div>
          </div>

          {/* Impact Analysis */}
          <div>
            <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-3 font-semibold">Impact Analysis</div>
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 rounded-xl border border-[var(--color-border)] text-center">
                <div className="text-xl font-bold text-indigo-600">{impactAnalysis.directEffects}</div>
                <div className="text-[10px] text-[var(--color-text-muted)] font-medium">Downstream Effects</div>
              </div>
              <div className="p-3 rounded-xl border border-[var(--color-border)] text-center">
                <div className="text-xl font-bold text-amber-600">{impactAnalysis.upstreamCauses}</div>
                <div className="text-[10px] text-[var(--color-text-muted)] font-medium">Upstream Causes</div>
              </div>
              <div className="p-3 rounded-xl border border-[var(--color-border)] text-center">
                <div className="text-xl font-bold text-red-600">{impactAnalysis.blastRadius}</div>
                <div className="text-[10px] text-[var(--color-text-muted)] font-medium">Blast Radius</div>
              </div>
            </div>
          </div>

          {/* Confidence */}
          <div className="p-4 rounded-xl border border-[var(--color-border)]">
            <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Confidence</div>
            <div className="flex items-center gap-3">
              <DonutChart value={link.confidence} total={100} color={confidenceColor} size={48} strokeWidth={5} />
              <span className="text-2xl font-bold" style={{ color: confidenceColor }}>{link.confidence}%</span>
            </div>
          </div>

          {/* Root Cause Path */}
          <div>
            <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-3 font-semibold">Root Cause Chain</div>
            <div className="flex items-center gap-0 overflow-x-auto py-1">
              {rootCausePath.map((node, i) => (
                <div key={i} className="flex items-center flex-shrink-0">
                  <div className={`px-3 py-1.5 rounded-lg border text-xs font-medium whitespace-nowrap ${
                    i === 0 ? 'bg-blue-50 border-blue-200 text-blue-700' :
                    i === rootCausePath.length - 1 ? 'bg-red-50 border-red-200 text-red-700' :
                    'bg-amber-50 border-amber-200 text-amber-700'
                  }`}>
                    {node}
                  </div>
                  {i < rootCausePath.length - 1 && (
                    <ChevronRight className="w-4 h-4 text-slate-300 mx-0.5 flex-shrink-0" />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Reasoning */}
          <div>
            <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-2 font-semibold">Explanation</div>
            <div className="p-4 bg-slate-50 rounded-xl space-y-3">
              <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">
                <strong>Plain English:</strong>{' '}
                {link.easy_summary || `${link.cause.replace(/_/g, ' ')} likely led to ${link.effect.replace(/_/g, ' ')}`}.
              </p>
              <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">
                <strong>Technical:</strong>{' '}
                {link.reasoning || `Temporal ordering + repeated co‑occurrence indicate ${link.cause} consistently precedes ${link.effect} across recent cycles, suggesting a causal dependency rather than a coincidental correlation.`}
              </p>
              <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">
                <strong>Confidence:</strong> <code>{link.confidence}%</code>. Based on recurrence strength, ordering stability, and supporting evidence density.
              </p>
              <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">
                <strong>Alternates:</strong> {competingCauses === 0
                  ? `No competing causes are currently linked to "${link.effect}" in the active graph.`
                  : `${competingCauses} alternate cause link(s) also target "${link.effect}". Prioritize the most recent/highest‑confidence chain and validate against evidence IDs.`}
              </p>
              <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">
                <strong>Operational Note:</strong> Treat this as a ranked hypothesis; validate quickly using linked evidence before executing high‑risk mitigation steps.
              </p>
            </div>
          </div>

          <div>
            <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-2 font-semibold">Action Checklist</div>
            <div className="space-y-3">
              {[
                { title: 'Do now', items: checklist.do_now, bg: 'bg-red-50 border-red-100', text: 'text-red-900' },
                { title: 'Do next', items: checklist.do_next, bg: 'bg-amber-50 border-amber-100', text: 'text-amber-900' },
                { title: 'Verify', items: checklist.verify, bg: 'bg-emerald-50 border-emerald-100', text: 'text-emerald-900' },
              ].map((group) => (
                <div key={group.title} className={`p-4 rounded-xl border ${group.bg}`}>
                  <div className={`text-xs font-semibold uppercase tracking-wider mb-2 ${group.text}`}>{group.title}</div>
                  <div className="space-y-2">
                    {group.items.map((item, idx) => (
                      <div key={`${group.title}_${idx}`} className="text-sm leading-relaxed flex items-start gap-2">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${ownerStyles[item.owner] || 'bg-slate-100 text-slate-700'}`}>
                          {item.owner}
                        </span>
                        <span className={group.text}><strong>{idx + 1}.</strong> {item.action}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Agent & Timestamp */}
          <div className="flex gap-4">
            <div className="flex-1 p-3 bg-[var(--color-surface-tertiary)] rounded-xl flex items-center gap-3">
              <Activity className="w-5 h-5 text-indigo-500" />
              <div>
                <div className="text-[10px] text-[var(--color-text-muted)]">Agent</div>
                <div className="text-sm font-semibold">{link.agent}</div>
              </div>
            </div>
            <div className="flex-1 p-3 bg-[var(--color-surface-tertiary)] rounded-xl flex items-center gap-3">
              <Clock className="w-5 h-5 text-slate-500" />
              <div>
                <div className="text-[10px] text-[var(--color-text-muted)]">Updated</div>
                <div className="text-sm font-semibold">{formatTime(link.timestamp)}</div>
              </div>
            </div>
          </div>

          {/* Evidence */}
          {link.evidence_ids && link.evidence_ids.length > 0 && (
            <div>
              <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-2 font-semibold">Evidence</div>
              <div className="space-y-2">
                {link.evidence_ids.map((id) => (
                  <div key={id} className="flex items-center gap-3 p-2.5 rounded-lg border border-[var(--color-border)] hover:border-indigo-200 transition-colors cursor-pointer">
                    <FileText className="w-4 h-4 text-indigo-500" />
                    <code className="text-xs font-bold text-[var(--color-primary)]">{id}</code>
                    <span className="text-[10px] bg-slate-100 px-2 py-0.5 rounded-full font-medium text-[var(--color-text-muted)]">
                      {id.startsWith('evt_') ? 'EVENT' : id.startsWith('metric_') ? 'METRIC' : id.startsWith('v_') ? 'VIOLATION' : 'DATA'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="pt-4 border-t border-[var(--color-border)] space-y-3">
            <button className="btn btn-primary w-full" onClick={() => setShowSnapshot(true)}>
              <Camera className="w-4 h-4" />
              Extract Snapshot
            </button>
            <button className="btn btn-secondary w-full" onClick={() => onNavigate('/workflow-map')}>
              <ExternalLink className="w-4 h-4" />
              Jump to Workflow Timeline
            </button>
          </div>
        </div>
      </div>

      {/* Snapshot Modal */}
      {showSnapshot && (
        <SnapshotModal link={link} allLinks={allLinks} onClose={() => setShowSnapshot(false)} />
      )}
    </>
  );
}

export default function CausalAnalysisPage() {
  const router = useRouter();
  const [selectedLink, setSelectedLink] = useState<CausalLink | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>('all');

  const { data: links } = useQuery({
    queryKey: ['causalLinks'],
    queryFn: fetchCausalLinks,
    refetchInterval: 10000,
  });
  const { data: workflows } = useQuery({
    queryKey: ['workflows'],
    queryFn: fetchWorkflows,
    refetchInterval: 30000,
  });

  const displayLinks = useMemo(() => links || [], [links]);
  const workflowIds = useMemo(() => {
    const ids = new Set<string>();
    (workflows || []).forEach((w) => {
      if (w.workflow_id) ids.add(w.workflow_id);
    });
    const re = /wf_[a-zA-Z0-9_-]+/g;
    displayLinks.forEach((l) => {
      const inCause = l.cause.match(re) || [];
      const inEffect = l.effect.match(re) || [];
      inCause.concat(inEffect).forEach((id) => ids.add(id));
    });
    return Array.from(ids).sort();
  }, [displayLinks, workflows]);
  const effectiveWorkflow = useMemo(() => {
    if (selectedWorkflow === 'all') return 'all';
    return workflowIds.includes(selectedWorkflow) ? selectedWorkflow : 'all';
  }, [selectedWorkflow, workflowIds]);

  const filteredLinks = useMemo(() => {
    if (effectiveWorkflow === 'all') return displayLinks;
    return displayLinks.filter(
      (l) => l.cause.includes(effectiveWorkflow) || l.effect.includes(effectiveWorkflow)
    );
  }, [displayLinks, effectiveWorkflow]);

  // Summary stats
  const uniqueNodes = new Set(filteredLinks.flatMap(l => [l.cause, l.effect])).size;
  const avgConfidence = filteredLinks.length > 0 ? Math.round(filteredLinks.reduce((a, l) => a + l.confidence, 0) / filteredLinks.length) : 0;
  const highConfLinks = filteredLinks.filter(l => l.confidence >= 90).length;

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="icon-container icon-container-lg bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg">
            <GitMerge className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="page-title">Root Cause Explorer</h1>
            <p className="page-subtitle">Trace why issues happened and what they impacted</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Workflow</label>
          <select
            className="input w-[220px]"
            value={effectiveWorkflow}
            onChange={(e) => {
              setSelectedWorkflow(e.target.value);
              setSelectedLink(null);
            }}
          >
            <option value="all">All deployments</option>
            {workflowIds.map((id) => (
              <option key={id} value={id}>{id}</option>
            ))}
          </select>
        </div>
      </div>

      {/* How It Works */}
      <div className="p-5 bg-gradient-to-r from-indigo-50 via-violet-50 to-purple-50 rounded-2xl border border-indigo-100">
        <div className="flex items-start gap-4">
          <div className="icon-container icon-container-md bg-gradient-to-br from-indigo-500 to-violet-500 shadow-lg flex-shrink-0">
            <Info className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-semibold text-indigo-900 mb-1">How Causal Analysis Works</div>
            <p className="text-sm text-indigo-700 leading-relaxed">
              The <strong>Causal Agent</strong> correlates event ordering, dependency maps, and repeated signal patterns to infer cause → effect.
              Each link is scored for confidence and tied to evidence IDs so teams can validate quickly and respond safely.
            </p>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Causal Links</div>
              <div className="stats-value text-indigo-600">{filteredLinks.length}</div>
            </div>
            <div className="icon-container icon-container-md bg-indigo-100">
              <GitMerge className="w-5 h-5 text-indigo-600" />
            </div>
          </div>
        </div>
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Unique Nodes</div>
              <div className="stats-value text-violet-600">{uniqueNodes}</div>
            </div>
            <div className="icon-container icon-container-md bg-violet-100">
              <Network className="w-5 h-5 text-violet-600" />
            </div>
          </div>
        </div>
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Avg Confidence</div>
              <div className="stats-value" style={{ color: avgConfidence > 80 ? '#10b981' : '#f59e0b' }}>{avgConfidence}%</div>
            </div>
            <DonutChart value={avgConfidence} total={100} color={avgConfidence > 80 ? '#10b981' : '#f59e0b'} size={40} strokeWidth={4} />
          </div>
        </div>
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">High Confidence</div>
              <div className="stats-value text-emerald-600">{highConfLinks}</div>
            </div>
            <div className="icon-container icon-container-md bg-emerald-100">
              <TrendingUp className="w-5 h-5 text-emerald-600" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Causal Graph */}
        <div className="col-span-8">
          <div className="chart-container" style={{ height: '520px' }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="chart-title">Cause → Effect Graph</h3>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 text-[10px] text-[var(--color-text-muted)]">
                <span className="w-2 h-2 rounded-full bg-emerald-500" /> Resource
                <span className="w-2 h-2 rounded-full bg-indigo-500 ml-2" /> Workflow
                <span className="w-2 h-2 rounded-full bg-red-500 ml-2" /> Compliance
                <span className="w-2 h-2 rounded-full bg-amber-500 ml-2" /> Network
              </div>
              <span className="badge badge-info">{filteredLinks.length} links</span>
            </div>
          </div>
          <div className="h-[calc(100%-40px)]">
            <CausalGraph
              links={filteredLinks}
              selectedLink={selectedLink}
              onLinkSelect={setSelectedLink}
            />
          </div>
        </div>
      </div>

        {/* Link List */}
        <div className="col-span-4">
          <div className="card p-4 h-[520px] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-[var(--color-text-primary)]">Cause Links</h3>
              <span className="text-[10px] text-[var(--color-text-muted)]">Click to inspect</span>
            </div>
            <div className="flex-1 overflow-y-auto space-y-2.5">
              {filteredLinks.map((link, i) => (
                <CausalLinkCard
                  key={i}
                  link={link}
                  isSelected={selectedLink?.cause === link.cause && selectedLink?.effect === link.effect}
                  onClick={() => setSelectedLink(link)}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Detail Panel */}
      {selectedLink && (
        <InsightDetailPanel
          link={selectedLink}
          allLinks={filteredLinks}
          onClose={() => setSelectedLink(null)}
          onNavigate={(path) => { setSelectedLink(null); router.push(path); }}
        />
      )}

    </div>
  );
}
