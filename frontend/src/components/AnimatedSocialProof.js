import React, { useState, useEffect, useRef } from 'react';
import { Eye } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

export function AnimatedViewerCount({ className = '' }) {
  const [viewers, setViewers] = useState(null);
  const [label, setLabel] = useState(null);
  const [show, setShow] = useState(false);
  const [displayCount, setDisplayCount] = useState(0);
  const animRef = useRef(null);

  useEffect(() => {
    const fetchViewers = async () => {
      try {
        const res = await axios.get(`${API}/api/compete/live-viewers`);
        if (res.data.success) {
          setViewers(res.data.viewers);
          setLabel(res.data.label);
          setShow(res.data.show);
        }
      } catch {}
    };

    fetchViewers();
    const interval = setInterval(fetchViewers, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  // Animate count changes
  useEffect(() => {
    if (viewers === null) return;
    const start = displayCount;
    const end = viewers;
    if (start === end) return;

    const duration = 600;
    const startTime = Date.now();

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayCount(Math.round(start + (end - start) * eased));

      if (progress < 1) {
        animRef.current = requestAnimationFrame(animate);
      }
    };

    animRef.current = requestAnimationFrame(animate);
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [viewers]);

  if (!show) return null;

  return (
    <div
      className={`inline-flex items-center gap-1.5 ${className}`}
      data-testid="animated-viewer-count"
    >
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
      </span>
      <Eye className="w-3.5 h-3.5 text-emerald-400" />
      <span className="text-xs font-semibold text-emerald-400" data-testid="viewer-count-number">
        {label || `${displayCount} viewing`}
      </span>
    </div>
  );
}

/* Inline version for cards/pages */
export function LiveViewerBadge({ className = '' }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await axios.get(`${API}/api/compete/live-viewers`);
        if (res.data.success && res.data.show) setData(res.data);
      } catch {}
    })();
  }, []);

  if (!data) return null;

  return (
    <div
      className={`flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full ${className}`}
      data-testid="live-viewer-badge"
    >
      <span className="relative flex h-1.5 w-1.5">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
      </span>
      {data.label}
    </div>
  );
}
