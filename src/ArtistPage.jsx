import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import AlbumGrid from './AlbumGrid';

export default function ArtistPage() {
  const { artistName } = useParams();
  const navigate = useNavigate();
  const [artistData, setArtistData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    fetch(`/api/artists/${encodeURIComponent(artistName)}`)
      .then(res => res.json())
      .then(data => {
        setArtistData(data);
        setIsLoading(false);
      })
      .catch(err => {
        console.error("Failed to load artist:", err);
        setIsLoading(false);
      });
  }, [artistName]);

  if (isLoading) {
    return <div className="text-gray-500 text-center py-20 animate-pulse">Loading Discography...</div>;
  }

  if (!artistData) return null;

  return (
    <div className="w-full max-w-screen-xl mx-auto px-6 py-8 pb-32 animate-fade-in text-white">
      
      {/* Back Button */}
      <button 
        onClick={() => navigate(-1)} // Takes user back to previous history state!
        className="flex items-center text-gray-400 hover:text-blue-400 transition-colors mb-8"
      >
        Back
      </button>

      {/* Hero Section */}
      <div className="flex items-center gap-8 mb-12 border-b border-gray-800 pb-8">
        <div className="flex-shrink-0 w-32 h-32 md:w-48 md:h-48 rounded-full bg-gray-800 flex items-center justify-center text-6xl shadow-xl border-4 border-gray-900">
          🎤
        </div>
        <div>
          <h2 className="text-sm font-bold text-blue-400 uppercase tracking-widest mb-2">Artist</h2>
          <h1 className="text-4xl md:text-6xl font-extrabold mb-4">{artistData.name}</h1>
          <p className="text-gray-400 text-lg">
            {artistData.albums.length} Album{artistData.albums.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {/* Discography Grid */}
      <div className="mb-6">
        <h3 className="text-2xl font-bold mb-6 text-gray-100">Discography</h3>
        {/*  When clicking an album in the artist's grid, push to the new URL: */}
        <AlbumGrid 
          albums={artistData.albums} 
          onAlbumClick={(id) => navigate(`/album/${encodeURIComponent(id)}`)} 
        />
      </div>
    </div>
  );
}