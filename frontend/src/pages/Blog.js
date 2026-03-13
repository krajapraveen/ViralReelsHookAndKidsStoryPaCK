import React, { useState, useEffect, useRef } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { 
  ArrowLeft, Calendar, Eye, Tag, Clock, Search, ChevronRight,
  Sparkles, BookOpen, Share2, Twitter, Facebook, Linkedin
} from 'lucide-react';
import analytics from '../utils/analytics';

const API_URL = process.env.REACT_APP_BACKEND_URL;

function BlogList() {
  const [posts, setPosts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchPosts();
    fetchCategories();
  }, [selectedCategory]);

  const fetchPosts = async () => {
    try {
      setLoading(true);
      let url = `${API_URL}/api/blog/posts?limit=20`;
      if (selectedCategory) {
        url += `&category=${encodeURIComponent(selectedCategory)}`;
      }
      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        setPosts(data.posts || []);
      }
    } catch (error) {
      console.error('Error fetching posts:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_URL}/api/blog/categories`);
      if (response.ok) {
        const data = await response.json();
        setCategories(data.categories || []);
      }
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const filteredPosts = posts.filter(post =>
    post.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    post.excerpt.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-sm border-b border-slate-700/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-xl flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white">Visionary Suite Blog</span>
          </Link>
          <div className="flex gap-3">
            <Link to="/signup">
              <Button className="bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600">
                Get Started Free
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="py-16 px-4 text-center">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
          Creator Tips & Resources
        </h1>
        <p className="text-slate-400 text-lg max-w-2xl mx-auto mb-8">
          Learn how to grow your audience, create viral content, and monetize your creativity with AI-powered tools.
        </p>
        
        {/* Search */}
        <div className="max-w-xl mx-auto relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search articles..."
            className="w-full bg-slate-800/50 border border-slate-700 rounded-full pl-12 pr-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            data-testid="blog-search"
          />
        </div>
      </section>

      <div className="max-w-7xl mx-auto px-4 pb-20">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Main Content */}
          <div className="flex-1">
            {/* Category Filters */}
            <div className="flex flex-wrap gap-2 mb-8">
              <button
                onClick={() => setSelectedCategory(null)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  !selectedCategory
                    ? 'bg-indigo-500 text-white'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                }`}
              >
                All Posts
              </button>
              {categories.map((cat) => (
                <button
                  key={cat.name}
                  onClick={() => setSelectedCategory(cat.name)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                    selectedCategory === cat.name
                      ? 'bg-indigo-500 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  {cat.name} ({cat.count})
                </button>
              ))}
            </div>

            {/* Posts Grid */}
            {loading ? (
              <div className="flex justify-center py-20">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
              </div>
            ) : filteredPosts.length === 0 ? (
              <div className="text-center py-20">
                <BookOpen className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-white mb-2">No posts found</h3>
                <p className="text-slate-400">Check back soon for new content!</p>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 gap-6">
                {filteredPosts.map((post) => (
                  <Link
                    key={post.id}
                    to={`/blog/${post.slug}`}
                    className="group bg-slate-800/50 rounded-2xl border border-slate-700/50 overflow-hidden hover:border-indigo-500/50 transition-all"
                    data-testid={`blog-post-${post.slug}`}
                  >
                    {post.featuredImage && (
                      <div className="aspect-video bg-slate-900 overflow-hidden">
                        <img 
                          src={post.featuredImage} 
                          alt={post.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                      </div>
                    )}
                    <div className="p-6">
                      <div className="flex items-center gap-2 mb-3">
                        <span className="px-3 py-1 bg-indigo-500/20 text-indigo-400 text-xs font-medium rounded-full">
                          {post.category}
                        </span>
                        <span className="text-slate-500 text-xs flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          5 min read
                        </span>
                      </div>
                      <h2 className="text-xl font-bold text-white mb-2 group-hover:text-indigo-400 transition-colors">
                        {post.title}
                      </h2>
                      <p className="text-slate-400 text-sm line-clamp-2 mb-4">
                        {post.excerpt}
                      </p>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-500 flex items-center gap-1">
                          <Calendar className="w-4 h-4" />
                          {new Date(post.publishedAt).toLocaleDateString()}
                        </span>
                        <span className="text-slate-500 flex items-center gap-1">
                          <Eye className="w-4 h-4" />
                          {post.views || 0} views
                        </span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <aside className="lg:w-80">
            {/* CTA Card */}
            <div className="bg-gradient-to-br from-indigo-500/20 to-purple-500/20 rounded-2xl border border-indigo-500/30 p-6 mb-6">
              <h3 className="text-lg font-bold text-white mb-2">Try Visionary Suite Free</h3>
              <p className="text-slate-400 text-sm mb-4">
                Get 10 free credits and start creating viral content in seconds.
              </p>
              <Link to="/signup">
                <Button className="w-full bg-gradient-to-r from-indigo-500 to-purple-500">
                  Get Started Free
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </Link>
            </div>

            {/* Categories */}
            <div className="bg-slate-800/50 rounded-2xl border border-slate-700/50 p-6">
              <h3 className="text-lg font-bold text-white mb-4">Categories</h3>
              <div className="space-y-2">
                {categories.map((cat) => (
                  <button
                    key={cat.name}
                    onClick={() => setSelectedCategory(cat.name)}
                    className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-slate-700/50 transition-colors text-left"
                  >
                    <span className="text-slate-300">{cat.name}</span>
                    <span className="text-slate-500 text-sm">{cat.count}</span>
                  </button>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-slate-900 border-t border-slate-800 py-8">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-slate-500">© 2026 Visionary Suite. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

function BlogPost() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const startTimeRef = useRef(null);
  const hasTrackedViewRef = useRef(false);

  useEffect(() => {
    fetchPost();
    startTimeRef.current = Date.now();
    
    // Track read completion on scroll to bottom
    const handleScroll = () => {
      const scrollHeight = document.documentElement.scrollHeight;
      const scrollTop = window.scrollY;
      const clientHeight = window.innerHeight;
      
      if (scrollTop + clientHeight >= scrollHeight - 100 && post && !hasTrackedViewRef.current) {
        hasTrackedViewRef.current = true;
        const readTime = Math.floor((Date.now() - startTimeRef.current) / 1000);
        analytics.trackBlogReadComplete(slug, readTime);
      }
    };
    
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [slug, post]);

  const fetchPost = async () => {
    try {
      const response = await fetch(`${API_URL}/api/blog/posts/${slug}`);
      if (response.ok) {
        const data = await response.json();
        setPost(data.post);
        // Track blog view
        if (data.post) {
          analytics.trackBlogView(slug, data.post.title, data.post.category);
        }
      } else {
        navigate('/blog');
      }
    } catch (error) {
      console.error('Error fetching post:', error);
      navigate('/blog');
    } finally {
      setLoading(false);
    }
  };

  const shareUrl = typeof window !== 'undefined' ? window.location.href : '';
  const shareText = post ? `${post.title} - Visionary Suite Blog` : '';

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  if (!post) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-sm border-b border-slate-700/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/blog" className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
            <ArrowLeft className="w-5 h-5" />
            Back to Blog
          </Link>
          <div className="flex gap-3">
            <Link to="/signup">
              <Button className="bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600">
                Try Free
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <article className="max-w-4xl mx-auto px-4 py-12">
        {/* Meta */}
        <div className="flex items-center gap-4 mb-6">
          <span className="px-3 py-1 bg-indigo-500/20 text-indigo-400 text-sm font-medium rounded-full">
            {post.category}
          </span>
          <span className="text-slate-500 text-sm flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            {new Date(post.publishedAt).toLocaleDateString('en-US', { 
              month: 'long', 
              day: 'numeric', 
              year: 'numeric' 
            })}
          </span>
          <span className="text-slate-500 text-sm flex items-center gap-1">
            <Eye className="w-4 h-4" />
            {post.views} views
          </span>
        </div>

        {/* Title */}
        <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-6 leading-tight">
          {post.title}
        </h1>

        {/* Author */}
        <div className="flex items-center gap-3 mb-8 pb-8 border-b border-slate-800">
          <div className="w-12 h-12 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full flex items-center justify-center text-white font-bold">
            {post.author?.charAt(0) || 'A'}
          </div>
          <div>
            <p className="text-white font-medium">{post.author}</p>
            <p className="text-slate-500 text-sm">Visionary Suite Team</p>
          </div>
        </div>

        {/* Featured Image */}
        {post.featuredImage && (
          <div className="aspect-video bg-slate-900 rounded-2xl overflow-hidden mb-8">
            <img 
              src={post.featuredImage} 
              alt={post.title}
              className="w-full h-full object-cover"
            />
          </div>
        )}

        {/* Content */}
        <div 
          className="prose prose-invert prose-lg max-w-none
            prose-headings:text-white prose-headings:font-bold
            prose-h1:text-3xl prose-h2:text-2xl prose-h3:text-xl
            prose-p:text-slate-300 prose-p:leading-relaxed
            prose-a:text-indigo-400 prose-a:no-underline hover:prose-a:underline
            prose-strong:text-white
            prose-ul:text-slate-300 prose-ol:text-slate-300
            prose-li:marker:text-indigo-500
            prose-blockquote:border-indigo-500 prose-blockquote:text-slate-400
            prose-code:text-indigo-400 prose-code:bg-slate-800 prose-code:px-1 prose-code:rounded
            prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-700"
          dangerouslySetInnerHTML={{ __html: post.content.replace(/\n/g, '<br>') }}
        />

        {/* Tags */}
        {post.tags && post.tags.length > 0 && (
          <div className="mt-12 pt-8 border-t border-slate-800">
            <div className="flex items-center gap-2 flex-wrap">
              <Tag className="w-4 h-4 text-slate-500" />
              {post.tags.map((tag) => (
                <span 
                  key={tag}
                  className="px-3 py-1 bg-slate-800 text-slate-400 text-sm rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Share */}
        <div className="mt-8 pt-8 border-t border-slate-800">
          <p className="text-slate-400 mb-4">Share this article:</p>
          <div className="flex gap-3">
            <a
              href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="p-3 bg-slate-800 hover:bg-slate-700 rounded-xl transition-colors"
            >
              <Twitter className="w-5 h-5 text-slate-400" />
            </a>
            <a
              href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="p-3 bg-slate-800 hover:bg-slate-700 rounded-xl transition-colors"
            >
              <Facebook className="w-5 h-5 text-slate-400" />
            </a>
            <a
              href={`https://www.linkedin.com/shareArticle?mini=true&url=${encodeURIComponent(shareUrl)}&title=${encodeURIComponent(shareText)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="p-3 bg-slate-800 hover:bg-slate-700 rounded-xl transition-colors"
            >
              <Linkedin className="w-5 h-5 text-slate-400" />
            </a>
          </div>
        </div>

        {/* CTA */}
        <div className="mt-12 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-2xl border border-indigo-500/30 p-8 text-center">
          <h3 className="text-2xl font-bold text-white mb-2">Ready to Create Viral Content?</h3>
          <p className="text-slate-400 mb-6">Get 10 free credits and start creating in seconds.</p>
          <Link to="/signup">
            <Button size="lg" className="bg-gradient-to-r from-indigo-500 to-purple-500">
              Get Started Free
              <ChevronRight className="w-5 h-5 ml-1" />
            </Button>
          </Link>
        </div>
      </article>

      {/* Footer */}
      <footer className="bg-slate-900 border-t border-slate-800 py-8">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-slate-500">© 2026 Visionary Suite. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default function Blog() {
  const { slug } = useParams();
  
  if (slug) {
    return <BlogPost />;
  }
  
  return <BlogList />;
}
