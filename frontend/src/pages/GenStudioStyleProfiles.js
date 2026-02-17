import React, { useState, useEffect, useRef } from 'react';
import api from '../utils/api';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import {
  Palette, Plus, Upload, Trash2, Image, RefreshCw,
  ChevronLeft, X, Check, Eye, Edit2, Sparkles
} from 'lucide-react';

export default function GenStudioStyleProfiles() {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [credits, setCredits] = useState(0);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [uploadingTo, setUploadingTo] = useState(null);
  
  // Form state
  const [newProfileName, setNewProfileName] = useState('');
  const [newProfileDesc, setNewProfileDesc] = useState('');
  const [newProfileTags, setNewProfileTags] = useState('');
  
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchProfiles();
    fetchCredits();
  }, []);

  const fetchProfiles = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/genstudio/style-profiles');
      setProfiles(res.data.profiles || []);
    } catch (error) {
      console.error('Failed to fetch profiles:', error);
      toast.error('Failed to load style profiles');
    } finally {
      setLoading(false);
    }
  };

  const fetchCredits = async () => {
    try {
      const res = await api.get('/api/credits/balance');
      setCredits(res.data.credits || 0);
    } catch (error) {
      console.error('Failed to fetch credits:', error);
    }
  };

  const createProfile = async () => {
    if (!newProfileName.trim()) {
      toast.error('Please enter a profile name');
      return;
    }
    
    try {
      const res = await api.post('/api/genstudio/style-profile', {
        name: newProfileName.trim(),
        description: newProfileDesc.trim(),
        tags: newProfileTags.split(',').map(t => t.trim()).filter(Boolean)
      });
      
      toast.success('Style profile created!');
      setShowCreateModal(false);
      setNewProfileName('');
      setNewProfileDesc('');
      setNewProfileTags('');
      fetchProfiles();
      fetchCredits();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create profile');
    }
  };

  const deleteProfile = async (profileId) => {
    if (!window.confirm('Delete this style profile? This cannot be undone.')) {
      return;
    }
    
    try {
      await api.delete(`/api/genstudio/style-profile/${profileId}`);
      toast.success('Profile deleted');
      setSelectedProfile(null);
      fetchProfiles();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete profile');
    }
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file || !uploadingTo) return;
    
    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }
    
    if (file.size > 10 * 1024 * 1024) {
      toast.error('Image too large (max 10MB)');
      return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await api.post(
        `/api/genstudio/style-profile/${uploadingTo}/upload-image`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      
      toast.success(`Image uploaded! (${res.data.imageCount} total)`);
      fetchProfiles();
      
      // Update selected profile if viewing it
      if (selectedProfile?.id === uploadingTo) {
        setSelectedProfile(prev => ({
          ...prev,
          refImageUrls: [...(prev.refImageUrls || []), res.data.imageUrl]
        }));
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload image');
    } finally {
      setUploadingTo(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const startUpload = (profileId) => {
    setUploadingTo(profileId);
    fileInputRef.current?.click();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-purple-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileSelect}
      />
      
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold flex items-center gap-3">
              <Palette className="w-8 h-8 text-purple-500" />
              Style Profile Gallery
            </h1>
            <p className="text-slate-400 mt-1 text-sm sm:text-base">
              Create brand styles for consistent AI generations
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-xs sm:text-sm text-slate-400">Credits</p>
              <p className="text-xl sm:text-2xl font-bold text-purple-400">{credits}</p>
            </div>
            <Button 
              onClick={() => setShowCreateModal(true)}
              className="bg-purple-600 hover:bg-purple-700"
            >
              <Plus className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">New Profile</span>
              <span className="sm:hidden">New</span>
            </Button>
          </div>
        </div>

        {/* Profiles Grid */}
        {profiles.length === 0 ? (
          <div className="text-center py-16 bg-slate-800/50 rounded-2xl border border-slate-700">
            <Palette className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">No Style Profiles Yet</h2>
            <p className="text-slate-400 mb-6 max-w-md mx-auto px-4">
              Create your first style profile to maintain consistent branding across all your AI generations.
            </p>
            <Button 
              onClick={() => setShowCreateModal(true)}
              className="bg-purple-600 hover:bg-purple-700"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Your First Profile (20 credits)
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {profiles.map((profile) => (
              <div
                key={profile.id}
                className="bg-slate-800/50 rounded-xl border border-slate-700 overflow-hidden hover:border-purple-500/50 transition-colors"
              >
                {/* Profile Header */}
                <div className="p-4 border-b border-slate-700">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-white truncate">{profile.name}</h3>
                      {profile.description && (
                        <p className="text-sm text-slate-400 mt-1 line-clamp-2">{profile.description}</p>
                      )}
                    </div>
                    <div className="flex gap-1 ml-2 flex-shrink-0">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => setSelectedProfile(profile)}
                        className="text-slate-400 hover:text-white p-2"
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => deleteProfile(profile.id)}
                        className="text-red-400 hover:text-red-300 p-2"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                  
                  {/* Tags */}
                  {profile.tags && profile.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {profile.tags.slice(0, 3).map((tag, i) => (
                        <span key={i} className="px-2 py-0.5 bg-purple-500/20 rounded text-xs text-purple-300">
                          {tag}
                        </span>
                      ))}
                      {profile.tags.length > 3 && (
                        <span className="px-2 py-0.5 text-xs text-slate-500">
                          +{profile.tags.length - 3}
                        </span>
                      )}
                    </div>
                  )}
                </div>
                
                {/* Image Gallery Preview */}
                <div className="p-4">
                  {profile.refImageUrls && profile.refImageUrls.length > 0 ? (
                    <div className="grid grid-cols-3 gap-2">
                      {profile.refImageUrls.slice(0, 5).map((url, i) => (
                        <div 
                          key={i} 
                          className="aspect-square bg-slate-700 rounded-lg overflow-hidden"
                        >
                          <img 
                            src={url.startsWith('http') ? url : `${process.env.REACT_APP_BACKEND_URL}${url}`}
                            alt={`Reference ${i + 1}`}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              e.target.style.display = 'none';
                            }}
                          />
                        </div>
                      ))}
                      {profile.refImageUrls.length < 6 && (
                        <button
                          onClick={() => startUpload(profile.id)}
                          className="aspect-square bg-slate-700/50 rounded-lg border-2 border-dashed border-slate-600 flex items-center justify-center hover:border-purple-500 transition-colors"
                        >
                          <Plus className="w-5 h-5 text-slate-500" />
                        </button>
                      )}
                    </div>
                  ) : (
                    <button
                      onClick={() => startUpload(profile.id)}
                      className="w-full py-8 bg-slate-700/30 rounded-lg border-2 border-dashed border-slate-600 flex flex-col items-center justify-center gap-2 hover:border-purple-500 transition-colors"
                    >
                      <Upload className="w-6 h-6 text-slate-500" />
                      <span className="text-sm text-slate-400">Upload reference images</span>
                    </button>
                  )}
                  
                  <p className="text-xs text-slate-500 mt-2 text-center">
                    {profile.refImageUrls?.length || 0}/20 images • {profile.trained ? '✓ Trained' : 'Not trained'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Create Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-xl max-w-md w-full p-6 border border-slate-700">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold">Create Style Profile</h2>
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => setShowCreateModal(false)}
                  className="text-slate-400"
                >
                  <X className="w-5 h-5" />
                </Button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Profile Name *
                  </label>
                  <Input
                    value={newProfileName}
                    onChange={(e) => setNewProfileName(e.target.value)}
                    placeholder="e.g., Brand Style, Product Photography"
                    className="bg-slate-700 border-slate-600 text-white"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Description
                  </label>
                  <Textarea
                    value={newProfileDesc}
                    onChange={(e) => setNewProfileDesc(e.target.value)}
                    placeholder="Describe the visual style..."
                    className="bg-slate-700 border-slate-600 text-white"
                    rows={3}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Tags (comma-separated)
                  </label>
                  <Input
                    value={newProfileTags}
                    onChange={(e) => setNewProfileTags(e.target.value)}
                    placeholder="e.g., minimalist, professional, vibrant"
                    className="bg-slate-700 border-slate-600 text-white"
                  />
                </div>
                
                <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-3">
                  <p className="text-sm text-purple-300">
                    <Sparkles className="w-4 h-4 inline mr-1" />
                    Creating a style profile costs <strong>20 credits</strong>
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    After creating, upload 5-20 reference images to train your style.
                  </p>
                </div>
                
                <div className="flex gap-3 pt-2">
                  <Button 
                    variant="outline"
                    onClick={() => setShowCreateModal(false)}
                    className="flex-1 border-slate-600"
                  >
                    Cancel
                  </Button>
                  <Button 
                    onClick={createProfile}
                    className="flex-1 bg-purple-600 hover:bg-purple-700"
                    disabled={!newProfileName.trim()}
                  >
                    Create Profile
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Profile Detail Modal */}
        {selectedProfile && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto border border-slate-700">
              <div className="sticky top-0 bg-slate-800 p-4 sm:p-6 border-b border-slate-700 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold">{selectedProfile.name}</h2>
                  {selectedProfile.description && (
                    <p className="text-sm text-slate-400 mt-1">{selectedProfile.description}</p>
                  )}
                </div>
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => setSelectedProfile(null)}
                  className="text-slate-400"
                >
                  <X className="w-5 h-5" />
                </Button>
              </div>
              
              <div className="p-4 sm:p-6">
                {/* Tags */}
                {selectedProfile.tags && selectedProfile.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-6">
                    {selectedProfile.tags.map((tag, i) => (
                      <span key={i} className="px-3 py-1 bg-purple-500/20 rounded-full text-sm text-purple-300">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                
                {/* Image Gallery */}
                <h3 className="text-sm font-medium text-slate-400 mb-4">
                  Reference Images ({selectedProfile.refImageUrls?.length || 0}/20)
                </h3>
                
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 sm:gap-4">
                  {selectedProfile.refImageUrls?.map((url, i) => (
                    <div 
                      key={i} 
                      className="aspect-square bg-slate-700 rounded-lg overflow-hidden relative group"
                    >
                      <img 
                        src={url.startsWith('http') ? url : `${process.env.REACT_APP_BACKEND_URL}${url}`}
                        alt={`Reference ${i + 1}`}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect fill="%23334155" width="100" height="100"/><text x="50" y="50" text-anchor="middle" dy=".3em" fill="%2364748b" font-size="12">Image</text></svg>';
                        }}
                      />
                      <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <span className="text-xs text-white">Image {i + 1}</span>
                      </div>
                    </div>
                  ))}
                  
                  {/* Upload button */}
                  {(selectedProfile.refImageUrls?.length || 0) < 20 && (
                    <button
                      onClick={() => startUpload(selectedProfile.id)}
                      className="aspect-square bg-slate-700/50 rounded-lg border-2 border-dashed border-slate-600 flex flex-col items-center justify-center gap-2 hover:border-purple-500 transition-colors"
                    >
                      <Upload className="w-6 h-6 text-slate-500" />
                      <span className="text-xs text-slate-400">Add Image</span>
                    </button>
                  )}
                </div>
                
                {(!selectedProfile.refImageUrls || selectedProfile.refImageUrls.length === 0) && (
                  <div className="text-center py-8 text-slate-400">
                    <Image className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No reference images yet</p>
                    <p className="text-sm">Upload 5-20 images to train this style</p>
                  </div>
                )}
                
                {/* Actions */}
                <div className="flex flex-col sm:flex-row gap-3 mt-6 pt-6 border-t border-slate-700">
                  <Button
                    onClick={() => startUpload(selectedProfile.id)}
                    className="flex-1 bg-purple-600 hover:bg-purple-700"
                    disabled={(selectedProfile.refImageUrls?.length || 0) >= 20}
                  >
                    <Upload className="w-4 h-4 mr-2" />
                    Upload Images
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => deleteProfile(selectedProfile.id)}
                    className="flex-1 border-red-500/50 text-red-400 hover:bg-red-500/10"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete Profile
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
