import { useState, useEffect } from 'react';
import AlbumGrid from './AlbumGrid';
import ArtistGrid from './ArtistGrid';
import AlbumPage from './AlbumPage';
import ArtistPage from './ArtistPage'; // Import the new component

export default function DiscoveryView() {
  const [activeTab, setActiveTab] = useState('albums');
  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Navigation State
  const [selectedAlbum, setSelectedAlbum] = useState(null);
  const [selectedArtist, setSelectedArtist] = useState(null); // NEW

  // Fetch base grid data
  useEffect(() => {
    // Only fetch if we are NOT viewing a specific album or artist
    if (selectedAlbum || selectedArtist) return;

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
  }, [activeTab, selectedAlbum, selectedArtist]);

  // ==========================================
  // NAVIGATION ROUTER
  // ==========================================
  
  // 1. If an Album is selected, show the Album Page
  if (selectedAlbum) {
    return (
      <AlbumPage 
        albumId={selectedAlbum} 
        onBack={() => setSelectedAlbum(null)} 
      />
    );
  }

  // 2. If an Artist is selected, show the Artist Page
  if (selectedArtist) {
    return (
      <ArtistPage 
        artistName={selectedArtist} 
        onBack={() => setSelectedArtist(null)} 
        onAlbumClick={setSelectedAlbum} // Pass the click down so you can open albums from here!
      />
    );
  }

  // 3. Default View: Show the Main Grids
  return (
    <div className="w-full max-w-screen-2xl mx-auto px-6 py-8 pb-32">
      <div className="flex items-end justify-between mb-8 border-b border-gray-800 pb-4">
        <h1 className="text-4xl font-extrabold tracking-tight text-white">Library</h1>
        
        <div className="flex space-x-6 text-lg font-medium">
          <button 
            onClick={() => setActiveTab('albums')}
            className={`transition-colors ${activeTab === 'albums' ? 'text-blue-500 border-b-2 border-blue-500' : 'text-gray-400 hover:text-white'}`}
          >
            Albums
          </button>
          <button 
            onClick={() => setActiveTab('artists')}
            className={`transition-colors ${activeTab === 'artists' ? 'text-blue-500 border-b-2 border-blue-500' : 'text-gray-400 hover:text-white'}`}
          >
            Artists
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-pulse flex space-x-4">
            <div className="w-12 h-12 bg-gray-800 rounded-full"></div>
            <div className="w-12 h-12 bg-gray-800 rounded-full"></div>
            <div className="w-12 h-12 bg-gray-800 rounded-full"></div>
          </div>
        </div>
      ) : (
        activeTab === 'albums' 
          ? <AlbumGrid albums={items} onAlbumClick={setSelectedAlbum} /> 
          : <ArtistGrid artists={items} onArtistClick={setSelectedArtist} /> // FINALLY FIXED!
      )}
    </div>
  );
}