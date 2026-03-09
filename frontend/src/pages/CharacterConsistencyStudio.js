import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import api from '../utils/api';
import {
  ArrowLeft, Upload, Users, Wand2, Loader2, Save,
  Plus, Trash2, Edit, Image, Palette, Eye, Copy,
  CheckCircle, XCircle, RefreshCw, Download, Sparkles,
  User, Shirt, Smile, Zap
} from 'lucide-react';

export default function CharacterConsistencyStudio() {
  const [loading, setLoading] = useState(false);
  const [characters, setCharacters] = useState([]);
  const [selectedCharacter, setSelectedCharacter] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [generatedImages, setGeneratedImages] = useState([]);
  const fileInputRef = useRef(null);

  // New character form
  const [newCharacter, setNewCharacter] = useState({
    name: '',
    description: '',
    appearance: '',
    clothing: '',
    personality: '',
    age_group: 'adult',
    style: 'cartoon',
    reference_images: []
  });

  // Generation settings
  const [generateSettings, setGenerateSettings] = useState({
    poses: ['standing', 'sitting', 'walking'],
    expressions: ['happy', 'neutral', 'surprised'],
    count: 3
  });

  useEffect(() => {
    fetchCharacters();
  }, []);

  const fetchCharacters = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/story-video-studio/characters/list');
      if (res.data.success) {
        setCharacters(res.data.characters || []);
      }
    } catch (error) {
      console.error('Failed to fetch characters:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCharacter = async () => {
    if (!newCharacter.name || !newCharacter.description) {
      toast.error('Please fill in name and description');
      return;
    }

    setLoading(true);
    try {
      const res = await api.post('/api/story-video-studio/characters/create', newCharacter);
      if (res.data.success) {
        toast.success('Character created successfully!');
        setShowCreateModal(false);
        setNewCharacter({
          name: '',
          description: '',
          appearance: '',
          clothing: '',
          personality: '',
          age_group: 'adult',
          style: 'cartoon',
          reference_images: []
        });
        fetchCharacters();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create character');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateVariations = async () => {
    if (!selectedCharacter) {
      toast.error('Please select a character first');
      return;
    }

    setLoading(true);
    try {
      const res = await api.post('/api/story-video-studio/characters/generate-variations', {
        character_id: selectedCharacter.character_id,
        poses: generateSettings.poses,
        expressions: generateSettings.expressions,
        count: generateSettings.count
      });

      if (res.data.success) {
        setGeneratedImages(res.data.images);
        toast.success(`Generated ${res.data.images.length} character variations!`);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate variations');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCharacter = async (characterId) => {
    if (!window.confirm('Are you sure you want to delete this character?')) return;

    try {
      await api.delete(`/api/story-video-studio/characters/${characterId}`);
      toast.success('Character deleted');
      if (selectedCharacter?.character_id === characterId) {
        setSelectedCharacter(null);
      }
      fetchCharacters();
    } catch (error) {
      toast.error('Failed to delete character');
    }
  };

  const handleImageUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    // For now, we'll just store URLs of uploaded files
    // In production, these would be uploaded to R2
    toast.info('Reference images will be used for character consistency');
    setNewCharacter(prev => ({
      ...prev,
      reference_images: [...prev.reference_images, ...files.map(f => URL.createObjectURL(f))]
    }));
  };

  const copyPrompt = (character) => {
    const prompt = `${character.name}: ${character.appearance}. ${character.clothing}. ${character.description}. Style: ${character.style}`;
    navigator.clipboard.writeText(prompt);
    toast.success('Character prompt copied!');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-purple-950 to-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-lg border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app/story-video-studio">
              <Button variant="ghost" size="icon" className="text-white">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                <Users className="w-6 h-6 text-purple-400" />
                Character Consistency Studio
              </h1>
              <p className="text-sm text-slate-400">Create and manage consistent characters</p>
            </div>
          </div>

          <Button
            onClick={() => setShowCreateModal(true)}
            className="bg-purple-500 hover:bg-purple-600"
            data-testid="create-character-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Character
          </Button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Character List */}
          <div className="lg:col-span-1 space-y-4">
            <h2 className="text-lg font-semibold text-white mb-4">Your Characters</h2>
            
            {loading && characters.length === 0 ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
              </div>
            ) : characters.length === 0 ? (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-8 text-center">
                <Users className="w-12 h-12 text-slate-500 mx-auto mb-3" />
                <p className="text-slate-400">No characters yet</p>
                <p className="text-slate-500 text-sm mt-1">Create your first character to get started</p>
              </div>
            ) : (
              <div className="space-y-3">
                {characters.map((char) => (
                  <button
                    key={char.character_id}
                    onClick={() => setSelectedCharacter(char)}
                    className={`w-full p-4 rounded-xl border-2 text-left transition-all ${
                      selectedCharacter?.character_id === char.character_id
                        ? 'border-purple-500 bg-purple-500/20'
                        : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
                    }`}
                    data-testid={`character-${char.character_id}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                          <span className="text-white font-bold text-lg">
                            {char.name?.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <h3 className="font-semibold text-white">{char.name}</h3>
                          <p className="text-xs text-slate-400">{char.style} style</p>
                        </div>
                      </div>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            copyPrompt(char);
                          }}
                          className="text-slate-400 hover:text-white h-8 w-8 p-0"
                        >
                          <Copy className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteCharacter(char.character_id);
                          }}
                          className="text-slate-400 hover:text-red-400 h-8 w-8 p-0"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                    <p className="text-sm text-slate-400 mt-2 line-clamp-2">{char.description}</p>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Character Details & Generation */}
          <div className="lg:col-span-2 space-y-6">
            {selectedCharacter ? (
              <>
                {/* Character Details Card */}
                <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6" data-testid="character-details">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-white">{selectedCharacter.name}</h2>
                    <span className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded-full text-sm">
                      {selectedCharacter.style}
                    </span>
                  </div>

                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-3">
                      <div>
                        <label className="text-xs text-slate-500 uppercase flex items-center gap-1">
                          <User className="w-3 h-3" /> Appearance
                        </label>
                        <p className="text-slate-300 text-sm mt-1">{selectedCharacter.appearance || 'Not specified'}</p>
                      </div>
                      <div>
                        <label className="text-xs text-slate-500 uppercase flex items-center gap-1">
                          <Shirt className="w-3 h-3" /> Clothing
                        </label>
                        <p className="text-slate-300 text-sm mt-1">{selectedCharacter.clothing || 'Not specified'}</p>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div>
                        <label className="text-xs text-slate-500 uppercase flex items-center gap-1">
                          <Smile className="w-3 h-3" /> Personality
                        </label>
                        <p className="text-slate-300 text-sm mt-1">{selectedCharacter.personality || 'Not specified'}</p>
                      </div>
                      <div>
                        <label className="text-xs text-slate-500 uppercase">Description</label>
                        <p className="text-slate-300 text-sm mt-1">{selectedCharacter.description}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Generation Settings */}
                <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                  <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-yellow-400" />
                    Generate Variations
                  </h3>

                  <div className="grid md:grid-cols-3 gap-4 mb-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Poses</label>
                      <div className="flex flex-wrap gap-2">
                        {['standing', 'sitting', 'walking', 'running', 'jumping'].map((pose) => (
                          <button
                            key={pose}
                            onClick={() => {
                              setGenerateSettings(prev => ({
                                ...prev,
                                poses: prev.poses.includes(pose)
                                  ? prev.poses.filter(p => p !== pose)
                                  : [...prev.poses, pose]
                              }));
                            }}
                            className={`px-3 py-1 rounded-full text-sm transition-all ${
                              generateSettings.poses.includes(pose)
                                ? 'bg-purple-500 text-white'
                                : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                            }`}
                          >
                            {pose}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Expressions</label>
                      <div className="flex flex-wrap gap-2">
                        {['happy', 'sad', 'angry', 'surprised', 'neutral'].map((expr) => (
                          <button
                            key={expr}
                            onClick={() => {
                              setGenerateSettings(prev => ({
                                ...prev,
                                expressions: prev.expressions.includes(expr)
                                  ? prev.expressions.filter(e => e !== expr)
                                  : [...prev.expressions, expr]
                              }));
                            }}
                            className={`px-3 py-1 rounded-full text-sm transition-all ${
                              generateSettings.expressions.includes(expr)
                                ? 'bg-pink-500 text-white'
                                : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                            }`}
                          >
                            {expr}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Number of Images</label>
                      <Input
                        type="number"
                        min="1"
                        max="10"
                        value={generateSettings.count}
                        onChange={(e) => setGenerateSettings(prev => ({ ...prev, count: parseInt(e.target.value) || 1 }))}
                        className="bg-slate-900/50 border-slate-600 text-white w-24"
                      />
                    </div>
                  </div>

                  <Button
                    onClick={handleGenerateVariations}
                    disabled={loading}
                    className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
                    data-testid="generate-variations-btn"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Wand2 className="w-4 h-4 mr-2" />
                        Generate {generateSettings.count} Variations
                      </>
                    )}
                  </Button>
                </div>

                {/* Generated Images Grid */}
                {generatedImages.length > 0 && (
                  <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6" data-testid="generated-images">
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                      <Image className="w-5 h-5 text-blue-400" />
                      Generated Variations ({generatedImages.length})
                    </h3>

                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {generatedImages.map((img, idx) => (
                        <div key={idx} className="relative group">
                          <img
                            src={img.url}
                            alt={`Variation ${idx + 1}`}
                            className="w-full aspect-square object-cover rounded-lg"
                          />
                          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center gap-2">
                            <Button size="sm" variant="secondary">
                              <Download className="w-4 h-4" />
                            </Button>
                            <Button size="sm" variant="secondary">
                              <Eye className="w-4 h-4" />
                            </Button>
                          </div>
                          <div className="absolute bottom-2 left-2 right-2 text-xs text-white bg-black/50 rounded px-2 py-1">
                            {img.pose} - {img.expression}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-12 text-center">
                <Users className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-slate-400 mb-2">Select a Character</h3>
                <p className="text-slate-500">Choose a character from the list or create a new one to get started</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Create Character Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 rounded-2xl border border-slate-700 max-w-2xl w-full max-h-[90vh] overflow-y-auto" data-testid="create-character-modal">
            <div className="p-6 border-b border-slate-700">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-purple-400" />
                Create New Character
              </h2>
            </div>

            <div className="p-6 space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Character Name *</label>
                  <Input
                    value={newCharacter.name}
                    onChange={(e) => setNewCharacter(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Luna the Rabbit"
                    className="bg-slate-800 border-slate-600 text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Age Group</label>
                  <select
                    value={newCharacter.age_group}
                    onChange={(e) => setNewCharacter(prev => ({ ...prev, age_group: e.target.value }))}
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-lg px-3 py-2"
                  >
                    <option value="child">Child</option>
                    <option value="teen">Teen</option>
                    <option value="adult">Adult</option>
                    <option value="elderly">Elderly</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Description *</label>
                <Textarea
                  value={newCharacter.description}
                  onChange={(e) => setNewCharacter(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="A brief description of your character..."
                  className="bg-slate-800 border-slate-600 text-white min-h-[80px]"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Physical Appearance</label>
                <Textarea
                  value={newCharacter.appearance}
                  onChange={(e) => setNewCharacter(prev => ({ ...prev, appearance: e.target.value }))}
                  placeholder="e.g., White fluffy fur, big blue eyes, long ears with pink tips..."
                  className="bg-slate-800 border-slate-600 text-white min-h-[80px]"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Clothing / Accessories</label>
                <Textarea
                  value={newCharacter.clothing}
                  onChange={(e) => setNewCharacter(prev => ({ ...prev, clothing: e.target.value }))}
                  placeholder="e.g., Red bow tie, blue overalls, star-shaped pendant..."
                  className="bg-slate-800 border-slate-600 text-white min-h-[60px]"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Personality</label>
                <Input
                  value={newCharacter.personality}
                  onChange={(e) => setNewCharacter(prev => ({ ...prev, personality: e.target.value }))}
                  placeholder="e.g., Brave, curious, friendly..."
                  className="bg-slate-800 border-slate-600 text-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Art Style</label>
                <div className="grid grid-cols-3 gap-2">
                  {['cartoon', 'anime', 'realistic', 'watercolor', 'comic', '3d_render'].map((style) => (
                    <button
                      key={style}
                      onClick={() => setNewCharacter(prev => ({ ...prev, style }))}
                      className={`p-3 rounded-lg border-2 text-sm transition-all ${
                        newCharacter.style === style
                          ? 'border-purple-500 bg-purple-500/20 text-white'
                          : 'border-slate-600 text-slate-400 hover:border-slate-500'
                      }`}
                    >
                      {style.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>

              {/* Reference Images Upload */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Reference Images (Optional)</label>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleImageUpload}
                  accept="image/*"
                  multiple
                  className="hidden"
                />
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  variant="outline"
                  className="w-full border-dashed border-2 border-slate-600 hover:border-purple-500 h-20"
                >
                  <Upload className="w-5 h-5 mr-2" />
                  Upload Reference Images
                </Button>
                {newCharacter.reference_images.length > 0 && (
                  <div className="flex gap-2 mt-3 flex-wrap">
                    {newCharacter.reference_images.map((img, idx) => (
                      <div key={idx} className="relative">
                        <img src={img} alt={`Ref ${idx + 1}`} className="w-16 h-16 object-cover rounded" />
                        <button
                          onClick={() => setNewCharacter(prev => ({
                            ...prev,
                            reference_images: prev.reference_images.filter((_, i) => i !== idx)
                          }))}
                          className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center"
                        >
                          <XCircle className="w-4 h-4 text-white" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="p-6 border-t border-slate-700 flex justify-end gap-3">
              <Button
                variant="ghost"
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400"
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreateCharacter}
                disabled={loading || !newCharacter.name || !newCharacter.description}
                className="bg-purple-500 hover:bg-purple-600"
              >
                {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                Create Character
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
