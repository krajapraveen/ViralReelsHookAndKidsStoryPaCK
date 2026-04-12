import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trophy, Swords, TrendingDown, ArrowRight, Crown, GitBranch, Flame, Clock } from 'lucide-react';
import api from '../utils/api';

/**
 * PersonalAlertStrip — THE return trigger.
 * Shows rank changes, losses, and opportunities at the very top of the homepage.
 * "You lost something" > "Welcome back"
 */
export default function PersonalAlertStrip() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const collected = [];

        // 1. Check battle rank changes (unread notifications)
        const notifRes = await api.get('/api/stories/notifications/battle?limit=5');
        if (notifRes.data?.notifications) {
          for (const n of notifRes.data.notifications) {
            if (n.read) continue;
            if (n.type === 'rank_drop') {
              collected.push({
                type: 'rank_drop',
                icon: TrendingDown,
                color: 'border-rose-500/30 bg-rose-500/10',
                iconColor: 'text-rose-400 bg-rose-500/20',
                title: n.title,
                subtitle: n.message,
                cta: 'Take Back Rank',
                link: n.data?.deep_link || '/app/war',
                priority: 10,
              });
            } else if (n.type === 'version_outperformed') {
              collected.push({
                type: 'outperformed',
                icon: Swords,
                color: 'border-amber-500/30 bg-amber-500/10',
                iconColor: 'text-amber-400 bg-amber-500/20',
                title: n.title,
                subtitle: n.message,
                cta: 'Fight Back',
                link: n.data?.deep_link || '/app/war',
                priority: 8,
              });
            } else if (n.type === 'war_overtake') {
              collected.push({
                type: 'war_overtake',
                icon: Flame,
                color: 'border-rose-500/30 bg-rose-500/10',
                iconColor: 'text-rose-400 bg-rose-500/20',
                title: n.title,
                subtitle: n.message,
                cta: 'Fight Back',
                link: n.data?.deep_link || '/app/war',
                priority: 12,
              });
            } else if (n.type === 'war_won') {
              collected.push({
                type: 'war_won',
                icon: Crown,
                color: 'border-amber-500/30 bg-amber-500/10',
                iconColor: 'text-amber-400 bg-amber-500/20',
                title: n.title,
                subtitle: n.message,
                cta: 'View Win',
                link: n.data?.deep_link || '/app/war',
                priority: 6,
              });
            }
          }
        }

        // 2. Check active war position
        try {
          const warRes = await api.get('/api/war/current');
          if (warRes.data?.war?.state === 'active' && warRes.data.leaderboard?.user_rank) {
            const rank = warRes.data.leaderboard.user_rank;
            const entry = warRes.data.leaderboard.user_entry;
            const timeLeft = warRes.data.war.time_left_seconds || 0;
            const hoursLeft = Math.floor(timeLeft / 3600);
            if (rank > 1) {
              collected.push({
                type: 'war_losing',
                icon: Clock,
                color: 'border-orange-500/30 bg-orange-500/10',
                iconColor: 'text-orange-400 bg-orange-500/20',
                title: `You're #${rank} in today's Story War`,
                subtitle: `Gap to #1: ${entry?.gap_score || '?'} pts. ${hoursLeft}h left.`,
                cta: 'Enter War',
                link: '/app/war',
                priority: 9,
              });
            }
          }
        } catch {}

        // 3. Check stories being overtaken
        try {
          const discoverRes = await api.get('/api/stories/feed/trending?limit=3');
          const trending = discoverRes.data?.stories || [];
          if (trending.length > 0 && !collected.some(a => a.type === 'rank_drop')) {
            const top = trending[0];
            collected.push({
              type: 'trending_opportunity',
              icon: Flame,
              color: 'border-violet-500/20 bg-violet-500/[0.06]',
              iconColor: 'text-violet-400 bg-violet-500/20',
              title: `"${top.title}" is exploding`,
              subtitle: `${top.total_views || 0} views, ${top.total_children || 0} continues — can you beat it?`,
              cta: 'Compete',
              link: `/app/story-battle/${top.root_story_id || top.job_id}`,
              priority: 3,
            });
          }
        } catch {}

        // Sort by priority (highest first) and take top 2
        collected.sort((a, b) => b.priority - a.priority);
        setAlerts(collected.slice(0, 2));
      } catch {}
      finally { setLoading(false); }
    })();
  }, []);

  if (loading || alerts.length === 0) return null;

  return (
    <div className="px-4 sm:px-6 lg:px-10 py-2 space-y-2" data-testid="personal-alert-strip">
      {alerts.map((alert, i) => {
        const Icon = alert.icon;
        return (
          <button
            key={`${alert.type}-${i}`}
            onClick={() => navigate(alert.link)}
            className={`w-full rounded-xl border p-3.5 flex items-center gap-3 transition-all hover:scale-[1.005] text-left ${alert.color}`}
            data-testid={`alert-${alert.type}`}
          >
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${alert.iconColor}`}>
              <Icon className="w-4.5 h-4.5" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-white truncate">{alert.title}</p>
              <p className="text-xs text-white/40 truncate">{alert.subtitle}</p>
            </div>
            <div className="flex-shrink-0 flex items-center gap-1.5 text-xs font-bold text-white/80 bg-white/10 rounded-lg px-3 py-1.5 hover:bg-white/15 transition-colors">
              {alert.cta} <ArrowRight className="w-3 h-3" />
            </div>
          </button>
        );
      })}
    </div>
  );
}
