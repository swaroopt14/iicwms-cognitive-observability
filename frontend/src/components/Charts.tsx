'use client';

import { useEffect, useRef, useState } from 'react';
import type { RiskDataPoint } from '@/lib/api';

// Utility function for smooth bezier curves
function drawSmoothLine(
  ctx: CanvasRenderingContext2D,
  points: { x: number; y: number }[],
  tension = 0.3
) {
  if (points.length < 2) return;

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);

  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i === 0 ? i : i - 1];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2 >= points.length ? i + 1 : i + 2];

    const cp1x = p1.x + (p2.x - p0.x) * tension;
    const cp1y = p1.y + (p2.y - p0.y) * tension;
    const cp2x = p2.x - (p3.x - p1.x) * tension;
    const cp2y = p2.y - (p3.y - p1.y) * tension;

    ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y);
  }
}

// ============================================
// Area Chart Component
// ============================================
interface AreaChartProps {
  data: number[];
  color?: string;
  gradientFrom?: string;
  gradientTo?: string;
  height?: number;
  showGrid?: boolean;
  showDots?: boolean;
  showLabels?: boolean;
  xLabels?: string[];
  xAxisLabel?: string;
  yAxisLabel?: string;
  yFormatter?: (value: number) => string;
  animated?: boolean;
}

export function AreaChart({
  data,
  color = '#6366f1',
  gradientFrom = 'rgba(99, 102, 241, 0.3)',
  gradientTo = 'rgba(99, 102, 241, 0)',
  height = 160,
  showGrid = true,
  showDots = true,
  showLabels = false,
  xLabels,
  xAxisLabel = 'Time',
  yAxisLabel = 'Value',
  yFormatter,
  animated = true,
}: AreaChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [progress, setProgress] = useState(animated ? 0 : 1);

  useEffect(() => {
    if (animated) {
      let start: number;
      const duration = 1000;
      
      const animate = (timestamp: number) => {
        if (!start) start = timestamp;
        const elapsed = timestamp - start;
        const newProgress = Math.min(elapsed / duration, 1);
        setProgress(newProgress);
        
        if (newProgress < 1) {
          requestAnimationFrame(animate);
        }
      };
      
      requestAnimationFrame(animate);
    }
  }, [animated, data]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const chartHeight = rect.height;
    const padding = { top: 10, right: 10, bottom: showLabels ? 25 : 10, left: showLabels ? 35 : 10 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = chartHeight - padding.top - padding.bottom;

    ctx.clearRect(0, 0, width, chartHeight);

    if (data.length === 0 || plotWidth <= 0 || plotHeight <= 0) return;

    const rawMax = Math.max(...data);
    const rawMin = Math.min(...data);
    const maxVal = rawMax * 1.1 || 1;
    const minVal = rawMin * 0.9;
    const range = maxVal - minVal || 1;

    // Draw grid
    if (showGrid) {
      ctx.strokeStyle = '#f1f5f9';
      ctx.lineWidth = 1;
      
      // Horizontal lines
      for (let i = 0; i <= 4; i++) {
        const y = padding.top + (plotHeight / 4) * i;
        ctx.beginPath();
        ctx.setLineDash([4, 4]);
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
        ctx.setLineDash([]);
        
        if (showLabels) {
          ctx.fillStyle = '#94a3b8';
          ctx.font = '10px Inter, system-ui';
          ctx.textAlign = 'right';
          const value = maxVal - (range / 4) * i;
          const label = yFormatter ? yFormatter(value) : value.toFixed(0);
          ctx.fillText(label, padding.left - 5, y + 3);
        }
      }
    }

    if (showLabels) {
      // Axis lines
      ctx.strokeStyle = '#cbd5e1';
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(padding.left, padding.top);
      ctx.lineTo(padding.left, chartHeight - padding.bottom);
      ctx.lineTo(width - padding.right, chartHeight - padding.bottom);
      ctx.stroke();
    }

    // Calculate points
    const visibleDataCount = Math.ceil(data.length * progress);
    const points: { x: number; y: number }[] = [];
    
    const minY = padding.top;
    const maxY = padding.top + plotHeight;
    for (let i = 0; i < visibleDataCount; i++) {
      const x = padding.left + (plotWidth / (data.length - 1)) * i;
      const rawY = padding.top + plotHeight - ((data[i] - minVal) / range) * plotHeight;
      const y = Math.max(minY, Math.min(maxY, rawY));
      points.push({ x, y });
    }

    if (points.length < 2) return;

    // Clip plotting to chart area so curves never overflow below X-axis.
    ctx.save();
    ctx.beginPath();
    ctx.rect(padding.left, padding.top, plotWidth, plotHeight);
    ctx.clip();

    // Draw gradient fill
    const gradient = ctx.createLinearGradient(0, padding.top, 0, chartHeight - padding.bottom);
    gradient.addColorStop(0, gradientFrom);
    gradient.addColorStop(1, gradientTo);

    ctx.beginPath();
    ctx.moveTo(points[0].x, chartHeight - padding.bottom);
    drawSmoothLine(ctx, points);
    ctx.lineTo(points[points.length - 1].x, chartHeight - padding.bottom);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Draw line
    ctx.beginPath();
    drawSmoothLine(ctx, points);
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.stroke();

    ctx.restore();

    // Draw dots
    if (showDots && progress === 1) {
      points.forEach((point, i) => {
        // Outer glow
        ctx.beginPath();
        ctx.arc(point.x, point.y, 6, 0, Math.PI * 2);
        ctx.fillStyle = `${color}20`;
        ctx.fill();
        
        // Dot
        ctx.beginPath();
        ctx.arc(point.x, point.y, 3, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = 'white';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      });

      // Highlight last point
      const lastPoint = points[points.length - 1];
      ctx.beginPath();
      ctx.arc(lastPoint.x, lastPoint.y, 8, 0, Math.PI * 2);
      ctx.fillStyle = `${color}30`;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(lastPoint.x, lastPoint.y, 5, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = 'white';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    if (showLabels) {
      // X-axis labels
      ctx.fillStyle = '#94a3b8';
      ctx.font = '10px Inter, system-ui';
      ctx.textAlign = 'center';
      const labelInterval = Math.max(1, Math.ceil(data.length / 6));
      for (let i = 0; i < data.length; i++) {
        if (i % labelInterval !== 0 && i !== data.length - 1) continue;
        const x = padding.left + (plotWidth / Math.max(data.length - 1, 1)) * i;
        const label = xLabels?.[i] ?? `${i + 1}`;
        ctx.fillText(label, x, chartHeight - 10);
      }

      // Axis titles
      ctx.fillStyle = '#64748b';
      ctx.font = '11px Inter, system-ui';
      ctx.textAlign = 'center';
      ctx.fillText(xAxisLabel, padding.left + plotWidth / 2, chartHeight - 2);

      ctx.save();
      ctx.translate(12, padding.top + plotHeight / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText(yAxisLabel, 0, 0);
      ctx.restore();
    }
  }, [
    data,
    color,
    gradientFrom,
    gradientTo,
    showGrid,
    showDots,
    showLabels,
    xLabels,
    xAxisLabel,
    yAxisLabel,
    yFormatter,
    progress,
  ]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: '100%', height }}
      className="w-full"
    />
  );
}

// ============================================
// Bar Chart Component
// ============================================
interface BarChartProps {
  data: number[];
  colors?: string[];
  height?: number;
  showGrid?: boolean;
  showAxes?: boolean;
  xLabels?: string[];
  xAxisLabel?: string;
  yAxisLabel?: string;
  yTickCount?: number;
  yFormatter?: (value: number) => string;
  barRadius?: number;
  animated?: boolean;
  highlightThreshold?: number;
  highlightColor?: string;
}

export function BarChart({
  data,
  colors = ['#6366f1', '#818cf8'],
  height = 160,
  showGrid = true,
  showAxes = true,
  xLabels,
  xAxisLabel = 'Categories',
  yAxisLabel = 'Value',
  yTickCount = 4,
  yFormatter,
  barRadius = 6,
  animated = true,
  highlightThreshold,
  highlightColor = '#f59e0b',
}: BarChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [progress, setProgress] = useState(animated ? 0 : 1);

  useEffect(() => {
    if (animated) {
      let start: number;
      const duration = 800;
      
      const animate = (timestamp: number) => {
        if (!start) start = timestamp;
        const elapsed = timestamp - start;
        const newProgress = Math.min(elapsed / duration, 1);
        // Ease out cubic
        setProgress(1 - Math.pow(1 - newProgress, 3));
        
        if (newProgress < 1) {
          requestAnimationFrame(animate);
        }
      };
      
      requestAnimationFrame(animate);
    }
  }, [animated, data]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const chartHeight = rect.height;
    const padding = showAxes
      ? { top: 10, right: 12, bottom: 38, left: 46 }
      : { top: 10, right: 10, bottom: 10, left: 10 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = chartHeight - padding.top - padding.bottom;

    ctx.clearRect(0, 0, width, chartHeight);

    if (data.length === 0 || plotWidth <= 0 || plotHeight <= 0) return;

    const maxRaw = Math.max(...data);
    const maxVal = maxRaw > 0 ? maxRaw * 1.15 : 1;
    const groups = Math.max(1, data.length);
    const groupWidth = plotWidth / groups;
    const barWidth = Math.max(6, Math.min(48, groupWidth * 0.64));
    const tickCount = Math.max(2, yTickCount);

    // Draw grid
    if (showGrid) {
      ctx.strokeStyle = '#f1f5f9';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      
      for (let i = 0; i <= tickCount; i++) {
        const y = padding.top + (plotHeight / tickCount) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();

        if (showAxes) {
          const value = maxVal - (maxVal / tickCount) * i;
          ctx.fillStyle = '#64748b';
          ctx.font = '10px ui-sans-serif, system-ui, -apple-system, Segoe UI';
          ctx.textAlign = 'right';
          ctx.textBaseline = 'middle';
          const label = yFormatter ? yFormatter(value) : value.toFixed(0);
          ctx.fillText(label, padding.left - 8, y);
        }
      }
      ctx.setLineDash([]);
    }

    if (showAxes) {
      // Axis lines
      ctx.strokeStyle = '#cbd5e1';
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(padding.left, padding.top);
      ctx.lineTo(padding.left, chartHeight - padding.bottom);
      ctx.lineTo(width - padding.right, chartHeight - padding.bottom);
      ctx.stroke();

      // Axis labels
      ctx.fillStyle = '#64748b';
      ctx.font = '11px ui-sans-serif, system-ui, -apple-system, Segoe UI';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'alphabetic';
      ctx.fillText(xAxisLabel, padding.left + plotWidth / 2, chartHeight - 6);

      ctx.save();
      ctx.translate(14, padding.top + plotHeight / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(yAxisLabel, 0, 0);
      ctx.restore();
    }

    // Draw bars
    data.forEach((value, i) => {
      const barHeight = (value / maxVal) * plotHeight * progress;
      const x = padding.left + i * groupWidth + (groupWidth - barWidth) / 2;
      const y = chartHeight - padding.bottom - barHeight;

      // Create gradient for bar
      const gradient = ctx.createLinearGradient(x, y, x, chartHeight - padding.bottom);
      
      const isHighlighted = highlightThreshold && value > highlightThreshold;
      if (isHighlighted) {
        gradient.addColorStop(0, highlightColor);
        gradient.addColorStop(1, `${highlightColor}80`);
      } else {
        gradient.addColorStop(0, colors[0]);
        gradient.addColorStop(1, colors[1] || colors[0]);
      }

      // Draw bar with rounded top
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, barHeight, [barRadius, barRadius, 0, 0]);
      ctx.fillStyle = gradient;
      ctx.fill();

      // Add subtle shadow
      ctx.shadowColor = isHighlighted ? `${highlightColor}40` : `${colors[0]}40`;
      ctx.shadowBlur = 8;
      ctx.shadowOffsetY = 4;
      ctx.fill();
      ctx.shadowColor = 'transparent';
      ctx.shadowBlur = 0;
      ctx.shadowOffsetY = 0;

      // X labels
      if (showAxes) {
        const label = (xLabels && xLabels[i]) ? xLabels[i] : String(i + 1);
        ctx.fillStyle = '#64748b';
        ctx.font = '10px ui-sans-serif, system-ui, -apple-system, Segoe UI';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(label, x + barWidth / 2, chartHeight - padding.bottom + 6);
      }
    });
  }, [
    data,
    colors,
    showGrid,
    showAxes,
    xLabels,
    xAxisLabel,
    yAxisLabel,
    yTickCount,
    yFormatter,
    barRadius,
    progress,
    highlightThreshold,
    highlightColor,
  ]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: '100%', height }}
      className="w-full"
    />
  );
}

// ============================================
// Risk Index Graph Component
// ============================================
interface RiskGraphProps {
  data: RiskDataPoint[];
  height?: number;
  showZones?: boolean;
  onPointHover?: (point: RiskDataPoint | null, x: number, y: number) => void;
}

export function RiskGraph({
  data,
  height = 200,
  showZones = true,
  onPointHover,
}: RiskGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const chartHeight = rect.height;
    const padding = { top: 20, right: 20, bottom: 30, left: 45 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = chartHeight - padding.top - padding.bottom;

    ctx.clearRect(0, 0, width, chartHeight);

    if (plotWidth <= 0 || plotHeight <= 0) return;

    // Draw risk zones
    if (showZones) {
      const zones = [
        { start: 0, end: 30, color1: 'rgba(16, 185, 129, 0.08)', color2: 'rgba(16, 185, 129, 0.02)', label: 'Normal' },
        { start: 30, end: 50, color1: 'rgba(245, 158, 11, 0.08)', color2: 'rgba(245, 158, 11, 0.02)', label: 'Degraded' },
        { start: 50, end: 70, color1: 'rgba(249, 115, 22, 0.08)', color2: 'rgba(249, 115, 22, 0.02)', label: 'At Risk' },
        { start: 70, end: 100, color1: 'rgba(239, 68, 68, 0.08)', color2: 'rgba(239, 68, 68, 0.02)', label: 'Critical' },
      ];

      zones.forEach((zone) => {
        const y1 = padding.top + plotHeight - (zone.end / 100) * plotHeight;
        const y2 = padding.top + plotHeight - (zone.start / 100) * plotHeight;
        const gradient = ctx.createLinearGradient(0, y1, 0, y2);
        gradient.addColorStop(0, zone.color1);
        gradient.addColorStop(1, zone.color2);
        ctx.fillStyle = gradient;
        ctx.fillRect(padding.left, y1, plotWidth, y2 - y1);
      });
    }

    // Draw grid
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (plotHeight / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();

      // Y-axis labels
      ctx.fillStyle = '#64748b';
      ctx.font = '11px Inter, system-ui';
      ctx.textAlign = 'right';
      ctx.fillText(String(100 - i * 25), padding.left - 8, y + 4);
    }
    ctx.setLineDash([]);

    if (data.length === 0) {
      ctx.fillStyle = '#94a3b8';
      ctx.font = '14px Inter, system-ui';
      ctx.textAlign = 'center';
      ctx.fillText('No data available', width / 2, chartHeight / 2);
      return;
    }

    // Calculate points
    const points: { x: number; y: number; data: RiskDataPoint }[] = data.map((d, i) => ({
      x: padding.left + (plotWidth / (data.length - 1 || 1)) * i,
      y: padding.top + plotHeight - (d.risk_score / 100) * plotHeight,
      data: d,
    }));

    // Draw gradient fill
    const gradient = ctx.createLinearGradient(0, padding.top, 0, chartHeight - padding.bottom);
    gradient.addColorStop(0, 'rgba(99, 102, 241, 0.2)');
    gradient.addColorStop(1, 'rgba(99, 102, 241, 0)');

    ctx.beginPath();
    ctx.moveTo(points[0].x, chartHeight - padding.bottom);
    points.forEach((p) => ctx.lineTo(p.x, p.y));
    ctx.lineTo(points[points.length - 1].x, chartHeight - padding.bottom);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Draw line with gradient stroke
    const lineGradient = ctx.createLinearGradient(0, 0, width, 0);
    lineGradient.addColorStop(0, '#6366f1');
    lineGradient.addColorStop(0.5, '#8b5cf6');
    lineGradient.addColorStop(1, '#6366f1');

    ctx.beginPath();
    points.forEach((p, i) => {
      if (i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.strokeStyle = lineGradient;
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.stroke();

    // Draw points
    points.forEach((p, i) => {
      const isHovered = hoveredIndex === i;
      const color = p.data.risk_score > 70 ? '#ef4444' : 
                    p.data.risk_score > 50 ? '#f97316' :
                    p.data.risk_score > 30 ? '#f59e0b' : '#10b981';

      // Glow effect
      if (isHovered) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 16, 0, Math.PI * 2);
        ctx.fillStyle = `${color}20`;
        ctx.fill();
      }

      // Outer ring
      ctx.beginPath();
      ctx.arc(p.x, p.y, isHovered ? 10 : 6, 0, Math.PI * 2);
      ctx.fillStyle = `${color}30`;
      ctx.fill();

      // Inner dot
      ctx.beginPath();
      ctx.arc(p.x, p.y, isHovered ? 6 : 4, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = 'white';
      ctx.lineWidth = 2;
      ctx.stroke();
    });

    // X-axis time labels
    ctx.fillStyle = '#64748b';
    ctx.font = '10px Inter, system-ui';
    ctx.textAlign = 'center';
    const labelInterval = Math.max(1, Math.ceil(data.length / 6));
    data.forEach((d, i) => {
      if (i % labelInterval === 0 || i === data.length - 1) {
        const x = padding.left + (plotWidth / (data.length - 1 || 1)) * i;
        const time = new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        ctx.fillText(time, x, chartHeight - 8);
      }
    });
  }, [data, showZones, hoveredIndex]);

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || data.length === 0) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const padding = { left: 45, right: 20 };
    const plotWidth = rect.width - padding.left - padding.right;

    // Find closest point
    let closestIndex = -1;
    let closestDist = Infinity;

    data.forEach((_, i) => {
      const px = padding.left + (plotWidth / (data.length - 1 || 1)) * i;
      const dist = Math.abs(x - px);
      if (dist < 30 && dist < closestDist) {
        closestDist = dist;
        closestIndex = i;
      }
    });

    setHoveredIndex(closestIndex !== -1 ? closestIndex : null);
    if (onPointHover && closestIndex !== -1) {
      onPointHover(data[closestIndex], e.clientX, e.clientY);
    } else if (onPointHover) {
      onPointHover(null, 0, 0);
    }
  };

  return (
    <canvas
      ref={canvasRef}
      style={{ width: '100%', height }}
      className="w-full cursor-crosshair"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => {
        setHoveredIndex(null);
        onPointHover?.(null, 0, 0);
      }}
    />
  );
}

// ============================================
// Donut Chart Component
// ============================================
interface DonutChartProps {
  value: number;
  total: number;
  color?: string;
  size?: number;
  strokeWidth?: number;
  showLabel?: boolean;
  animated?: boolean;
}

export function DonutChart({
  value,
  total,
  color = '#6366f1',
  size = 80,
  strokeWidth = 8,
  showLabel = true,
  animated = true,
}: DonutChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [progress, setProgress] = useState(animated ? 0 : 1);

  useEffect(() => {
    if (animated) {
      let start: number;
      const duration = 1000;
      
      const animate = (timestamp: number) => {
        if (!start) start = timestamp;
        const elapsed = timestamp - start;
        const newProgress = Math.min(elapsed / duration, 1);
        // Ease out cubic
        setProgress(1 - Math.pow(1 - newProgress, 3));
        
        if (newProgress < 1) {
          requestAnimationFrame(animate);
        }
      };
      
      requestAnimationFrame(animate);
    }
  }, [animated, value]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    const center = size / 2;
    const radius = (size - strokeWidth) / 2;
    const percentage = (value / total) * progress;

    ctx.clearRect(0, 0, size, size);

    // Background circle
    ctx.beginPath();
    ctx.arc(center, center, radius, 0, Math.PI * 2);
    ctx.strokeStyle = '#f1f5f9';
    ctx.lineWidth = strokeWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Progress arc with gradient
    const gradient = ctx.createLinearGradient(0, 0, size, size);
    gradient.addColorStop(0, color);
    gradient.addColorStop(1, `${color}cc`);

    ctx.beginPath();
    ctx.arc(center, center, radius, -Math.PI / 2, -Math.PI / 2 + percentage * Math.PI * 2);
    ctx.strokeStyle = gradient;
    ctx.lineWidth = strokeWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Center text
    if (showLabel) {
      ctx.fillStyle = '#1e293b';
      ctx.font = `bold ${size / 3.5}px Inter, system-ui`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(String(Math.round(value * progress)), center, center);
    }
  }, [value, total, color, size, strokeWidth, showLabel, progress]);

  return (
    <canvas
      ref={canvasRef}
      width={size}
      height={size}
      style={{ width: size, height: size }}
    />
  );
}

// ============================================
// Sparkline Component
// ============================================
interface SparklineProps {
  data: number[];
  color?: string;
  width?: number;
  height?: number;
}

export function Sparkline({
  data,
  color = '#6366f1',
  width = 100,
  height = 32,
}: SparklineProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length < 2) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, width, height);

    const padding = 2;
    const maxVal = Math.max(...data);
    const minVal = Math.min(...data);
    const range = maxVal - minVal || 1;

    const points = data.map((v, i) => ({
      x: padding + ((width - padding * 2) / (data.length - 1)) * i,
      y: padding + (height - padding * 2) - ((v - minVal) / range) * (height - padding * 2),
    }));

    // Gradient fill
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, `${color}30`);
    gradient.addColorStop(1, `${color}00`);

    ctx.beginPath();
    ctx.moveTo(points[0].x, height);
    points.forEach((p) => ctx.lineTo(p.x, p.y));
    ctx.lineTo(points[points.length - 1].x, height);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Line
    ctx.beginPath();
    points.forEach((p, i) => {
      if (i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.lineCap = 'round';
    ctx.stroke();

    // End dot
    const last = points[points.length - 1];
    ctx.beginPath();
    ctx.arc(last.x, last.y, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
  }, [data, color, width, height]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{ width, height }}
    />
  );
}

// ============================================
// Multi-Line Chart Component
// ============================================
interface MultiLineDataset {
  data: number[];
  color: string;
  label: string;
}

interface MultiLineChartProps {
  datasets: MultiLineDataset[];
  height?: number;
  showLegend?: boolean;
}

export function MultiLineChart({
  datasets,
  height = 200,
  showLegend = true,
}: MultiLineChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || datasets.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const chartHeight = rect.height;
    const padding = { top: 10, right: 10, bottom: showLegend ? 40 : 10, left: 40 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = chartHeight - padding.top - padding.bottom;

    ctx.clearRect(0, 0, width, chartHeight);

    if (plotWidth <= 0 || plotHeight <= 0) return;

    // Find global max
    const allData = datasets.flatMap((d) => d.data);
    const maxVal = Math.max(...allData) * 1.1 || 1;
    const dataLength = Math.max(...datasets.map((d) => d.data.length));

    // Draw grid
    ctx.strokeStyle = '#f1f5f9';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (plotHeight / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();

      ctx.fillStyle = '#94a3b8';
      ctx.font = '10px Inter, system-ui';
      ctx.textAlign = 'right';
      const value = maxVal - (maxVal / 4) * i;
      ctx.fillText(value.toFixed(0), padding.left - 5, y + 3);
    }
    ctx.setLineDash([]);

    // Draw each dataset
    datasets.forEach((dataset) => {
      const points = dataset.data.map((v, i) => ({
        x: padding.left + (plotWidth / (dataLength - 1 || 1)) * i,
        y: padding.top + plotHeight - (v / maxVal) * plotHeight,
      }));

      // Line
      ctx.beginPath();
      points.forEach((p, i) => {
        if (i === 0) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
      });
      ctx.strokeStyle = dataset.color;
      ctx.lineWidth = 2;
      ctx.lineCap = 'round';
      ctx.stroke();
    });

    // Draw legend
    if (showLegend) {
      const legendY = chartHeight - 20;
      let legendX = padding.left;
      
      datasets.forEach((dataset) => {
        ctx.fillStyle = dataset.color;
        ctx.beginPath();
        ctx.arc(legendX + 6, legendY, 4, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.fillStyle = '#64748b';
        ctx.font = '11px Inter, system-ui';
        ctx.textAlign = 'left';
        ctx.fillText(dataset.label, legendX + 14, legendY + 4);
        
        legendX += ctx.measureText(dataset.label).width + 30;
      });
    }
  }, [datasets, showLegend]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: '100%', height }}
      className="w-full"
    />
  );
}
