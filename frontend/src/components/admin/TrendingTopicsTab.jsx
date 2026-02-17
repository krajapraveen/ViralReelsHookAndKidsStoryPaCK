import React, { useState, useEffect } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { TrendingUp, Plus, Trash2, Loader2, Calendar, X } from 'lucide-react';
import api from '../../utils/api';

export default function TrendingTopicsTab() {
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [newTopic, setNewTopic] = useState({
    title: '',
    niche: 'business',
    hook_preview: '',
    suggested_angle: '',
    is_active: true
  });

  const niches = ['luxury', 'relationship', 'health', 'motivation', 'parenting', 'business', 'travel', 'food'];

  useEffect(() => {
    fetchTopics();
  }, []);

  const fetchTopics = async () => {
    try {
      const response = await api.get('/api/content/trending?active_only=false');
      setTopics(response.data.topics || []);
    } catch (error) {
      toast.error('Failed to load trending topics');
    } finally {
      setLoading(false);
    }
  };

  const createTopic = async () => {
    if (!newTopic.title || !newTopic.hook_preview) {
      toast.error('Title and hook preview are required');
      return;
    }

    setSaving(true);
    try {
      await api.post('/api/content/trending', newTopic);
      toast.success('Trending topic created!');
      setNewTopic({
        title: '',
        niche: 'business',
        hook_preview: '',
        suggested_angle: '',
        is_active: true
      });
      setShowForm(false);
      fetchTopics();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create topic');
    } finally {
      setSaving(false);
    }
  };

  const deleteTopic = async (topicId) => {
    if (!window.confirm('Delete this trending topic?')) return;
    
    try {
      await api.delete(`/api/content/trending/${topicId}`);
      toast.success('Topic deleted');
      fetchTopics();
    } catch (error) {
      toast.error('Failed to delete topic');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-orange-500" />
            Trending Topics Manager
          </h3>
          <p className="text-slate-400 text-sm">Manage weekly trending content topics for creators</p>
        </div>
        <Button 
          onClick={() => setShowForm(!showForm)}
          className="bg-purple-600 hover:bg-purple-700"
          data-testid="add-trending-topic-btn"
        >
          {showForm ? <X className="w-4 h-4 mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
          {showForm ? 'Cancel' : 'Add Topic'}
        </Button>
      </div>

      {/* Add Topic Form */}
      {showForm && (
        <div className="bg-slate-700/50 rounded-lg p-6 border border-slate-600">
          <h4 className="font-semibold mb-4">Create New Trending Topic</h4>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <Label className="text-slate-300">Topic Title</Label>
              <Input
                placeholder="e.g., 'AI Tools for Creators'"
                value={newTopic.title}
                onChange={(e) => setNewTopic({...newTopic, title: e.target.value})}
                className="bg-slate-800 border-slate-600"
                data-testid="trending-title-input"
              />
            </div>
            <div>
              <Label className="text-slate-300">Niche</Label>
              <Select value={newTopic.niche} onValueChange={(v) => setNewTopic({...newTopic, niche: v})}>
                <SelectTrigger className="bg-slate-800 border-slate-600" data-testid="trending-niche-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {niches.map(n => (
                    <SelectItem key={n} value={n}>{n.charAt(0).toUpperCase() + n.slice(1)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="md:col-span-2">
              <Label className="text-slate-300">Hook Preview</Label>
              <Input
                placeholder="e.g., 'These 5 AI tools changed how I create content...'"
                value={newTopic.hook_preview}
                onChange={(e) => setNewTopic({...newTopic, hook_preview: e.target.value})}
                className="bg-slate-800 border-slate-600"
                data-testid="trending-hook-input"
              />
            </div>
            <div className="md:col-span-2">
              <Label className="text-slate-300">Suggested Angle</Label>
              <Input
                placeholder="e.g., 'Focus on practical use cases and before/after results'"
                value={newTopic.suggested_angle}
                onChange={(e) => setNewTopic({...newTopic, suggested_angle: e.target.value})}
                className="bg-slate-800 border-slate-600"
                data-testid="trending-angle-input"
              />
            </div>
            <div className="flex items-center gap-2">
              <input 
                type="checkbox"
                id="isActive"
                checked={newTopic.is_active}
                onChange={(e) => setNewTopic({...newTopic, is_active: e.target.checked})}
                className="rounded"
              />
              <Label htmlFor="isActive" className="text-slate-300 cursor-pointer">Active (visible to users)</Label>
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <Button 
              onClick={createTopic} 
              disabled={saving}
              className="bg-green-600 hover:bg-green-700"
              data-testid="save-trending-topic-btn"
            >
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
              Create Topic
            </Button>
          </div>
        </div>
      )}

      {/* Topics List */}
      <div className="space-y-4">
        {topics.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <TrendingUp className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No trending topics yet. Create your first one!</p>
          </div>
        ) : (
          topics.map((topic) => (
            <div 
              key={topic.id} 
              className={`bg-slate-800 rounded-lg p-4 border ${topic.is_active ? 'border-green-500/50' : 'border-slate-600'}`}
              data-testid={`trending-topic-${topic.id}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${topic.is_active ? 'bg-green-500/20 text-green-400' : 'bg-slate-600 text-slate-400'}`}>
                      {topic.is_active ? 'Active' : 'Inactive'}
                    </span>
                    <span className="px-2 py-0.5 rounded text-xs bg-purple-500/20 text-purple-400">
                      {topic.niche}
                    </span>
                  </div>
                  <h4 className="font-bold text-lg mb-1">{topic.title}</h4>
                  <p className="text-sm text-slate-400 mb-2">
                    <span className="text-orange-400 font-medium">Hook: </span>
                    {topic.hook_preview}
                  </p>
                  {topic.suggested_angle && (
                    <p className="text-xs text-slate-500">
                      💡 {topic.suggested_angle}
                    </p>
                  )}
                  <p className="text-xs text-slate-600 mt-2 flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    Created: {new Date(topic.createdAt).toLocaleDateString()}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteTopic(topic.id)}
                  className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                  data-testid={`delete-topic-${topic.id}`}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
