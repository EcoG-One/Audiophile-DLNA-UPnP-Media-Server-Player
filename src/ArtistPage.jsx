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
<div className="relative w-full aspect-video rounded-xl overflow-hidden mb-12 shadow-2xl border border-gray-800 bg-gray-900">
  
  {/* Background Fanart & Gradient Overlay */}
  {artistData.background ? (
    <div 
      className="absolute inset-0 bg-cover bg-center"
      style={{ backgroundImage: `url(${artistData.background})` }}
    >
      <div className="absolute inset-0 bg-gradient-to-t from-gray-950 via-gray-900/80 to-transparent"></div>
    </div>
  ) : (
    <div className="absolute inset-0 bg-gray-800 bg-gradient-to-tr from-gray-900 to-gray-800"></div>
  )}

  {/* Foreground Metadata & Logo */}
  <div className="absolute inset-0 p-8 flex flex-col justify-end">
    <div className="flex items-end gap-6 z-10">
      {artistData.logo ? (
        <img 
          src={artistData.logo} 
          alt={`${artistData.name} Logo`} 
          className="max-h-24 md:max-h-32 object-contain filter drop-shadow-[0_4px_4px_rgba(0,0,0,0.8)]" 
        />
      ) : (
        <div>
          <h2 className="text-sm font-bold text-blue-400 uppercase tracking-widest mb-2 shadow-black drop-shadow-md">Artist</h2>
          <h1 className="text-4xl md:text-6xl font-extrabold text-white shadow-black drop-shadow-md">{artistData.name}</h1>
        </div>
      )}
    </div>
    
    <p className="text-gray-300 text-lg mt-4 font-medium drop-shadow-md z-10">
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