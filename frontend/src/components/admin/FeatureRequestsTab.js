import React, { useState } from 'react';
import { Lightbulb, PieChart, MessageSquare, TrendingUp, ThumbsUp } from 'lucide-react';

const statusColors = {
  PENDING: 'bg-yellow-500/20 text-yellow-400',
  UNDER_REVIEW: 'bg-blue-500/20 text-blue-400',
  PLANNED: 'bg-purple-500/20 text-purple-400',
  IN_PROGRESS: 'bg-indigo-500/20 text-indigo-400',
  COMPLETED: 'bg-green-500/20 text-green-400',
  DECLINED: 'bg-red-500/20 text-red-400',
};

export default function FeatureRequestsTab({ data, onUpdateStatus }) {
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [adminResponse, setAdminResponse] = useState('');

  const handleStatusChange = (featureId, newStatus) => {
    onUpdateStatus(featureId, newStatus, adminResponse);
    setSelectedFeature(null);
    setAdminResponse('');
  };

  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Summary Stats */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-yellow-400" />
          Feature Requests Summary
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-4 bg-slate-600/50 rounded-lg">
            <div className="text-3xl font-bold text-yellow-400">{data?.totalRequests || 0}</div>
            <div className="text-sm text-slate-400">Total Requests</div>
          </div>
          <div className="text-center p-4 bg-slate-600/50 rounded-lg">
            <div className="text-3xl font-bold text-purple-400">{data?.totalVotes || 0}</div>
            <div className="text-sm text-slate-400">Total Votes</div>
          </div>
        </div>
      </div>

      {/* Status Breakdown */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4">Status Breakdown</h3>
        <div className="space-y-2">
          {data?.byStatus && Object.entries(data.byStatus).map(([status, count]) => (
            <div key={status} className="flex items-center justify-between p-2 bg-slate-600/50 rounded-lg">
              <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[status]}`}>
                {status.replace('_', ' ')}
              </span>
              <span className="font-bold">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <PieChart className="w-5 h-5 text-indigo-400" />
          By Category
        </h3>
        <div className="space-y-2">
          {data?.byCategory?.map((cat, i) => (
            <div key={i} className="flex items-center justify-between p-2 bg-slate-600/50 rounded-lg">
              <span className="text-sm">{cat.category.replace('_', ' ')}</span>
              <span className="font-bold text-indigo-400">{cat.count}</span>
            </div>
          ))}
          {(!data?.byCategory || data.byCategory.length === 0) && (
            <div className="text-center text-slate-400 py-4">No data yet</div>
          )}
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-green-400" />
          Managing Requests
        </h3>
        <div className="text-sm text-slate-400 space-y-2">
          <p>• Click on a feature request below to update its status</p>
          <p>• Add admin response to communicate with users</p>
          <p>• Status options: Pending, Under Review, Planned, In Progress, Completed, Declined</p>
          <p>• Users can vote on features they want to see implemented</p>
        </div>
      </div>

      {/* Top Requested Features */}
      <div className="md:col-span-2 bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-purple-400" />
          Top Requested Features (by votes)
        </h3>
        <div className="space-y-3">
          {data?.topRequests?.map((feature, i) => (
            <div 
              key={feature.id} 
              className={`p-4 bg-slate-600/50 rounded-lg cursor-pointer hover:bg-slate-600 transition-colors ${
                selectedFeature === feature.id ? 'ring-2 ring-purple-500' : ''
              }`}
              onClick={() => setSelectedFeature(selectedFeature === feature.id ? null : feature.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg font-bold text-purple-400">#{i + 1}</span>
                    <h4 className="font-semibold">{feature.title}</h4>
                  </div>
                  <p className="text-sm text-slate-400 mb-2">{feature.description}</p>
                  <div className="flex flex-wrap gap-2">
                    <span className="px-2 py-1 bg-slate-500/30 rounded text-xs">
                      {feature.category.replace('_', ' ')}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[feature.status]}`}>
                      {feature.status.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-slate-500">
                      {new Date(feature.createdAt).toLocaleDateString()}
                    </span>
                  </div>
                  {feature.adminResponse && (
                    <div className="mt-2 p-2 bg-purple-500/10 rounded text-sm">
                      <span className="text-purple-400 font-medium">Admin Response: </span>
                      {feature.adminResponse}
                    </div>
                  )}
                </div>
                <div className="flex flex-col items-center ml-4">
                  <ThumbsUp className="w-5 h-5 text-green-400" />
                  <span className="text-xl font-bold text-green-400">{feature.voteCount}</span>
                  <span className="text-xs text-slate-500">votes</span>
                </div>
              </div>
              
              {/* Status Update Panel */}
              {selectedFeature === feature.id && (
                <div className="mt-4 pt-4 border-t border-slate-500">
                  <div className="grid grid-cols-3 gap-2 mb-3">
                    {['PENDING', 'UNDER_REVIEW', 'PLANNED', 'IN_PROGRESS', 'COMPLETED', 'DECLINED'].map((status) => (
                      <button
                        key={status}
                        onClick={(e) => { e.stopPropagation(); handleStatusChange(feature.id, status); }}
                        className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                          feature.status === status 
                            ? statusColors[status] + ' ring-2 ring-white/50'
                            : 'bg-slate-500/30 hover:bg-slate-500/50'
                        }`}
                      >
                        {status.replace('_', ' ')}
                      </button>
                    ))}
                  </div>
                  <input
                    type="text"
                    placeholder="Add admin response (optional)"
                    value={adminResponse}
                    onChange={(e) => setAdminResponse(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="w-full p-2 bg-slate-700 border border-slate-600 rounded text-sm"
                  />
                </div>
              )}
            </div>
          ))}
          {(!data?.topRequests || data.topRequests.length === 0) && (
            <div className="text-center text-slate-400 py-8">
              <Lightbulb className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No feature requests yet</p>
              <p className="text-sm">Users can submit feature requests from the app</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
