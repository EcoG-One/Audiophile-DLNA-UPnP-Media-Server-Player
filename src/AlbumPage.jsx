import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { usePlayerStore } from './store';

export default function AlbumPage() {
  const { albumId } = useParams();
  const navigate = useNavigate();
  const [albumData, setAlbumData] = useState(null);
  
  // NEW: Track which edition is currently selected in the UI
  const [selectedEditionIndex, setSelectedEditionIndex] = useState(0);

  // Connect to global audio player
  const { playTrack, setPlaylist, currentTrack, isPlaying } = usePlayerStore();

  useEffect(() => {
    fetch(`/api/albums/${encodeURIComponent(albumId)}`)
      .then(res => res.json())
      .then(data => {
        setAlbumData(data);
        // Reset to the first edition whenever a new album loads
        setSelectedEditionIndex(0); 
      })
      .catch(err => console.error("Failed to load album:", err));
  }, [albumId]);

  if (!albumData || !albumData.editions || albumData.editions.length === 0) {
    return <div className="text-gray-500 text-center py-20 animate-pulse">Loading High-Res Audio...</div>;
  }

  const activeEdition = albumData.editions[selectedEditionIndex];

  // Helper to format duration
  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // Play a specific track and load the rest of THIS edition into the queue
  const handlePlayTrack = (trackIndex) => {
    const playlist = activeEdition.tracks.map(t => ({
      ...t,
      artist: t.artist || albumData.artist,
      album: albumData.title,
      art: activeEdition.art_hash
    }));
    
    setPlaylist(playlist);
    playTrack(playlist[trackIndex]);
  };

  return (
    <div className="w-full max-w-screen-xl mx-auto px-6 py-8 pb-32 animate-fade-in text-white">
      
      {/* Back Button */}
      <button 
        onClick={() => navigate(-1)}
        className="flex items-center text-gray-400 hover:text-blue-400 transition-colors mb-8 focus:outline-none"
      >
        <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Back
      </button>

      {/* Hero Section */}
      <div className="flex flex-col md:flex-row gap-10 mb-12">
        {/* Large Artwork */}
        <div className="flex-shrink-0 w-64 h-64 md:w-80 md:h-80 shadow-2xl rounded-lg overflow-hidden bg-gray-800 border border-gray-700">
          {activeEdition.art_hash ? (
            <img 
              src={`/art/${activeEdition.art_hash}`} 
              alt={albumData.title} 
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-600 text-6xl">💿</div>
          )}
        </div>

        {/* Details & Controls */}
        <div className="flex flex-col justify-end">
          <h2 className="text-sm font-bold text-blue-400 uppercase tracking-widest mb-2">Album</h2>
          <h1 className="text-4xl md:text-6xl font-extrabold mb-4 leading-tight">{albumData.title}</h1>
          <h2 className="text-2xl text-gray-400 mb-6">{albumData.artist}</h2>
          
          {/* EDITIONS SELECTOR: Only shows if there are multiple versions */}
          {albumData.editions.length > 1 && (
            <div className="mb-6">
              <label className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">Select Edition:</label>
              <div className="flex flex-wrap gap-2">
                {albumData.editions.map((edition, idx) => (
                  <button
                    key={edition.id}
                    onClick={() => setSelectedEditionIndex(idx)}
                    className={`px-4 py-2 rounded-full text-sm font-medium border transition-colors ${
                      idx === selectedEditionIndex 
                        ? 'bg-blue-600 border-blue-500 text-white shadow-lg' 
                        : 'bg-gray-900 border-gray-700 text-gray-400 hover:bg-gray-800'
                    }`}
                  >
                    {edition.edition_title || `Edition ${idx + 1}`}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Tracks Table for Active Edition */}
      <div className="bg-gray-900 bg-opacity-50 rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-left text-gray-300">
          <thead className="bg-gray-900/80 text-gray-500 text-xs uppercase border-b border-gray-800">
            <tr>
              <th className="px-6 py-4 w-16 text-center">Disc</th>
              <th className="px-6 py-4 w-16 text-center">#</th>
              <th className="px-6 py-4">Title</th>
              <th className="px-6 py-4">Artist</th>
              <th className="px-6 py-4 text-right w-32">Duration</th>
            </tr>
          </thead>
          <tbody>
            {activeEdition.tracks.map((track, index) => {
              const isCurrentlyPlaying = currentTrack?.id === track.id;

              return (
                <tr 
                  key={track.id} 
                  onClick={() => handlePlayTrack(index)}
                  className={`group border-b border-gray-800 hover:bg-gray-800/80 transition-colors cursor-pointer ${isCurrentlyPlaying ? 'bg-gray-800 border-l-4 border-l-blue-500' : 'border-l-4 border-l-transparent'}`}
                >
                  <td className="px-6 py-4 text-center font-mono text-gray-500">{track.disc_number || 1}</td>
                  
                  {/* Track Number / Play Icon */}
                  <td className="px-6 py-4 text-center font-mono text-gray-500 group-hover:text-white">
                    {isCurrentlyPlaying && isPlaying ? (
                       <span className="text-blue-500">▶</span>
                    ) : (
                      <span className="block group-hover:hidden">{track.track_number}</span>
                    )}
                    {!isCurrentlyPlaying && (
                      <span className="hidden group-hover:block text-blue-400">▶</span>
                    )}
                  </td>
                  
                  <td className={`px-6 py-4 font-medium ${isCurrentlyPlaying ? 'text-blue-400' : 'text-gray-100'}`}>{track.title}</td>
                  <td className="px-6 py-4 text-sm text-gray-400">{track.artist}</td>
                  <td className="px-6 py-4 text-right font-mono text-sm text-gray-500">{formatTime(track.duration)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}