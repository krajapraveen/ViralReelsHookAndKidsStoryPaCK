import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Swords, Clock, Trophy, ArrowRight } from 'lucide-react';
import api from '../utils/api';

/**
 * WarBanner — Homepage banner for the Daily Story War.
 * Shows countdown, entry count, and CTA.
 */
export default function WarBanner() {
  const navigate = useNavigate();
  const [war, setWar] = useState(null);
  const [timeLeft, setTimeLeft] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/api/war/current');
        if (res.data?.success && res.data.war) {
          setWar(res.data.war);
          setTimeLeft(res.data.war.time_left_seconds || 0);
        }
      } catch {}
    })();
  }, []);

  useEffect(() => {
    if (timeLeft <= 0) return;
    const iv = setInterval(() => setTimeLeft(t => Math.max(0, t - 1)), 1000);
    return () => clearInterval(iv);
  }, [timeLeft]);

  if (!war || war.state === 'scheduled') return null;

  const isActive = war.state === 'active';
  const h = Math.floor(timeLeft / 3600);
  const m = Math.floor((timeLeft % 3600) / 60);
  const s = timeLeft % 60;
  const pad = (n) => String(n).padStart(2, '0');

  return (
    <div
      className="relative overflow-hidden rounded-2xl border border-rose-500/20 bg-gradient-to-r from-rose-600/10 via-orange-600/5 to-rose-600/10 p-5 cursor-pointer group hover:border-rose-500/40 transition-all"
      onClick={() => navigate('/app/war')}
      data-testid="war-banner"
    >
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-xl bg-rose-500/20 flex items-center justify-center flex-shrink-0 group-hover:bg-rose-500/30 transition-colors">
          <Swords className="w-6 h-6 text-rose-400" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-bold text-rose-400 uppercase tracking-wider">Daily Story War</span>
            {isActive && (
              <span className="text-[10px] bg-rose-500/20 text-rose-300 rounded-full px-2 py-0.5 font-semibold">
                LIVE
              </span>
            )}
          </div>
          <p className="text-sm font-bold text-white truncate">
            {war.root_title || '1 Story. 24 Hours. 1 Winner.'}
          </p>
          <div className="flex items-center gap-3 mt-1.5">
            {isActive && timeLeft > 0 && (
              <span className="flex items-center gap-1 text-xs text-white/50">
                <Clock className="w-3 h-3" />
                <span className="font-mono font-semibold">{pad(h)}:{pad(m)}:{pad(s)}</span>
              </span>
            )}
            <span className="text-xs text-white/30">
              {war.total_entries || 0} competing
            </span>
            {war.winner_title && !isActive && (
              <span className="flex items-center gap-1 text-xs text-amber-400">
                <Trophy className="w-3 h-3" /> {war.winner_creator_name}
              </span>
            )}
          </div>
        </div>

        <div className="flex-shrink-0">
          <div className="w-10 h-10 rounded-xl bg-rose-500/10 flex items-center justify-center group-hover:bg-rose-500/20 transition-colors">
            <ArrowRight className="w-5 h-5 text-rose-400 group-hover:translate-x-0.5 transition-transform" />
          </div>
        </div>
      </div>
    </div>
  );
}
