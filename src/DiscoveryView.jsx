import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AlbumGrid from './AlbumGrid';
import ArtistGrid from './ArtistGrid';

export default function DiscoveryView() {
  const [activeTab, setActiveTab] = useState('albums');
  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  // The perfectly clean fetch logic (no more selectedAlbum checks!)
  useEffect(() => {
    setIsLoading(true);
    const endpoint = activeTab === 'albums' ? '/api/albums' : '/api/artists';
    
    fetch(endpoint)
      .then(res => res.json())
      .then(data => {
        setItems(data);
        setIsLoading(false);
      })
      .catch(err => {
        console.error("Failed to load library:", err);
        setIsLoading(false);
      });
  }, [activeTab]); // We only care about the active tab changing now

  return (
    <div className="w-full max-w-screen-2xl mx-auto px-6 py-8 pb-32 animate-fade-in">
      
      {/* Header & Tabs */}
      <div className="flex items-end justify-between mb-8 border-b border-gray-800 pb-4">
        <h1 className="text-4xl font-extrabold tracking-tight text-white">Library</h1>
        
        <div className="flex space-x-6 text-lg font-medium">
          <button 
            onClick={() => setActiveTab('albums')}
            className={`transition-colors ${activeTab === 'albums' ? 'text-blue-500 border-b-2 border-blue-500' : 'text-gray-400 hover:text-white focus:outline-none'}`}
          >
            Albums
          </button>
          <button 
            onClick={() => setActiveTab('artists')}
            className={`transition-colors ${activeTab === 'artists' ? 'text-blue-500 border-b-2 border-blue-500' : 'text-gray-400 hover:text-white focus:outline-none'}`}
          >
            Artists
          </button>
        </div>
      </div>

      {/* Loading State */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-pulse flex space-x-4">
            <div className="w-12 h-12 bg-gray-800 rounded-full"></div>
            <div className="w-12 h-12 bg-gray-800 rounded-full"></div>
            <div className="w-12 h-12 bg-gray-800 rounded-full"></div>
          </div>
        </div>
      ) : (
        /* Render Grids & wire them directly to the Router URL */
        activeTab === 'albums' 
          ? <AlbumGrid albums={items} onAlbumClick={(id) => navigate(`/album/${encodeURIComponent(id)}`)} /> 
          : <ArtistGrid artists={items} onArtistClick={(name) => navigate(`/artist/${encodeURIComponent(name)}`)} />
      )}
    </div>
  );
}