import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Plus, 
  Edit2, 
  Trash2, 
  Save, 
  X, 
  Check,
  Search,
  RefreshCw,
  FileText,
  MessageSquare,
  Sparkles,
  Grid3X3,
  Shield,
  AlertTriangle
} from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const BioTemplatesAdmin = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [activeTab, setActiveTab] = useState('niches');
  const [stats, setStats] = useState(null);
  
  // Data states
  const [niches, setNiches] = useState([]);
  const [headlines, setHeadlines] = useState([]);
  const [values, setValues] = useState([]);
  const [ctas, setCtas] = useState([]);
  const [emojis, setEmojis] = useState([]);
  
  // Edit modal state
  const [editModal, setEditModal] = useState({ open: false, type: '', data: null, isNew: false });
  const [deleteConfirm, setDeleteConfirm] = useState({ open: false, type: '', id: '' });
  
  // Search/filter
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    checkAdminAccess();
  }, []);

  const checkAdminAccess = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        navigate('/login');
        return;
      }

      const response = await fetch(`${API_URL}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        const user = data.user || data;
        
        if (user.role?.toUpperCase() !== 'ADMIN') {
          toast.error('Access denied. Admin role required.');
          navigate('/app');
          return;
        }
        
        setIsAdmin(true);
        fetchAllData();
      } else {
        navigate('/login');
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      navigate('/login');
    }
  };

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const [statsRes, nichesRes, headlinesRes, valuesRes, ctasRes, emojisRes] = await Promise.all([
        fetch(`${API_URL}/api/instagram-bio-generator/admin/stats`, { headers }),
        fetch(`${API_URL}/api/instagram-bio-generator/admin/niches`, { headers }),
        fetch(`${API_URL}/api/instagram-bio-generator/admin/headlines`, { headers }),
        fetch(`${API_URL}/api/instagram-bio-generator/admin/values`, { headers }),
        fetch(`${API_URL}/api/instagram-bio-generator/admin/ctas`, { headers }),
        fetch(`${API_URL}/api/instagram-bio-generator/admin/emojis`, { headers })
      ]);

      if (statsRes.ok) setStats(await statsRes.json());
      if (nichesRes.ok) setNiches((await nichesRes.json()).niches || []);
      if (headlinesRes.ok) setHeadlines((await headlinesRes.json()).headlines || []);
      if (valuesRes.ok) setValues((await valuesRes.json()).values || []);
      if (ctasRes.ok) setCtas((await ctasRes.json()).ctas || []);
      if (emojisRes.ok) setEmojis((await emojisRes.json()).emoji_sets || []);

    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load template data');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    const { type, data, isNew } = editModal;
    const token = localStorage.getItem('token');
    
    try {
      let url = `${API_URL}/api/instagram-bio-generator/admin/${type}`;
      let method = 'POST';
      
      if (!isNew) {
        url += `/${data.id}`;
        method = 'PUT';
      }

      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });

      if (response.ok) {
        toast.success(isNew ? 'Created successfully' : 'Updated successfully');
        setEditModal({ open: false, type: '', data: null, isNew: false });
        fetchAllData();
      } else {
        const err = await response.json();
        toast.error(err.detail || 'Operation failed');
      }
    } catch (error) {
      toast.error('Save failed');
    }
  };

  const handleDelete = async () => {
    const { type, id } = deleteConfirm;
    const token = localStorage.getItem('token');

    try {
      const response = await fetch(`${API_URL}/api/instagram-bio-generator/admin/${type}/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        toast.success('Deleted successfully');
        setDeleteConfirm({ open: false, type: '', id: '' });
        fetchAllData();
      } else {
        toast.error('Delete failed');
      }
    } catch (error) {
      toast.error('Delete failed');
    }
  };

  const openEditModal = (type, data = null) => {
    const isNew = !data;
    
    const defaults = {
      niches: { name: '', description: '', active: true },
      headlines: { niche: '', tone: '', template: '', active: true },
      values: { niche: '', template: '', active: true },
      ctas: { goal: '', template: '', active: true },
      emojis: { tone: '', emojis: [], active: true }
    };

    setEditModal({
      open: true,
      type,
      data: data || defaults[type],
      isNew
    });
  };

  const filterData = (data) => {
    if (!searchTerm) return data;
    const term = searchTerm.toLowerCase();
    return data.filter(item => 
      JSON.stringify(item).toLowerCase().includes(term)
    );
  };

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl text-white mb-2">Access Denied</h2>
          <p className="text-slate-400">Admin privileges required</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/app/admin" className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700 transition-colors">
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-white" data-testid="admin-bio-title">Bio Template Admin</h1>
              <p className="text-slate-400 text-sm">Manage Instagram Bio Generator templates</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchAllData}
              className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
              data-testid="refresh-btn"
            >
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="text-2xl font-bold text-white">{stats.total_niches}</div>
              <div className="text-slate-400 text-sm">Niches</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="text-2xl font-bold text-white">{stats.total_headlines}</div>
              <div className="text-slate-400 text-sm">Headlines</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="text-2xl font-bold text-white">{stats.total_value_lines}</div>
              <div className="text-slate-400 text-sm">Value Lines</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="text-2xl font-bold text-white">{stats.total_ctas}</div>
              <div className="text-slate-400 text-sm">CTAs</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="text-2xl font-bold text-purple-400">{stats.total_generations}</div>
              <div className="text-slate-400 text-sm">Generations</div>
            </div>
          </div>
        )}

        {/* Search */}
        <div className="relative mb-6">
          <Search className="w-5 h-5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search templates..."
            className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
            data-testid="search-input"
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'niches', label: 'Niches', icon: Grid3X3 },
            { id: 'headlines', label: 'Headlines', icon: FileText },
            { id: 'values', label: 'Value Lines', icon: MessageSquare },
            { id: 'ctas', label: 'CTAs', icon: Sparkles },
            { id: 'emojis', label: 'Emojis', icon: Sparkles }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
              data-testid={`tab-${tab.id}`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
          {/* Add Button */}
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-white capitalize">{activeTab}</h2>
            <button
              onClick={() => openEditModal(activeTab)}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors"
              data-testid="add-new-btn"
            >
              <Plus className="w-4 h-4" /> Add New
            </button>
          </div>

          {/* Niches Tab */}
          {activeTab === 'niches' && (
            <div className="space-y-3">
              {filterData(niches).length === 0 ? (
                <div className="text-center py-8 text-slate-400">No niches found</div>
              ) : (
                filterData(niches).map(niche => (
                  <div key={niche.id} className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                    <div>
                      <div className="font-medium text-white">{niche.name}</div>
                      {niche.description && <div className="text-sm text-slate-400">{niche.description}</div>}
                      <span className={`text-xs px-2 py-0.5 rounded ${niche.active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                        {niche.active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => openEditModal('niches', niche)} className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg">
                        <Edit2 className="w-4 h-4 text-blue-400" />
                      </button>
                      <button onClick={() => setDeleteConfirm({ open: true, type: 'niches', id: niche.id })} className="p-2 bg-slate-700 hover:bg-red-600/20 rounded-lg">
                        <Trash2 className="w-4 h-4 text-red-400" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Headlines Tab */}
          {activeTab === 'headlines' && (
            <div className="space-y-3">
              {filterData(headlines).length === 0 ? (
                <div className="text-center py-8 text-slate-400">No headlines found</div>
              ) : (
                filterData(headlines).map(h => (
                  <div key={h.id} className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex gap-2 mb-2">
                          <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded">{h.niche}</span>
                          <span className="text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded">{h.tone}</span>
                        </div>
                        <div className="text-white text-sm">{h.template}</div>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => openEditModal('headlines', h)} className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg">
                          <Edit2 className="w-4 h-4 text-blue-400" />
                        </button>
                        <button onClick={() => setDeleteConfirm({ open: true, type: 'headlines', id: h.id })} className="p-2 bg-slate-700 hover:bg-red-600/20 rounded-lg">
                          <Trash2 className="w-4 h-4 text-red-400" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Values Tab */}
          {activeTab === 'values' && (
            <div className="space-y-3">
              {filterData(values).length === 0 ? (
                <div className="text-center py-8 text-slate-400">No value lines found</div>
              ) : (
                filterData(values).map(v => (
                  <div key={v.id} className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded mb-2 inline-block">{v.niche}</span>
                        <div className="text-white text-sm">{v.template}</div>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => openEditModal('values', v)} className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg">
                          <Edit2 className="w-4 h-4 text-blue-400" />
                        </button>
                        <button onClick={() => setDeleteConfirm({ open: true, type: 'values', id: v.id })} className="p-2 bg-slate-700 hover:bg-red-600/20 rounded-lg">
                          <Trash2 className="w-4 h-4 text-red-400" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* CTAs Tab */}
          {activeTab === 'ctas' && (
            <div className="space-y-3">
              {filterData(ctas).length === 0 ? (
                <div className="text-center py-8 text-slate-400">No CTAs found</div>
              ) : (
                filterData(ctas).map(c => (
                  <div key={c.id} className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <span className="text-xs px-2 py-0.5 bg-green-500/20 text-green-400 rounded mb-2 inline-block">{c.goal}</span>
                        <div className="text-white text-sm">{c.template}</div>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => openEditModal('ctas', c)} className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg">
                          <Edit2 className="w-4 h-4 text-blue-400" />
                        </button>
                        <button onClick={() => setDeleteConfirm({ open: true, type: 'ctas', id: c.id })} className="p-2 bg-slate-700 hover:bg-red-600/20 rounded-lg">
                          <Trash2 className="w-4 h-4 text-red-400" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Emojis Tab */}
          {activeTab === 'emojis' && (
            <div className="space-y-3">
              {filterData(emojis).length === 0 ? (
                <div className="text-center py-8 text-slate-400">No emoji sets found</div>
              ) : (
                filterData(emojis).map(e => (
                  <div key={e.id} className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <span className="text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded mb-2 inline-block">{e.tone}</span>
                        <div className="text-white text-xl">{e.emojis?.join(' ')}</div>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => openEditModal('emojis', e)} className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg">
                          <Edit2 className="w-4 h-4 text-blue-400" />
                        </button>
                        <button onClick={() => setDeleteConfirm({ open: true, type: 'emojis', id: e.id })} className="p-2 bg-slate-700 hover:bg-red-600/20 rounded-lg">
                          <Trash2 className="w-4 h-4 text-red-400" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Edit Modal */}
        {editModal.open && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-lg">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-white">
                  {editModal.isNew ? 'Add New' : 'Edit'} {editModal.type.slice(0, -1)}
                </h3>
                <button onClick={() => setEditModal({ open: false, type: '', data: null, isNew: false })} className="p-2 hover:bg-slate-800 rounded-lg">
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              <div className="space-y-4">
                {/* Niches */}
                {editModal.type === 'niches' && (
                  <>
                    <div>
                      <label className="block text-sm text-slate-300 mb-1">Name</label>
                      <input
                        type="text"
                        value={editModal.data.name}
                        onChange={(e) => setEditModal(prev => ({ ...prev, data: { ...prev.data, name: e.target.value } }))}
                        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-slate-300 mb-1">Description</label>
                      <input
                        type="text"
                        value={editModal.data.description || ''}
                        onChange={(e) => setEditModal(prev => ({ ...prev, data: { ...prev.data, description: e.target.value } }))}
                        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white"
                      />
                    </div>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={editModal.data.active}
                        onChange={(e) => setEditModal(prev => ({ ...prev, data: { ...prev.data, active: e.target.checked } }))}
                        className="w-4 h-4"
                      />
                      <span className="text-slate-300">Active</span>
                    </label>
                  </>
                )}

                {/* Headlines */}
                {editModal.type === 'headlines' && (
                  <>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm text-slate-300 mb-1">Niche</label>
                        <select
                          value={editModal.data.niche}
                          onChange={(e) => setEditModal(prev => ({ ...prev, data: { ...prev.data, niche: e.target.value } }))}
                          className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white"
                        >
                          <option value="">Select niche</option>
                          {niches.filter(n => n.active).map(n => (
                            <option key={n.id} value={n.name}>{n.name}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm text-slate-300 mb-1">Tone</label>
                        <select
                          value={editModal.data.tone}
                          onChange={(e) => setEditModal(prev => ({ ...prev, data: { ...prev.data, tone: e.target.value } }))}
                          className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white"
                        >
                          <option value="">Select tone</option>
                          {['Professional', 'Bold', 'Friendly', 'Inspiring', 'Witty', 'Minimal', 'Luxurious', 'Edgy'].map(t => (
                            <option key={t} value={t}>{t}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-300 mb-1">Template</label>
                      <textarea
                        value={editModal.data.template}
                        onChange={(e) => setEditModal(prev => ({ ...prev, data: { ...prev.data, template: e.target.value } }))}
                        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white h-24"
                        placeholder="Use {emoji} for emoji placeholder"
                      />
                    </div>
                  </>
                )}

                {/* Values */}
                {editModal.type === 'values' && (
                  <>
                    <div>
                      <label className="block text-sm text-slate-300 mb-1">Niche</label>
                      <select
                        value={editModal.data.niche}
                        onChange={(e) => setEditModal(prev => ({ ...prev, data: { ...prev.data, niche: e.target.value } }))}
                        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white"
                      >
                        <option value="">Select niche</option>
                        {niches.filter(n => n.active).map(n => (
                          <option key={n.id} value={n.name}>{n.name}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-300 mb-1">Template</label>
                      <textarea
                        value={editModal.data.template}
                        onChange={(e) => setEditModal(prev => ({ ...prev, data: { ...prev.data, template: e.target.value } }))}
                        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white h-24"
                      />
                    </div>
                  </>
                )}

                {/* CTAs */}
                {editModal.type === 'ctas' && (
                  <>
                    <div>
                      <label className="block text-sm text-slate-300 mb-1">Goal</label>
                      <select
                        value={editModal.data.goal}
                        onChange={(e) => setEditModal(prev => ({ ...prev, data: { ...prev.data, goal: e.target.value } }))}
                        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white"
                      >
                        <option value="">Select goal</option>
                        {['Get Followers', 'Drive Traffic', 'Sell Products', 'Build Community', 'Get Leads', 'Book Calls', 'Grow Email List'].map(g => (
                          <option key={g} value={g}>{g}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-300 mb-1">Template</label>
                      <textarea
                        value={editModal.data.template}
                        onChange={(e) => setEditModal(prev => ({ ...prev, data: { ...prev.data, template: e.target.value } }))}
                        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white h-24"
                      />
                    </div>
                  </>
                )}

                {/* Emojis */}
                {editModal.type === 'emojis' && (
                  <>
                    <div>
                      <label className="block text-sm text-slate-300 mb-1">Tone</label>
                      <select
                        value={editModal.data.tone}
                        onChange={(e) => setEditModal(prev => ({ ...prev, data: { ...prev.data, tone: e.target.value } }))}
                        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white"
                      >
                        <option value="">Select tone</option>
                        {['Professional', 'Bold', 'Friendly', 'Inspiring', 'Witty', 'Minimal', 'Luxurious', 'Edgy'].map(t => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-300 mb-1">Emojis (space separated)</label>
                      <input
                        type="text"
                        value={editModal.data.emojis?.join(' ') || ''}
                        onChange={(e) => setEditModal(prev => ({ ...prev, data: { ...prev.data, emojis: e.target.value.split(' ').filter(Boolean) } }))}
                        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white text-xl"
                        placeholder="✨ 💼 🚀"
                      />
                    </div>
                  </>
                )}
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setEditModal({ open: false, type: '', data: null, isNew: false })}
                  className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg"
                  data-testid="save-btn"
                >
                  <Save className="w-4 h-4" /> Save
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {deleteConfirm.open && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-md">
              <div className="flex items-center gap-3 mb-4">
                <AlertTriangle className="w-8 h-8 text-red-400" />
                <h3 className="text-xl font-bold text-white">Confirm Delete</h3>
              </div>
              <p className="text-slate-400 mb-6">Are you sure you want to delete this item? This action cannot be undone.</p>
              <div className="flex gap-3">
                <button
                  onClick={() => setDeleteConfirm({ open: false, type: '', id: '' })}
                  className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg"
                  data-testid="confirm-delete-btn"
                >
                  <Trash2 className="w-4 h-4" /> Delete
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BioTemplatesAdmin;
