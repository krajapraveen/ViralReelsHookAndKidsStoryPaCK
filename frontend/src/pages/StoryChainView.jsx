import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, BookOpen, RefreshCw, Sparkles, Loader2,
  ChevronRight, Coins, Clock, Palette, GitBranch
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

export default function StoryChainView() {
  const { chainId } = useParams();
  const navigate = useNavigate();
  const [chain, setChain] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!chainId) return;
    (async () => {
      try {
        const res = await api.get(`/api/photo-to-comic/chain/${chainId}`);
        setChain(res.data);
      } catch {
        toast.error('Chain not found');
        navigate('/app/my-stories');
      } finally {
        setLoading(false);
      }
    })();
  }, [chainId, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  if (!chain) return null;

  const { flat = [], tree, total_episodes, continuations, remixes, styles_used } = chain;

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/app/my-stories">
              <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white px-2">
                <ArrowLeft className="w-4 h-4" />
              </Button>
            </Link>
            <div>
              <h1 className="text-base font-bold text-white flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-purple-400" /> Story Chain
              </h1>
              <p className="text-[10px] text-slate-500">
                {total_episodes} episode{total_episodes !== 1 ? 's' : ''} &middot; {continuations} continuation{continuations !== 1 ? 's' : ''} &middot; {remixes} remix{remixes !== 1 ? 'es' : ''}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {styles_used?.map(s => (
              <span key={s} className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full">{s}</span>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-6" data-testid="story-chain-view">
        {/* Chain timeline */}
        <div className="relative" data-testid="chain-timeline">
          {flat.map((job, idx) => {
            const isRoot = job.branch_type === 'original';
            const isContinuation = job.branch_type === 'continuation';
            const isRemix = job.branch_type === 'remix';
            const imageUrl = job.resultUrl || job.resultUrls?.[0] || job.panels?.[0]?.imageUrl;
            const isCompleted = job.status === 'COMPLETED' || job.status === 'PARTIAL_COMPLETE';

            return (
              <div key={job.id} className="relative flex gap-4 pb-6" data-testid={`chain-node-${idx}`}>
                {/* Timeline connector */}
                <div className="flex flex-col items-center shrink-0 w-8">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                    isRoot ? 'bg-purple-500/20 ring-2 ring-purple-500'
                    : isContinuation ? 'bg-blue-500/20 ring-2 ring-blue-500'
                    : 'bg-pink-500/20 ring-2 ring-pink-500'
                  }`}>
                    {isRoot && <BookOpen className="w-3.5 h-3.5 text-purple-400" />}
                    {isContinuation && <ChevronRight className="w-3.5 h-3.5 text-blue-400" />}
                    {isRemix && <RefreshCw className="w-3.5 h-3.5 text-pink-400" />}
                  </div>
                  {idx < flat.length - 1 && (
                    <div className="w-px flex-1 bg-slate-700 mt-1" />
                  )}
                </div>

                {/* Content card */}
                <div className={`flex-1 rounded-xl border overflow-hidden transition-all hover:border-slate-600 ${
                  isCompleted ? 'border-slate-700 bg-slate-900/80' : 'border-slate-800 bg-slate-900/40 opacity-70'
                }`}>
                  <div className="flex gap-4 p-4">
                    {/* Preview */}
                    {imageUrl ? (
                      <div className="w-24 h-24 rounded-lg overflow-hidden border border-slate-700 shrink-0 bg-slate-800">
                        <img src={imageUrl} alt={`Episode ${idx + 1}`} className="w-full h-full object-cover" crossOrigin="anonymous" />
                      </div>
                    ) : (
                      <div className="w-24 h-24 rounded-lg bg-slate-800 border border-slate-700 shrink-0 flex items-center justify-center">
                        <Loader2 className={`w-5 h-5 text-slate-600 ${!isCompleted ? 'animate-spin' : ''}`} />
                      </div>
                    )}

                    {/* Info */}
                    <div className="flex-1 min-w-0 space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                          isRoot ? 'bg-purple-500/20 text-purple-400'
                          : isContinuation ? 'bg-blue-500/20 text-blue-400'
                          : 'bg-pink-500/20 text-pink-400'
                        }`}>
                          {isRoot ? 'Original' : isContinuation ? `Ch. ${job.sequence_number}` : 'Remix'}
                        </span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                          isCompleted ? 'bg-emerald-500/20 text-emerald-400' : 'bg-yellow-500/20 text-yellow-400'
                        }`}>
                          {job.status}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-slate-500">
                        <span className="flex items-center gap-1"><Palette className="w-3 h-3" /> {job.style}</span>
                        {job.panelCount && <span>{job.panelCount} panels</span>}
                        {job.cost && <span className="flex items-center gap-0.5"><Coins className="w-3 h-3" /> {job.cost}</span>}
                      </div>

                      {job.storyPrompt && (
                        <p className="text-xs text-slate-400 line-clamp-2">{job.storyPrompt}</p>
                      )}

                      {/* Panels inline */}
                      {job.panels?.length > 1 && (
                        <div className="flex gap-1 pt-1">
                          {job.panels.slice(0, 4).map((p, pi) => (
                            <div key={pi} className="w-12 h-12 rounded overflow-hidden border border-slate-700 shrink-0">
                              <img src={p.imageUrl} alt="" className="w-full h-full object-cover" crossOrigin="anonymous" />
                            </div>
                          ))}
                          {job.panels.length > 4 && (
                            <div className="w-12 h-12 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px] text-slate-500">
                              +{job.panels.length - 4}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Actions */}
                      {isCompleted && (
                        <div className="flex gap-2 pt-1.5">
                          {job.mode === 'strip' && (
                            <Button
                              size="sm" variant="outline"
                              onClick={() => navigate(`/app/photo-to-comic?continue=${job.id}`)}
                              className="h-6 text-[10px] border-blue-500/30 text-blue-400 hover:bg-blue-500/10 px-2"
                              data-testid={`continue-from-${idx}`}
                            >
                              <Sparkles className="w-3 h-3 mr-1" /> Continue
                            </Button>
                          )}
                          <Button
                            size="sm" variant="outline"
                            onClick={() => navigate(`/app/photo-to-comic?remix=${job.id}`)}
                            className="h-6 text-[10px] border-pink-500/30 text-pink-400 hover:bg-pink-500/10 px-2"
                            data-testid={`remix-from-${idx}`}
                          >
                            <RefreshCw className="w-3 h-3 mr-1" /> Remix
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
