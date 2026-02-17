import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  ArrowLeft, Coins, Palette, Plus, Trash2, Upload,
  Tag, Check, X, Loader2, Image
} from 'lucide-react';
import api from '../utils/api';

export default function StyleProfiles() {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [credits, setCredits] = useState(0);
  
  const [newProfile, setNewProfile] = useState({
    name: '',
    description: '',
    tags: []
  });
  const [tagInput, setTagInput] = useState('');

  useEffect(() => {
    fetchProfiles();
  }, []);

  const fetchProfiles = async () => {
    try {
      const [profilesRes, creditsRes] = await Promise.all([
        api.get('/api/genstudio/style-profiles'),
        api.get('/api/credits/balance')
      ]);
      setProfiles(profilesRes.data.profiles);
      setCredits(creditsRes.data.balance);
    } catch (error) {
      toast.error('Failed to load style profiles');
    } finally {
      setLoading(false);
    }
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !newProfile.tags.includes(tagInput.trim())) {
      setNewProfile(prev => ({
        ...prev,
        tags: [...prev.tags, tagInput.trim()]
      }));
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag) => {
    setNewProfile(prev => ({
      ...prev,
      tags: prev.tags.filter(t => t !== tag)
    }));
  };

  const handleCreateProfile = async () => {
    if (!newProfile.name.trim()) {
      toast.error('Please enter a profile name');
      return;
    }

    if (credits < 20) {
      toast.error('Need 20 credits to create a style profile');
      return;
    }

    setCreating(true);
    try {
      const response = await api.post('/api/genstudio/style-profile', newProfile);
      toast.success('Style profile created!');
      setCredits(response.data.remainingCredits);
      setShowCreate(false);
      setNewProfile({ name: '', description: '', tags: [] });
      fetchProfiles();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create profile');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteProfile = async (profileId) => {
    if (!window.confirm('Delete this style profile?')) return;
    
    try {
      await api.delete(`/api/genstudio/style-profile/${profileId}`);
      toast.success('Profile deleted');
      fetchProfiles();
    } catch (error) {
      toast.error('Failed to delete profile');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950/20 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app/gen-studio" className="text-slate-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center">
                  <Palette className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">Brand Style Profiles</h1>
                  <p className="text-xs text-slate-400">Create consistent brand aesthetics</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2">
                <Coins className="w-4 h-4 text-yellow-500" />
                <span className="font-bold text-white">{credits}</span>
              </div>
              <Button 
                onClick={() => setShowCreate(true)}
                className="bg-orange-500 hover:bg-orange-600"
              >
                <Plus className="w-4 h-4 mr-2" />
                Create Profile
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Info */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 mb-8">
          <h3 className="text-lg font-semibold text-white mb-2">What are Brand Style Profiles?</h3>
          <p className="text-slate-400 text-sm mb-4">
            Style Profiles let you maintain visual consistency across all your generated content. 
            Upload 10-20 reference images that represent your brand's aesthetic (color palette, lighting, composition, typography vibe), 
            and use the profile to generate new images in the same style.
          </p>
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2 text-amber-400">
              <Coins className="w-4 h-4" />
              <span>20 credits to create</span>
            </div>
            <div className="flex items-center gap-2 text-green-400">
              <Check className="w-4 h-4" />
              <span>1 credit per use</span>
            </div>
          </div>
        </div>

        {/* Create Modal */}
        {showCreate && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-white">Create Style Profile</h3>
                <button onClick={() => setShowCreate(false)} className="text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-sm text-slate-400 mb-2 block">Profile Name</label>
                  <Input
                    placeholder="e.g., Luxury Brand, Kids Cartoon, Tech Minimal"
                    value={newProfile.name}
                    onChange={(e) => setNewProfile(prev => ({ ...prev, name: e.target.value }))}
                    className="bg-slate-800 border-slate-700 text-white"
                  />
                </div>

                <div>
                  <label className="text-sm text-slate-400 mb-2 block">Description (Optional)</label>
                  <Textarea
                    placeholder="Describe this style profile..."
                    value={newProfile.description}
                    onChange={(e) => setNewProfile(prev => ({ ...prev, description: e.target.value }))}
                    className="bg-slate-800 border-slate-700 text-white min-h-[80px]"
                  />
                </div>

                <div>
                  <label className="text-sm text-slate-400 mb-2 block">Tags</label>
                  <div className="flex gap-2 mb-2">
                    <Input
                      placeholder="Add tag..."
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                      className="bg-slate-800 border-slate-700 text-white"
                    />
                    <Button type="button" variant="outline" onClick={handleAddTag} className="border-slate-700">
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {newProfile.tags.map((tag) => (
                      <span key={tag} className="bg-amber-500/20 text-amber-400 text-xs px-2 py-1 rounded-full flex items-center gap-1">
                        <Tag className="w-3 h-3" />
                        {tag}
                        <button onClick={() => handleRemoveTag(tag)}>
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                </div>

                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
                  <p className="text-sm text-amber-400 flex items-center gap-2">
                    <Coins className="w-4 h-4" />
                    This will cost 20 credits
                  </p>
                </div>

                <Button
                  onClick={handleCreateProfile}
                  disabled={creating || !newProfile.name.trim()}
                  className="w-full bg-orange-500 hover:bg-orange-600"
                >
                  {creating ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <Plus className="w-4 h-4 mr-2" />
                  )}
                  Create Profile
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Profiles Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-500"></div>
          </div>
        ) : profiles.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-slate-800 flex items-center justify-center">
              <Palette className="w-10 h-10 text-slate-600" />
            </div>
            <p className="text-slate-400 mb-4">No style profiles yet</p>
            <Button onClick={() => setShowCreate(true)} className="bg-orange-500 hover:bg-orange-600">
              <Plus className="w-4 h-4 mr-2" />
              Create Your First Profile
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {profiles.map((profile) => (
              <div key={profile.id} className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
                {/* Preview Grid */}
                <div className="aspect-video bg-slate-800 grid grid-cols-4 gap-0.5 p-0.5">
                  {profile.refImageUrls?.length > 0 ? (
                    profile.refImageUrls.slice(0, 8).map((url, i) => (
                      <div key={i} className="bg-slate-700">
                        <img src={url} alt="" className="w-full h-full object-cover" />
                      </div>
                    ))
                  ) : (
                    <div className="col-span-4 flex items-center justify-center text-slate-600">
                      <div className="text-center">
                        <Upload className="w-8 h-8 mx-auto mb-2" />
                        <p className="text-xs">Upload reference images</p>
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Info */}
                <div className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-lg font-semibold text-white">{profile.name}</h4>
                    <button 
                      onClick={() => handleDeleteProfile(profile.id)}
                      className="text-slate-500 hover:text-red-400 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  
                  {profile.description && (
                    <p className="text-sm text-slate-400 mb-3">{profile.description}</p>
                  )}
                  
                  {profile.tags?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {profile.tags.map((tag) => (
                        <span key={tag} className="bg-slate-800 text-slate-400 text-xs px-2 py-0.5 rounded">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>{profile.refImageUrls?.length || 0} images</span>
                    <span className={profile.trained ? 'text-green-400' : 'text-yellow-400'}>
                      {profile.trained ? 'Ready' : 'Upload images to train'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
