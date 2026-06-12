import { useState, useEffect } from 'react';
import { usePlayerStore } from './store';

export default function AlbumPage({ albumId, onBack }) {
  const [albumData, setAlbumData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  
  // Connect to global audio player
  const { playTrack, setPlaylist, currentTrack, isPlaying, togglePlay } = usePlayerStore();

  useEffect(() => {
    setIsLoading(true);
    // Fetch album details and tracklist
    fetch(`/api/albums/${encodeURIComponent(albumId)}`)
      .then(res => res.json())
      .then(data => {
        setAlbumData(data);
        setIsLoading(false);
      })
      .catch(err => {
        console.error("Failed to load album:", err);
        setIsLoading(false);
      });
  }, [albumId]);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // Play the entire album starting from track 1
  const handlePlayAlbum = () => {
    if (!albumData || albumData.tracks.length === 0) return;
    
    // Construct rich track objects for the player
    const playlist = albumData.tracks.map(t => ({
      ...t,
      artist: albumData.artist,
      album: albumData.title,
      art: albumData.art_hash
    }));
    
    setPlaylist(playlist);
    playTrack(playlist[0]);
  };

  // Play a specific track, but load the rest of the album into the queue
  const handlePlayTrack = (trackIndex) => {
    const playlist = albumData.tracks.map(t => ({
      ...t,
      artist: albumData.artist,
      album: albumData.title,
      art: albumData.art_hash
    }));
    
    setPlaylist(playlist);
    playTrack(playlist[trackIndex]);
  };

  if (isLoading) {
    return <div className="text-gray-500 text-center py-20 animate-pulse">Loading High-Res Audio...</div>;
  }

  if (!albumData) return null;

  // Calculate total album duration
  const totalSeconds = albumData.tracks.reduce((acc, track) => acc + track.duration, 0);
  const totalMinutes = Math.floor(totalSeconds / 60);

  return (
    <div className="w-full max-w-screen-xl mx-auto px-6 py-8 pb-32 animate-fade-in text-white">
      
      {/* Back Button */}
      <button 
        onClick={onBack}
        className="flex items-center text-gray-400 hover:text-blue-400 transition-colors mb-8 focus:outline-none"
      >
        <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Back to Library
      </button>

      {/* Hero Section: Artwork & Metadata */}
      <div className="flex flex-col md:flex-row gap-10 mb-12">
        {/* Large Artwork */}
        <div className="flex-shrink-0 w-64 h-64 md:w-80 md:h-80 shadow-2xl rounded-lg overflow-hidden bg-gray-800 border border-gray-700">
          {albumData.art_hash ? (
            <img 
              src={`/art/${albumData.art_hash}`} 
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
          
          <div className="flex items-center text-gray-400 mb-8 text-lg">
            <span className="font-semibold text-gray-100 mr-2">{albumData.artist}</span>
            <span>&bull; {albumData.tracks.length} tracks &bull; {totalMinutes} min</span>
          </div>

          <div className="flex gap-4">
            <button 
              onClick={handlePlayAlbum}
              className="bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-8 rounded-full shadow-lg transform hover:scale-105 transition-all flex items-center"
            >
              <svg className="w-6 h-6 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
              </svg>
              Play Album
            </button>
          </div>
        </div>
      </div>

      {/* Tracklist Table */}
      <div className="bg-gray-900 bg-opacity-50 rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-left text-gray-300">
          <thead className="text-xs uppercase text-gray-500 border-b border-gray-800">
            <tr>
              <th className="px-6 py-4 w-16 text-center">#</th>
              <th className="px-6 py-4">Title</th>
              <th className="px-6 py-4 text-right w-32">Duration</th>
            </tr>
          </thead>
          <tbody>
            {albumData.tracks.map((track, index) => {
              const isCurrentlyPlaying = currentTrack?.id === track.id;
              
              return (
                <tr 
                  key={track.id} 
                  onClick={() => handlePlayTrack(index)}
                  className={`group border-b border-gray-800 hover:bg-gray-800 transition-colors cursor-pointer ${isCurrentlyPlaying ? 'bg-gray-800 border-l-4 border-l-blue-500' : 'border-l-4 border-l-transparent'}`}
                >
                  {/* Track Number / Play Icon */}
                  <td className="px-6 py-4 text-center font-mono text-gray-500 group-hover:text-white">
                    {isCurrentlyPlaying && isPlaying ? (
                       <span className="text-blue-500">▶</span>
                    ) : (
                      <span className="block group-hover:hidden">{index + 1}</span>
                    )}
                    {!isCurrentlyPlaying && (
                      <span className="hidden group-hover:block text-blue-400">▶</span>
                    )}
                  </td>
                  
                  {/* Title */}
                  <td className={`px-6 py-4 font-medium ${isCurrentlyPlaying ? 'text-blue-400' : 'text-gray-100'}`}>
                    {track.title}
                  </td>
                  
                  {/* Duration */}
                  <td className="px-6 py-4 text-right text-gray-500 font-mono text-sm">
                    {formatTime(track.duration)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}