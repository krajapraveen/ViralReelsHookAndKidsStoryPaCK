import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  Trophy, Star, Sparkles, ChevronRight, Gift, Film,
  BookOpen, Zap, X, ArrowRight
} from 'lucide-react';

const REWARD_ICONS = {
  unlock: Zap,
  bonus_credits: Gift,
  style: Star,
};

export function RewardModal({ reward, seriesId, onClaim, onDismiss, claiming }) {
  if (!reward) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" data-testid="reward-modal">
      <div className="w-full max-w-md mx-4 bg-slate-900 border border-slate-700/50 rounded-2xl overflow-hidden shadow-2xl">
        {/* Header glow */}
        <div className="relative bg-gradient-to-b from-amber-500/10 to-transparent pt-10 pb-6 px-6 text-center">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-40 h-20 bg-amber-500/20 rounded-full blur-[60px]" />
          <div className="relative">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-amber-500/30 to-amber-600/20 border-2 border-amber-500/40 mx-auto mb-4 flex items-center justify-center">
              <Trophy className="w-8 h-8 text-amber-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-1" data-testid="reward-title">
              {reward.title}
            </h2>
            <p className="text-sm text-amber-400 font-medium">{reward.subtitle}</p>
          </div>
        </div>

        {/* Emotional Message */}
        <div className="px-6 pb-4">
          <p className="text-sm text-slate-300 text-center leading-relaxed italic" data-testid="reward-message">
            "{reward.emotional_message}"
          </p>
        </div>

        {/* Rewards List */}
        <div className="px-6 pb-4 space-y-2">
          {reward.rewards?.map((r, i) => {
            const Icon = REWARD_ICONS[r.type] || Star;
            return (
              <div
                key={i}
                className="flex items-center gap-3 p-3 bg-slate-800/60 border border-slate-700/50 rounded-lg"
                data-testid={`reward-item-${i}`}
              >
                <div className="w-8 h-8 rounded-lg bg-amber-500/15 flex items-center justify-center flex-shrink-0">
                  <Icon className="w-4 h-4 text-amber-400" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{r.label}</p>
                  <p className="text-xs text-slate-400">{r.description}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Next Loop CTA */}
        {reward.next_loop && (
          <div className="px-6 pb-4">
            <div className="bg-gradient-to-r from-cyan-500/10 to-indigo-500/10 border border-cyan-500/20 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-400 mb-1">What's next?</p>
              <p className="text-sm font-semibold text-cyan-400" data-testid="next-loop-label">
                {reward.next_loop.label}
              </p>
              <p className="text-xs text-slate-500">{reward.next_loop.description}</p>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="px-6 pb-6 flex gap-3">
          <Button
            onClick={() => onClaim(reward.threshold)}
            disabled={claiming}
            className="flex-1 h-11 bg-amber-600 hover:bg-amber-700 text-white font-medium"
            data-testid="claim-reward-btn"
          >
            <Gift className="w-4 h-4 mr-2" />
            {claiming ? 'Claiming...' : 'Claim Reward'}
          </Button>
          <Button
            onClick={onDismiss}
            variant="ghost"
            className="text-slate-400 hover:text-white h-11"
            data-testid="dismiss-reward-btn"
          >
            Later
          </Button>
        </div>
      </div>
    </div>
  );
}


export function MilestoneProgress({ rewards, onViewReward }) {
  if (!rewards) return null;

  const { next_milestone, all_milestones, episode_count, pending_rewards } = rewards;

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4" data-testid="milestone-progress">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-white flex items-center gap-1.5">
          <Trophy className="w-3.5 h-3.5 text-amber-400" /> Story Milestones
        </h3>
        <span className="text-[10px] text-slate-500">{episode_count} episodes</span>
      </div>

      {/* Milestone dots */}
      <div className="flex items-center gap-1 mb-3">
        {all_milestones?.map((m, i) => (
          <React.Fragment key={m.threshold}>
            <div className="flex flex-col items-center">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold border-2 transition-all ${
                  m.claimed
                    ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                    : m.reached
                    ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400 animate-pulse'
                    : 'bg-slate-800 border-slate-700 text-slate-500'
                }`}
              >
                {m.claimed ? <Star className="w-3 h-3" /> : m.threshold}
              </div>
              <span className="text-[8px] text-slate-600 mt-0.5">{m.title.split(' ')[0]}</span>
            </div>
            {i < all_milestones.length - 1 && (
              <div className={`flex-1 h-0.5 ${m.reached ? 'bg-amber-500/40' : 'bg-slate-800'}`} />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Next milestone progress */}
      {next_milestone && (
        <div>
          <div className="flex items-center justify-between text-[10px] text-slate-500 mb-1">
            <span>Next: {next_milestone.title}</span>
            <span>{next_milestone.episodes_remaining} more episode{next_milestone.episodes_remaining !== 1 ? 's' : ''}</span>
          </div>
          <div className="w-full h-1.5 bg-slate-800 rounded-full">
            <div
              className="h-full bg-gradient-to-r from-amber-500 to-amber-400 rounded-full transition-all"
              style={{ width: `${next_milestone.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Pending rewards button */}
      {pending_rewards?.length > 0 && (
        <Button
          onClick={() => onViewReward(pending_rewards[0])}
          size="sm"
          className="w-full mt-3 bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 border border-amber-500/30 text-xs gap-1.5"
          data-testid="view-pending-reward-btn"
        >
          <Gift className="w-3 h-3" />
          {pending_rewards.length} reward{pending_rewards.length > 1 ? 's' : ''} waiting!
        </Button>
      )}
    </div>
  );
}
