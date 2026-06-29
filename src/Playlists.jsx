import { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { usePlayerStore } from './store';
import { useNavigate } from 'react-router-dom';

export default function Playlists() {
  const location = useLocation();
  const activeTrackRef = useRef(null);
  const [playlists, setPlaylists] = useState([]);
  const [activePlaylist, setActivePlaylist] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  const { playTrack, setPlaylist, currentTrack, isPlaying } = usePlayerStore();

  // Load all playlists on mount
  useEffect(() => {
    fetch('/api/playlists')
      .then(res => res.json())
      .then(data => {
        setPlaylists(data);
        
        // CHECK ROUTER STATE FIRST
        const targetId = location.state?.targetPlaylistId;
        
        if (targetId && data.find(p => p.id === targetId)) {
          loadPlaylistDetails(targetId);
        } else if (data.length > 0) {
          loadPlaylistDetails(data[0].id);
        } else {
          setIsLoading(false);
        }
      })
      .catch(err => console.error(err));
  }, [location.state]); // Re-run if the user navigates here via the player again

  // Scroll to the active track whenever the playlist changes or the track advances
  useEffect(() => {
    if (activeTrackRef.current) {
      // Small timeout ensures the DOM has fully rendered the table rows
      setTimeout(() => {
        activeTrackRef.current.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'center' 
        });
      }, 100);
    }
  }, [activePlaylist, currentTrack]);

  const loadPlaylistDetails = (id) => {
    setIsLoading(true);
    fetch(`/api/playlists/${id}`)
      .then(res => res.json())
      .then(data => {
        setActivePlaylist(data);
        setIsLoading(false);
      });
  };

  const handlePlayPlaylist = (startIndex = 0) => {
    if (!activePlaylist || !activePlaylist.tracks) return;
    
    const formattedTracks = activePlaylist.tracks.map(t => ({
      ...t,
      art: t.art_hash 
    }));
    
    // Pass the playback context!
    setPlaylist(formattedTracks, startIndex, {
      type: 'playlist',
      id: activePlaylist.id,
      name: activePlaylist.name
    });
    // playTrack(formattedTracks[startIndex]);
  };

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="w-full max-w-screen-xl mx-auto px-6 py-8 pb-32 animate-fade-in text-white h-[calc(100vh-80px)] flex gap-6">
      
      {/* Sidebar: Playlist List */}
      <div className="w-1/3 max-w-sm bg-gray-900/50 border border-gray-800 rounded-xl flex flex-col overflow-hidden">
        <div className="p-4 border-b border-gray-800 bg-gray-900/80">
          <h2 className="text-xl font-bold tracking-wide">Playlists</h2>
        </div>
        <div className="overflow-y-auto flex-1 p-2 space-y-1">
          {playlists.length === 0 && !isLoading && (
            <p className="text-gray-500 text-sm text-center mt-10">No playlists yet.<br/>Go add some tracks!</p>
          )}
          {playlists.map(pl => (
            <button
              key={pl.id}
              onClick={() => loadPlaylistDetails(pl.id)}
              className={`w-full text-left px-4 py-3 rounded-lg transition-colors flex items-center gap-3 ${
                activePlaylist?.id === pl.id 
                  ? 'bg-blue-600/20 text-blue-400 border-l-4 border-blue-500' 
                  : 'text-gray-400 hover:bg-gray-800 border-l-4 border-transparent'
              }`}
            >
              <span className="text-xl">📻</span>
              <div className="flex flex-col overflow-hidden">
                <span className="font-medium truncate">{pl.name}</span>
                <span className="text-[0.65em] font-mono text-gray-600 truncate">{pl.file_path.split(/[\\/]/).pop()}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Content: Tracklist */}
      <div className="flex-1 bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden flex flex-col">
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center text-gray-500 animate-pulse">Loading...</div>
        ) : activePlaylist ? (
          <>
            {/* Header */}
            <div className="p-8 border-b border-gray-800 bg-gradient-to-b from-gray-800 to-gray-900/50 flex gap-6 items-end">
              <div className="w-32 h-32 bg-gray-800 shadow-xl rounded-lg flex items-center justify-center text-4xl border border-gray-700">
                🎵
              </div>
              <div className="flex flex-col pb-2">
                <span className="text-xs font-bold text-blue-400 uppercase tracking-widest mb-1">M3U Playlist</span>
                <h1 className="text-4xl font-bold mb-4">{activePlaylist.name}</h1>
                <div className="flex items-center gap-4">
                  <button 
                    onClick={() => handlePlayPlaylist(0)}
                    disabled={activePlaylist.tracks.length === 0}
                    className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-6 py-2 rounded-full font-bold transition-all shadow-lg flex items-center gap-2"
                  >
                    <span>▶</span> Play All
                  </button>
                  <span className="text-gray-500 text-sm">{activePlaylist.tracks.length} tracks</span>
                </div>
              </div>
            </div>

            {/* Tracks Table */}
            <div className="flex-1 overflow-y-auto">
              <table className="w-full text-left text-gray-300">
                <thead className="bg-gray-900/90 text-gray-500 text-xs uppercase border-b border-gray-800 sticky top-0 z-10">
                  <tr>
                    <th className="px-6 py-3 w-16 text-center">#</th>
                    <th className="px-6 py-3">Title</th>
                    <th className="px-6 py-3">Artist</th>
                    <th className="px-6 py-3">Album</th>
                    <th className="px-6 py-3 text-right">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {activePlaylist.tracks.map((track, index) => {
                    const isCurrentlyPlaying = currentTrack?.id === track.id;
                    return (
                      <tr 
                        key={`${track.id}-${index}`} 
                        ref={isCurrentlyPlaying ? activeTrackRef : null} // Attach the ref here!
                        onClick={() => handlePlayPlaylist(index)}
                        className={`group border-b border-gray-800 ...`}
                      >
                        <td className="px-6 py-3 text-center text-gray-500">
                          {isCurrentlyPlaying && isPlaying ? (
                            <span className="text-blue-500">▶</span>
                          ) : (
                            <span>{index + 1}</span>
                          )}
                        </td>
                        <td className={`px-6 py-3 font-medium ${isCurrentlyPlaying ? 'text-blue-400' : 'text-gray-100'}`}>
                          <div className="flex items-center gap-3">
                            {track.art_hash ? (
                              <img src={`/art/${track.art_hash}`} alt="" className="w-8 h-8 rounded" />
                            ) : (
                              <div className="w-8 h-8 rounded bg-gray-700 flex items-center justify-center text-xs">💿</div>
                            )}
                            {track.title}
                          </div>
                        </td>
                        <td className="px-6 py-3 text-sm text-gray-400">{track.artist}</td>
                        <td className="px-6 py-3 text-sm text-gray-400 truncate max-w-[150px]">{track.album}</td>
                        <td className="px-6 py-3 text-right font-mono text-sm text-gray-500">{formatTime(track.duration)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {activePlaylist.tracks.length === 0 && (
                <div className="p-10 text-center text-gray-500">
                  This playlist is empty. Add tracks from the Albums page!
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}