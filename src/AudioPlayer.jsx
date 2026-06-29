import { useEffect, useRef, useState } from 'react';
import { usePlayerStore } from './store';
import { useNavigate } from 'react-router-dom';

export default function AudioPlayer() {
  const navigate = useNavigate();
  const [isExpanded, setIsExpanded] = useState(false);
  const audioRef = useRef(null);
  
  const { 
    currentTrack, 
    isPlaying, 
    playbackContext,
    volume, 
    togglePlay, 
    playNextTrack, 
    playPreviousTrack,
    queue,
    currentTime, 
    duration, 
    setTrackProgress, 
    seekTo,
    toggleQueueFlyout
  } = usePlayerStore();

  // Centralized navigation logic to handle both mobile expanding and desktop routing
  const handleTrackInfoClick = () => {
    if (!currentTrack) return;

    if (window.innerWidth < 768 && !isExpanded) {
      setIsExpanded(true);
    } else if (playbackContext?.type === 'playlist') {
      navigate('/playlists', { state: { targetPlaylistId: playbackContext.id } });
      setIsExpanded(false);
    } else {
      // Safely fall back to album_id (original working behavior) or release_id
      const targetId = playbackContext?.id || currentTrack.album_id || currentTrack.release_id;
      if (targetId) {
        navigate(`/album/${encodeURIComponent(targetId)}`);
      }
      setIsExpanded(false);
    }
  };

  const handleArtistClick = (e) => {
    e.stopPropagation(); // Prevents the main container click from firing
    if (!currentTrack) return;
    
    if (window.innerWidth < 768 && !isExpanded) {
      setIsExpanded(true); // Still expand the player on mobile if minimized
    } else if (currentTrack.artist_id) {
      navigate(`/artist/${encodeURIComponent(currentTrack.artist_id)}`);
      setIsExpanded(false);
    } else if (currentTrack.artist) {
      // Fallback if your backend only passed the string name
      navigate(`/artist/${encodeURIComponent(currentTrack.artist)}`);
      setIsExpanded(false);
    }
  };

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
      if (isPlaying) {
        audioRef.current.play().catch(e => console.error("Playback failed:", e));
      } else {
        audioRef.current.pause();
      }
    }
  }, [isPlaying, currentTrack, volume]);

  if (!currentTrack) return null;

  let trackUrl = `/media/${currentTrack.id}`;
  if (currentTrack.start_time !== undefined && currentTrack.end_time !== undefined) {
    trackUrl += `#t=${currentTrack.start_time},${currentTrack.end_time}`;
  }

  const handleTimeUpdate = (e) => {
    const audio = e.target;
    setTrackProgress(e.target.currentTime, e.target.duration);
    
    if (currentTrack?.end_time) {
      if (audio.currentTime >= currentTrack.end_time - 0.2) {
        audio.pause(); 
        playNextTrack(); 
      }
    }
  };

  return (
    <>
      <div 
        className={`fixed z-50 transition-all duration-300 ease-in-out bg-gray-900 border-gray-800 backdrop-blur-xl
          ${isExpanded 
            ? 'inset-0 flex flex-col p-6' 
            : 'bottom-16 md:bottom-0 w-full h-16 md:h-24 border-t flex items-center px-4 md:px-6' 
          }
        `}
      >
        {isExpanded && (
          <button 
            onClick={() => setIsExpanded(false)}
            className="md:hidden absolute top-6 left-6 text-gray-400 p-2"
          >
            ↓
          </button>
        )}

        {/* LEFT SECTION: Track Info */}
        <div 
          onClick={handleTrackInfoClick}
          className={`flex items-center cursor-pointer group hover:bg-gray-800/50 rounded-lg transition-colors
            ${isExpanded 
              ? 'flex-col flex-1 justify-center mt-12' 
              : 'w-2/3 md:w-1/3 gap-3 p-1' 
            }
          `}
          title="Go to playing source"
        >
          {currentTrack.art_hash || currentTrack.art ? (
            <img 
              src={`/art/${currentTrack.art_hash || currentTrack.art}`} 
              alt="Album Art" 
              className={`shadow-lg object-cover flex-shrink-0 ${
                isExpanded ? 'w-64 h-64 mb-8 rounded-xl shadow-2xl' : 'w-10 h-10 md:w-14 md:h-14 rounded-md'
              }`} 
            />
          ) : (
            <div className={`flex items-center justify-center bg-gray-800 text-gray-500 flex-shrink-0 shadow-lg ${
                isExpanded ? 'w-64 h-64 mb-8 rounded-xl shadow-2xl text-6xl' : 'w-10 h-10 md:w-14 md:h-14 rounded-md text-xl'
              }`}>
              🎵
            </div>
          )}
          <div className={`flex flex-col overflow-hidden ${isExpanded ? 'items-center text-center' : ''}`}>
            {/* TRACK TITLE (Routes to Album/Playlist) */}
            <span 
              className={`font-bold text-white truncate hover:underline ${isExpanded ? 'text-2xl mb-2' : 'text-sm md:text-base'}`}
            >
              {currentTrack.title}
            </span>
            
            {/* ARTIST NAME (Routes to Artist) */}
            <span 
              onClick={handleArtistClick}
              className={`text-gray-400 truncate hover:text-white hover:underline cursor-pointer transition-colors ${isExpanded ? 'text-lg' : 'text-xs md:text-sm'}`}
            >
              {currentTrack.artist}
            </span>
          </div>
        </div>

        {/* MIDDLE SECTION: Transport Controls (Fixed Layout) */}
        <div className={`flex flex-col items-center justify-center
          ${isExpanded 
            ? 'w-full mb-12 gap-8' 
            : 'hidden md:flex w-1/3' 
          }
        `}>
          {/* Buttons on top */}
          <div className={`flex items-center ${isExpanded ? 'gap-8' : 'gap-6 mb-2'}`}>
            <button onClick={playPreviousTrack} className="text-gray-400 hover:text-white transition-colors">
              <svg className={isExpanded ? 'w-10 h-10' : 'w-5 h-5'} fill="currentColor" viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" /></svg>
            </button>
            <button onClick={togglePlay} className="text-white bg-blue-600 hover:bg-blue-500 rounded-full p-2.5 transition-transform hover:scale-105 shadow-lg shadow-blue-500/30">
              {isPlaying ? (
                <svg className={isExpanded ? 'w-10 h-10' : 'w-6 h-6'} fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" /></svg>
              ) : (
                <svg className={isExpanded ? 'w-10 h-10' : 'w-6 h-6'} fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
              )}
            </button>
            <button onClick={playNextTrack} className="text-gray-400 hover:text-white transition-colors">
              <svg className={isExpanded ? 'w-10 h-10' : 'w-5 h-5'} fill="currentColor" viewBox="0 0 24 24"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" /></svg>
            </button>
          </div>

          {/* Progress bar and timestamps perfectly inline below buttons */}
          <div className="w-full max-w-md flex items-center gap-3 px-2">
            <span className="text-[10px] text-gray-400 font-mono w-8 text-right">
              {Math.floor(currentTime / 60)}:{(currentTime % 60).toFixed(0).padStart(2, '0')}
            </span>
            <input 
              type="range" 
              min="0" 
              max={duration || 0} 
              step="0.1" 
              value={currentTime}
              onChange={(e) => {
                const time = parseFloat(e.target.value);
                seekTo(time);
                if (audioRef.current) audioRef.current.currentTime = time;
              }}
              className="flex-1 h-1 bg-gray-700 accent-blue-500 cursor-pointer"
            />
            <span className="text-[10px] text-gray-400 font-mono w-8">
              {duration ? Math.floor(duration / 60) + ":" + (duration % 60).toFixed(0).padStart(2, '0') : "0:00"}
            </span>
          </div>
        </div>

        {/* MOBILE MINI TRANSPORT */}
        <div className={`md:hidden flex items-center justify-end w-1/3 gap-3 ${isExpanded ? 'hidden' : ''}`}>
          <button onClick={togglePlay} className="text-white p-2">
            {isPlaying 
              ? <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" /></svg>
              : <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
            }
          </button>
        </div>

        {/* RIGHT SECTION: Extras (Volume, Queue) */}
        <div className={`hidden md:flex items-center justify-end w-1/3 pr-4 gap-4 ${isExpanded ? 'hidden' : ''}`}>
          <button 
            onClick={toggleQueueFlyout}
            className={`p-2 rounded-lg transition-colors relative ${
              queue.length > 0 ? 'text-gray-300 hover:text-white hover:bg-gray-800' : 'text-gray-600 cursor-not-allowed'
            }`}
            title="Up Next"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h7" />
            </svg>
            {queue.length > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-blue-500 rounded-full border-2 border-gray-900"></span>
            )}
          </button>
          
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
            <input 
              type="range" min="0" max="1" step="0.01" 
              defaultValue={volume}
              onChange={(e) => usePlayerStore.getState().setVolume(e.target.value)}
              className="w-24 accent-blue-500"
            />
          </div>
        </div>
      </div>

      <audio 
        ref={audioRef} 
        src={trackUrl} 
        autoPlay={isPlaying}       
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={(e) => setTrackProgress(0, e.target.duration)}
        onEnded={playNextTrack}
      />
    </>
  );
}