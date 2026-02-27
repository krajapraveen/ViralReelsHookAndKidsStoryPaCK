import React, { useState, useEffect } from 'react';
import { 
  Zap, Layout, BookOpen, Lock, Unlock, ShoppingCart, 
  Filter, Search, ChevronRight, Star, Check, Crown,
  ArrowLeft, Sparkles, Copy, CheckCircle, Tag
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const ContentBlueprintLibrary = () => {
  const [activeTab, setActiveTab] = useState('catalog');
  const [catalog, setCatalog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [productData, setProductData] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [copiedId, setCopiedId] = useState(null);
  const [purchaseLoading, setPurchaseLoading] = useState(false);
  const [userCredits, setUserCredits] = useState(0);

  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchCatalog();
  }, []);

  const fetchCatalog = async () => {
    try {
      const response = await fetch(`${API_URL}/api/blueprint-library/catalog`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setCatalog(data);
        setUserCredits(data.user_credits || 0);
      }
    } catch (error) {
      console.error('Failed to fetch catalog:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchProductData = async (productId) => {
    setLoading(true);
    try {
      let endpoint = '';
      if (productId === 'viral_hook_bank') endpoint = '/api/blueprint-library/hooks';
      else if (productId === 'reel_frameworks') endpoint = '/api/blueprint-library/frameworks';
      else if (productId === 'kids_story_ideas') endpoint = '/api/blueprint-library/story-ideas';

      const params = new URLSearchParams();
      if (selectedCategory !== 'all') {
        if (productId === 'viral_hook_bank') params.append('niche', selectedCategory);
        else if (productId === 'reel_frameworks') params.append('category', selectedCategory);
        else if (productId === 'kids_story_ideas') params.append('genre', selectedCategory);
      }

      const response = await fetch(`${API_URL}${endpoint}?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setProductData(data);
      }
    } catch (error) {
      console.error('Failed to fetch product data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectProduct = (product) => {
    setSelectedProduct(product);
    setSelectedCategory('all');
    fetchProductData(product.id);
  };

  const handlePurchase = async (productType, tier, itemId = null, category = null) => {
    setPurchaseLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/blueprint-library/purchase`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          product_type: productType,
          purchase_tier: tier,
          item_id: itemId,
          category: category
        })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setUserCredits(data.new_balance);
        // Refresh the product data to show unlocked content
        fetchProductData(productType);
        fetchCatalog();
        alert(`Purchase successful! You spent ${data.credits_spent} credits.`);
      } else {
        alert(data.detail || 'Purchase failed');
      }
    } catch (error) {
      console.error('Purchase failed:', error);
      alert('Purchase failed. Please try again.');
    } finally {
      setPurchaseLoading(false);
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getIconComponent = (iconName) => {
    const icons = { Zap, Layout, BookOpen };
    return icons[iconName] || Sparkles;
  };

  if (loading && !catalog) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-400">Loading Blueprint Library...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 text-white" data-testid="blueprint-library-page">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {selectedProduct ? (
                <Button 
                  variant="ghost" 
                  onClick={() => {setSelectedProduct(null); setProductData(null);}}
                  className="text-slate-400 hover:text-white"
                  data-testid="back-to-catalog-btn"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Catalog
                </Button>
              ) : (
                <>
                  <Sparkles className="w-8 h-8 text-violet-400" />
                  <div>
                    <h1 className="text-2xl font-bold">Content Blueprint Library</h1>
                    <p className="text-slate-400 text-sm">Premium content packs - Zero API cost, instant access</p>
                  </div>
                </>
              )}
            </div>
            <div className="flex items-center gap-4">
              <div className="bg-slate-800 px-4 py-2 rounded-lg">
                <span className="text-slate-400 text-sm">Credits: </span>
                <span className="text-violet-400 font-bold" data-testid="user-credits">{userCredits}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {!selectedProduct ? (
          /* Catalog View */
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6" data-testid="catalog-grid">
            {catalog?.products?.map((product) => {
              const IconComponent = getIconComponent(product.icon);
              return (
                <Card 
                  key={product.id}
                  className="bg-slate-900 border-slate-800 hover:border-violet-500/50 transition-all cursor-pointer group"
                  onClick={() => handleSelectProduct(product)}
                  data-testid={`product-card-${product.id}`}
                >
                  <CardHeader>
                    <div className="flex items-center gap-3 mb-2">
                      <div className="p-2 bg-violet-500/20 rounded-lg">
                        <IconComponent className="w-6 h-6 text-violet-400" />
                      </div>
                      <Badge variant="outline" className="text-violet-400 border-violet-400">
                        {product.item_count} items
                      </Badge>
                    </div>
                    <CardTitle className="text-xl group-hover:text-violet-400 transition-colors">
                      {product.name}
                    </CardTitle>
                    <CardDescription className="text-slate-400">
                      {product.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {/* Categories */}
                      <div className="flex flex-wrap gap-2">
                        {product.categories?.slice(0, 4).map((cat) => (
                          <Badge key={cat} variant="secondary" className="bg-slate-800 text-slate-300">
                            {cat}
                          </Badge>
                        ))}
                        {product.categories?.length > 4 && (
                          <Badge variant="secondary" className="bg-slate-800 text-slate-400">
                            +{product.categories.length - 4} more
                          </Badge>
                        )}
                      </div>

                      {/* Pricing */}
                      <div className="bg-slate-800/50 rounded-lg p-3 space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-400">Single item</span>
                          <span className="text-violet-400 font-medium">
                            {Object.values(product.pricing)[0]} credits
                          </span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-400">Category pack</span>
                          <span className="text-violet-400 font-medium">
                            {Object.values(product.pricing)[1]} credits
                          </span>
                        </div>
                        <div className="flex justify-between text-sm border-t border-slate-700 pt-2">
                          <span className="text-white font-medium flex items-center gap-1">
                            <Crown className="w-4 h-4 text-amber-400" />
                            Full Access
                          </span>
                          <span className="text-amber-400 font-bold">
                            {Object.values(product.pricing)[2]} credits
                          </span>
                        </div>
                      </div>

                      <Button className="w-full bg-violet-600 hover:bg-violet-700">
                        Browse {product.name}
                        <ChevronRight className="w-4 h-4 ml-2" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        ) : (
          /* Product Detail View */
          <div data-testid="product-detail-view">
            {/* Product Header */}
            <div className="mb-6">
              <div className="flex items-center gap-4 mb-4">
                <div className="p-3 bg-violet-500/20 rounded-xl">
                  {React.createElement(getIconComponent(selectedProduct.icon), { className: "w-8 h-8 text-violet-400" })}
                </div>
                <div>
                  <h2 className="text-2xl font-bold">{selectedProduct.name}</h2>
                  <p className="text-slate-400">{selectedProduct.item_count} items available</p>
                </div>
              </div>

              {/* Quick Purchase Options */}
              <div className="flex flex-wrap gap-3 mb-6">
                <Button 
                  onClick={() => handlePurchase(selectedProduct.id, 'full_access')}
                  className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600"
                  disabled={purchaseLoading}
                  data-testid="buy-full-access-btn"
                >
                  <Crown className="w-4 h-4 mr-2" />
                  Buy Full Access ({Object.values(selectedProduct.pricing)[2]} credits)
                </Button>
              </div>

              {/* Filters */}
              <div className="flex flex-wrap gap-4 items-center">
                <div className="relative flex-1 max-w-md">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    placeholder="Search..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 bg-slate-800 border-slate-700"
                    data-testid="search-input"
                  />
                </div>
                <div className="flex gap-2 flex-wrap">
                  <Badge 
                    variant={selectedCategory === 'all' ? 'default' : 'outline'}
                    className={`cursor-pointer ${selectedCategory === 'all' ? 'bg-violet-600' : 'hover:bg-slate-800'}`}
                    onClick={() => {setSelectedCategory('all'); fetchProductData(selectedProduct.id);}}
                  >
                    All
                  </Badge>
                  {selectedProduct.categories?.map((cat) => (
                    <Badge
                      key={cat}
                      variant={selectedCategory === cat ? 'default' : 'outline'}
                      className={`cursor-pointer ${selectedCategory === cat ? 'bg-violet-600' : 'hover:bg-slate-800'}`}
                      onClick={() => {setSelectedCategory(cat); fetchProductData(selectedProduct.id);}}
                    >
                      {cat}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>

            {/* Content Grid */}
            {loading ? (
              <div className="flex justify-center py-12">
                <div className="w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Render based on product type */}
                {selectedProduct.id === 'viral_hook_bank' && productData?.hooks?.map((hook) => (
                  <HookCard 
                    key={hook.id} 
                    hook={hook} 
                    onPurchase={() => handlePurchase(selectedProduct.id, 'single', hook.id)}
                    onCopy={copyToClipboard}
                    copiedId={copiedId}
                    purchaseLoading={purchaseLoading}
                    pricing={selectedProduct.pricing}
                  />
                ))}
                
                {selectedProduct.id === 'reel_frameworks' && productData?.frameworks?.map((framework) => (
                  <FrameworkCard 
                    key={framework.id} 
                    framework={framework}
                    onPurchase={() => handlePurchase(selectedProduct.id, 'single', framework.id)}
                    purchaseLoading={purchaseLoading}
                    pricing={selectedProduct.pricing}
                  />
                ))}
                
                {selectedProduct.id === 'kids_story_ideas' && productData?.ideas?.map((idea) => (
                  <StoryIdeaCard 
                    key={idea.id} 
                    idea={idea}
                    onPurchase={() => handlePurchase(selectedProduct.id, 'single', idea.id)}
                    purchaseLoading={purchaseLoading}
                    pricing={selectedProduct.pricing}
                  />
                ))}
              </div>
            )}

            {/* Pack Purchase Options */}
            {selectedCategory !== 'all' && !productData?.access?.has_full_access && (
              <div className="mt-8 p-4 bg-slate-800/50 rounded-xl border border-slate-700">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-white">Want all {selectedCategory} content?</h3>
                    <p className="text-slate-400 text-sm">Get the entire pack at a discounted price</p>
                  </div>
                  <Button
                    onClick={() => handlePurchase(selectedProduct.id, 'pack', null, selectedCategory)}
                    className="bg-violet-600 hover:bg-violet-700"
                    disabled={purchaseLoading}
                    data-testid="buy-pack-btn"
                  >
                    <Tag className="w-4 h-4 mr-2" />
                    Buy {selectedCategory} Pack ({Object.values(selectedProduct.pricing)[1]} credits)
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

/* Hook Card Component */
const HookCard = ({ hook, onPurchase, onCopy, copiedId, purchaseLoading, pricing }) => {
  return (
    <Card className={`bg-slate-900 border-slate-800 ${hook.is_unlocked ? 'border-green-500/30' : ''}`} data-testid={`hook-card-${hook.id}`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <Badge variant="outline" className="text-violet-400 border-violet-400">
            {hook.niche}
          </Badge>
          {hook.is_unlocked ? (
            <Unlock className="w-4 h-4 text-green-400" />
          ) : (
            <Lock className="w-4 h-4 text-slate-500" />
          )}
        </div>
        
        <p className="text-white font-medium mb-3 min-h-[48px]">
          "{hook.hook_text}"
        </p>
        
        {hook.engagement_score && (
          <div className="flex items-center gap-2 mb-3">
            <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
            <span className="text-sm text-slate-400">
              {hook.engagement_score}% engagement
            </span>
          </div>
        )}

        {hook.is_unlocked ? (
          <div className="space-y-2">
            {hook.variations && (
              <div className="text-xs text-slate-400">
                +{hook.variations.length} variations included
              </div>
            )}
            <Button 
              variant="outline" 
              size="sm" 
              className="w-full"
              onClick={() => onCopy(hook.hook_text, hook.id)}
            >
              {copiedId === hook.id ? (
                <>
                  <CheckCircle className="w-4 h-4 mr-2 text-green-400" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4 mr-2" />
                  Copy Hook
                </>
              )}
            </Button>
          </div>
        ) : (
          <Button 
            size="sm" 
            className="w-full bg-violet-600 hover:bg-violet-700"
            onClick={onPurchase}
            disabled={purchaseLoading}
            data-testid={`buy-hook-${hook.id}`}
          >
            <ShoppingCart className="w-4 h-4 mr-2" />
            Unlock ({Object.values(pricing)[0]} credits)
          </Button>
        )}
      </CardContent>
    </Card>
  );
};

/* Framework Card Component */
const FrameworkCard = ({ framework, onPurchase, purchaseLoading, pricing }) => {
  return (
    <Card className={`bg-slate-900 border-slate-800 ${framework.is_unlocked ? 'border-green-500/30' : ''}`} data-testid={`framework-card-${framework.id}`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <Badge variant="outline" className="text-violet-400 border-violet-400">
            {framework.category}
          </Badge>
          {framework.is_unlocked ? (
            <Unlock className="w-4 h-4 text-green-400" />
          ) : (
            <Lock className="w-4 h-4 text-slate-500" />
          )}
        </div>
        
        <h3 className="text-white font-semibold mb-2">{framework.title}</h3>
        <p className="text-slate-400 text-sm mb-3">{framework.description}</p>
        
        {framework.preview_hook && (
          <div className="bg-slate-800 rounded-lg p-2 mb-3 text-sm italic text-slate-300">
            "{framework.preview_hook}"
          </div>
        )}

        {framework.is_unlocked ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-green-400">
              <Check className="w-3 h-3" />
              Full script included
            </div>
            <div className="flex items-center gap-2 text-xs text-green-400">
              <Check className="w-3 h-3" />
              Scene breakdown
            </div>
            <Button variant="outline" size="sm" className="w-full mt-2">
              View Full Framework
            </Button>
          </div>
        ) : (
          <Button 
            size="sm" 
            className="w-full bg-violet-600 hover:bg-violet-700"
            onClick={onPurchase}
            disabled={purchaseLoading}
            data-testid={`buy-framework-${framework.id}`}
          >
            <ShoppingCart className="w-4 h-4 mr-2" />
            Unlock ({Object.values(pricing)[0]} credits)
          </Button>
        )}
      </CardContent>
    </Card>
  );
};

/* Story Idea Card Component */
const StoryIdeaCard = ({ idea, onPurchase, purchaseLoading, pricing }) => {
  return (
    <Card className={`bg-slate-900 border-slate-800 ${idea.is_unlocked ? 'border-green-500/30' : ''}`} data-testid={`story-idea-card-${idea.id}`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex gap-2">
            <Badge variant="outline" className="text-violet-400 border-violet-400">
              {idea.genre}
            </Badge>
            <Badge variant="outline" className="text-slate-400 border-slate-600">
              {idea.age_group} yrs
            </Badge>
          </div>
          {idea.is_unlocked ? (
            <Unlock className="w-4 h-4 text-green-400" />
          ) : (
            <Lock className="w-4 h-4 text-slate-500" />
          )}
        </div>
        
        <h3 className="text-white font-semibold mb-2">{idea.title}</h3>
        <p className="text-slate-400 text-sm mb-3">{idea.brief_synopsis}</p>

        {idea.is_unlocked ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-green-400">
              <Check className="w-3 h-3" />
              Full synopsis
            </div>
            <div className="flex items-center gap-2 text-xs text-green-400">
              <Check className="w-3 h-3" />
              Character details
            </div>
            <div className="flex items-center gap-2 text-xs text-green-400">
              <Check className="w-3 h-3" />
              Scene outlines
            </div>
            <Button variant="outline" size="sm" className="w-full mt-2">
              View Full Story
            </Button>
          </div>
        ) : (
          <Button 
            size="sm" 
            className="w-full bg-violet-600 hover:bg-violet-700"
            onClick={onPurchase}
            disabled={purchaseLoading}
            data-testid={`buy-story-idea-${idea.id}`}
          >
            <ShoppingCart className="w-4 h-4 mr-2" />
            Unlock ({Object.values(pricing)[0]} credits)
          </Button>
        )}
      </CardContent>
    </Card>
  );
};

export default ContentBlueprintLibrary;
