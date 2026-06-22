import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useLibraryStore } from './store';
import AlbumGrid from './AlbumGrid';
import ArtistGrid from './ArtistGrid';

export default function DiscoveryView() {
  const navigate = useNavigate();
  
  // 1. URL-Driven State
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'albums';

  // 2. Cached Global State
  const { albums, artists, fetchAlbums, fetchArtists, albumsLoaded, artistsLoaded } = useLibraryStore();

  // Fetch only what we need, and only if it isn't already cached
  useEffect(() => {
    if (activeTab === 'albums') fetchAlbums();
    if (activeTab === 'artists') fetchArtists();
  }, [activeTab, fetchAlbums, fetchArtists]);

  // Determine loading state based on the active tab
  const isLoading = activeTab === 'albums' ? !albumsLoaded : !artistsLoaded;
  const items = activeTab === 'albums' ? albums : artists;

  // Change tab by pushing a new URL parameter
  const handleTabChange = (tab) => {
    setSearchParams({ tab });
  };

  return (
    <div className="w-full max-w-screen-2xl mx-auto px-6 py-8 pb-32 animate-fade-in">
      
      {/* Header & Tabs */}
      <div className="flex items-end justify-between mb-8 border-b border-gray-800 pb-4">
        <h1 className="text-4xl font-extrabold tracking-tight text-white">Library</h1>
        
        <div className="flex space-x-6 text-lg font-medium">
          <button 
            onClick={() => handleTabChange('albums')}
            className={`transition-colors ${activeTab === 'albums' ? 'text-blue-500 border-b-2 border-blue-500' : 'text-gray-400 hover:text-white focus:outline-none'}`}
          >
            Albums
          </button>
          <button 
            onClick={() => handleTabChange('artists')}
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
        /* Render Grids */
        activeTab === 'albums' 
          ? <AlbumGrid albums={items} onAlbumClick={(id) => navigate(`/album/${encodeURIComponent(id)}`)} /> 
          : <ArtistGrid artists={items} onArtistClick={(name) => navigate(`/artist/${encodeURIComponent(name)}`)} />
      )}
    </div>
  );
}