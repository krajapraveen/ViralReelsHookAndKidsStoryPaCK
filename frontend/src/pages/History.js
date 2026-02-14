import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { generationAPI } from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Video, BookOpen, ArrowLeft, Filter } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

export default function History() {
  const [generations, setGenerations] = useState([]);
  const [filter, setFilter] = useState('ALL');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGenerations();
  }, [filter]);

  const fetchGenerations = async () => {
    setLoading(true);
    try {
      const typeParam = filter === 'ALL' ? null : filter;
      const response = await generationAPI.getGenerations(typeParam, 0, 50);
      setGenerations(response.data.content || []);
    } catch (error) {
      toast.error('Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app"><Button variant="ghost" size="sm"><ArrowLeft className="w-4 h-4 mr-2" />Dashboard</Button></Link>
            <div className="flex items-center gap-2"><Sparkles className="w-6 h-6 text-indigo-500" /><span className="text-xl font-bold">Generation History</span></div>
          </div>
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-[180px]" data-testid="history-filter">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Types</SelectItem>
              <SelectItem value="REEL">Reels Only</SelectItem>
              <SelectItem value="STORY">Stories Only</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {loading ? (
          <div className="text-center py-12"><p className="text-slate-500">Loading...</p></div>
        ) : generations.length === 0 ? (
          <div className="text-center py-12"><p className="text-slate-500">No generations yet. Start creating!</p><Link to="/app"><Button className="mt-4 bg-indigo-500 hover:bg-indigo-600 text-white">Go to Dashboard</Button></Link></div>
        ) : (
          <div className="space-y-4" data-testid="history-list">
            {generations.map((gen) => (
              <div key={gen.id} className="bg-white rounded-xl border border-slate-200 p-6 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    {gen.type === 'REEL' ? (
                      <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center flex-shrink-0"><Video className="w-6 h-6 text-indigo-600" /></div>
                    ) : (
                      <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0"><BookOpen className="w-6 h-6 text-purple-600" /></div>
                    )}
                    <div className="flex-1">
                      <h3 className="font-bold text-lg">{gen.type} Generation</h3>
                      <p className="text-sm text-slate-500 mt-1">{new Date(gen.createdAt).toLocaleString()}</p>
                      <p className="text-sm text-slate-600 mt-2">Credits used: {gen.creditsUsed}</p>
                    </div>
                  </div>
                  <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                    gen.status === 'SUCCEEDED' ? 'bg-green-100 text-green-700' :
                    gen.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                    'bg-slate-100 text-slate-700'
                  }`}>{gen.status}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}