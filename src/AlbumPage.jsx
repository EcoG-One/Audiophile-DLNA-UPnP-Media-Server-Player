import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { usePlayerStore } from './store';

export default function AlbumPage() {
  const { albumId } = useParams();
  const navigate = useNavigate();
  const [albumData, setAlbumData] = useState(null);
  
  // State for selectors
  const [selectedEditionIndex, setSelectedEditionIndex] = useState(0);
  const [selectedDisc, setSelectedDisc] = useState(1);

  // Connect to global audio player
  const { playTrack, setPlaylist, currentTrack, isPlaying } = usePlayerStore();

  useEffect(() => {
    fetch(`/api/albums/${encodeURIComponent(albumId)}`)
      .then(res => res.json())
      .then(data => {
        // --- SMART CONSOLIDATION LAYER ---
        // Merges fragmented multi-disc releases (caused by folder splits) back into a single edition
        if (data.editions) {
          const mergedEditions = [];
          data.editions.forEach(edition => {
            const match = mergedEditions.find(m => 
              m.edition_title === edition.edition_title && 
              m.year === edition.year && 
              m.label === edition.label &&
              m.catalog === edition.catalog
            );

            if (match) {
              match.tracks = [...match.tracks, ...edition.tracks];
            } else {
              mergedEditions.push({ ...edition, tracks: [...edition.tracks] });
            }
          });
          data.editions = mergedEditions;
        }

        setAlbumData(data);
        
        // Reset selections on load
        setSelectedEditionIndex(0); 
        if (data.editions && data.editions.length > 0) {
          const firstEditionDiscs = [...new Set(data.editions[0].tracks.map(t => t.disc_number || 1))].sort((a,b) => a-b);
          setSelectedDisc(firstEditionDiscs[0]);
        }
      })
      .catch(err => console.error("Failed to load album:", err));
  }, [albumId]);

  if (!albumData || !albumData.editions || albumData.editions.length === 0) {
    return <div className="text-gray-500 text-center py-20 animate-pulse">Loading High-Res Audio...</div>;
  }

  // Active Data Lookups
  const activeEdition = albumData.editions[selectedEditionIndex];
  const uniqueDiscs = [...new Set(activeEdition.tracks.map(t => t.disc_number || 1))].sort((a, b) => a - b);
  const displayedTracks = activeEdition.tracks.filter(t => (t.disc_number || 1) === selectedDisc);

  // Handlers
  const handleEditionChange = (idx) => {
    setSelectedEditionIndex(idx);
    const newEditionDiscs = [...new Set(albumData.editions[idx].tracks.map(t => t.disc_number || 1))].sort((a,b) => a-b);
    setSelectedDisc(newEditionDiscs[0]); // Auto-select Disk 1 of the new edition
  };

  const handlePlayTrack = (trackIndex) => {
    // We only load the currently viewed disk into the playlist to preserve predictable ordering
    const playlist = displayedTracks.map(t => ({
      ...t,
      artist: t.artist || albumData.artist,
      album: albumData.title,
      art: activeEdition.art_hash
    }));
    
    setPlaylist(playlist);
    playTrack(playlist[trackIndex]);
  };

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="w-full max-w-screen-xl mx-auto px-6 py-8 pb-32 animate-fade-in text-white">
      
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

        <div className="flex flex-col justify-end">
          <h2 className="text-sm font-bold text-blue-400 uppercase tracking-widest mb-2">Album</h2>
          <h1 className="text-4xl md:text-6xl font-extrabold mb-4 leading-tight">{albumData.title}</h1>
          <h2 className="text-2xl text-gray-400 mb-6">{albumData.artist}</h2>
          
          {/* 1. EDITIONS SELECTOR */}
          {albumData.editions.length > 1 && (
            <div className="mb-4">
              <label className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">Select Edition:</label>
              <div className="flex flex-wrap gap-2">
                {albumData.editions.map((edition, idx) => (
                  <button
                    key={edition.id}
                    onClick={() => handleEditionChange(idx)}
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

          {/* 2. DISK SELECTOR */}
          {uniqueDiscs.length > 1 && (
            <div className="mb-2 mt-2">
              <label className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">Select Disk:</label>
              <div className="flex flex-wrap gap-2">
                {uniqueDiscs.map((disc) => (
                  <button
                    key={`disc-${disc}`}
                    onClick={() => setSelectedDisc(disc)}
                    className={`px-4 py-2 rounded-full text-sm font-medium border transition-colors ${
                      disc === selectedDisc 
                        ? 'bg-gray-100 border-gray-300 text-gray-900 shadow-lg' 
                        : 'bg-gray-900 border-gray-700 text-gray-400 hover:bg-gray-800'
                    }`}
                  >
                    DISK {disc}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Tracks Table for Active Disk */}
      <div className="bg-gray-900 bg-opacity-50 rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-left text-gray-300">
          <thead className="bg-gray-900/80 text-gray-500 text-xs uppercase border-b border-gray-800">
            <tr>
              <th className="px-6 py-4 w-16 text-center">#</th>
              <th className="px-6 py-4">Title</th>
              <th className="px-6 py-4">Artist</th>
              <th className="px-6 py-4 text-right w-32">Duration</th>
            </tr>
          </thead>
          <tbody>
            {displayedTracks.map((track, index) => {
              const isCurrentlyPlaying = currentTrack?.id === track.id;

              return (
                <tr 
                  key={track.id} 
                  onClick={() => handlePlayTrack(index)}
                  className={`group border-b border-gray-800 hover:bg-gray-800/80 transition-colors cursor-pointer ${isCurrentlyPlaying ? 'bg-gray-800 border-l-4 border-l-blue-500' : 'border-l-4 border-l-transparent'}`}
                >
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