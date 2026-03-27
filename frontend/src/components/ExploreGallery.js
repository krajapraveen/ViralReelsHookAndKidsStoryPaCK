import React, { useState, useEffect } from 'react';
import axios from 'axios';

const FALLBACK_STORIES = [
    {
        id: 'seed-1',
        title: 'The Whispering Woods',
        video_url: 'https://assets.mixkit.co/videos/preview/mixkit-mysterious-forest-with-low-fog-830-large.mp4',
        thumbnail_url: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800',
        hook: 'What lies behind the ancient oak tree?'
    },
    {
        id: 'seed-2',
        title: 'Space Cadet Luna',
        video_url: 'https://assets.mixkit.co/videos/preview/mixkit-stars-in-space-1610-large.mp4',
        thumbnail_url: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800',
        hook: 'The engines failed, but the stars started singing...'
    },
    {
        id: 'seed-3',
        title: 'Deep Sea Discovery',
        video_url: 'https://assets.mixkit.co/videos/preview/mixkit-underwater-ocean-bubbles-moving-up-4015-large.mp4',
        thumbnail_url: 'https://images.unsplash.com/photo-1551244072-5d12893278ab?w=800',
        hook: 'A golden city hidden for a thousand years.'
    }
];

const ExploreGallery = () => {
    const [stories, setStories] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStories = async () => {
            try {
                const res = await axios.get('/api/story-engine/explore');
                if (res.data && res.data.length > 0) {
                    setStories(res.data);
                } else {
                    console.warn("API returned empty, using fallback seeds");
                    setStories(FALLBACK_STORIES);
                }
            } catch (err) {
                console.error("Failed to load stories, triggering fallback", err);
                setStories(FALLBACK_STORIES);
            } finally {
                setLoading(false);
            }
        };
        fetchStories();
    }, []);

    if (loading) return <div className="p-8 text-center">Loading amazing stories...</div>;

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
            {stories.map((story) => (
                <div key={story.id} className="bg-card rounded-xl overflow-hidden shadow-lg border border-border hover:scale-[1.02] transition-transform">
                    <div className="aspect-video relative group">
                        <img 
                            src={story.thumbnail_url} 
                            alt={story.title} 
                            className="w-full h-full object-cover"
                            onError={(e) => { e.target.src = 'https://placehold.co/600x400?text=Video+Preview'; }}
                        />
                        <div className="absolute inset-0 bg-black/20 group-hover:bg-black/40 flex items-center justify-center transition-colors">
                            <button className="bg-primary text-white p-3 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                                ▶ Play
                            </button>
                        </div>
                    </div>
                    <div className="p-4">
                        <h3 className="text-lg font-bold mb-1">{story.title}</h3>
                        <p className="text-muted-pro text-sm italic">"{story.hook}"</p>
                        <button className="mt-4 w-full bg-secondary py-2 rounded-lg font-semibold text-white">
                            Continue Story
                        </button>
                    </div>
                </div>
            ))}
        </div>
    );
};

export default ExploreGallery;