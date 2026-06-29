import { useEffect, useRef } from 'react';
import { usePlayerStore } from './store';
import { useNavigate } from 'react-router-dom';

export default function AudioPlayer() {
  const navigate = useNavigate();
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
    queueIndex, 
    currentTime, 
    duration, 
    setTrackProgress, 
    seekTo,
    toggleQueueFlyout
  } = usePlayerStore();

  const handleNavigateToAlbum = () => {
    if (currentTrack?.album_id) {
      // Navigate seamlessly without interrupting the <audio> element
      navigate(`/album/${encodeURIComponent(currentTrack.album_id)}`);
    } else {
      console.warn("No album ID available for this track.");
    }
  };

  const handleContextNavigation = () => {
    if (!currentTrack) return;

    if (playbackContext?.type === 'playlist') {
      // Pass state via the router to tell the Playlists page what to open
      navigate('/playlists', { state: { targetPlaylistId: playbackContext.id } });
    } 
    else if (playbackContext?.type === 'album' || currentTrack.release_id) {
      // Fallback to album view (using context or extracting from the track)
      const targetId = playbackContext?.id || currentTrack.release_id;
      navigate(`/album/${targetId}`);
    }
    // Future expansion: else if (playbackContext?.type === 'search') ...
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

  if (!currentTrack) return null; // Hide if nothing is playing

  // const currentTrack = usePlayerStore(state => state.currentTrack);
  let trackUrl = `/media/${currentTrack.id}`;
  if (currentTrack.start_time !== undefined && currentTrack.end_time !== undefined) {
    trackUrl += `#t=${currentTrack.start_time},${currentTrack.end_time}`;
  }

  const handleTimeUpdate = (e) => {
    const audio = e.target;
    
    setTrackProgress(e.target.currentTime, e.target.duration);
    // --- CUE SHEET VIRTUAL TRACK LOGIC ---
    if (currentTrack?.end_time) {
      // We check if we are within 0.2 seconds of the end to account for 
      // floating-point inaccuracies in how browsers report currentTime.
      if (audio.currentTime >= currentTrack.end_time - 0.2) {
        // We reached the end of the slice! 
        audio.pause(); 
        
        // Manually trigger your store to move to the next track
        playNextTrack(); 
      }
    }
  };

  return (
    <div className="fixed bottom-0 w-full h-24 bg-gray-900 border-t border-gray-800 text-white flex items-center px-6">
      
      {/* Hidden Native Audio Element */}
      <audio 
        ref={audioRef} 
        src={trackUrl} 
        autoPlay={isPlaying}       
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={(e) => setTrackProgress(0, e.target.duration)}
        onEnded={playNextTrack}
      />

      {/* Track Info */}
      <div 
          onClick={handleContextNavigation}
          className="flex items-center gap-4 w-1/3 cursor-pointer group hover:bg-gray-800/50 p-2 rounded-lg transition-colors"
          title="Go to playing source"
        >
          {currentTrack ? (
            <>
              <div className="w-14 h-14 bg-gray-800 rounded-md overflow-hidden shadow-md group-hover:shadow-lg transition-shadow flex-shrink-0">
                {currentTrack.art ? (
                  <img src={`/art/${currentTrack.art}`} alt="Cover" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-xl">🎵</div>
                )}
              </div>
              <div className="flex flex-col overflow-hidden">
                {/* FormattedTitle can be used here if you imported it previously! */}
                <div className="text-sm font-bold text-gray-100 truncate group-hover:text-blue-400 transition-colors">
                  {currentTrack.title}
                </div>
                <div 
                  className="text-xs text-gray-400 truncate hover:text-blue-400 hover:underline cursor-pointer inline-block"
                  title="View Artist"
                  onClick={(e) => {
                    e.stopPropagation(); // Prevents the parent Album routing from firing
                    if (currentTrack?.artist) {
                      navigate(`/artist/${encodeURIComponent(currentTrack.artist)}`);
                    }
                  }}
                >
                  {currentTrack.artist}
                </div>
              </div>
            </>
          ) : (
            <div className="text-sm text-gray-500 font-medium">Not Playing</div>
          )}
        </div>

      {/* Controls */}
      <div className="flex flex-col items-center justify-center w-1/3">
        <div className="flex space-x-6">
          {/* PREVIOUS BUTTON */}
          <button 
            onClick={playPreviousTrack}
            disabled={queue.length === 0 || queueIndex === 0}
            className="text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
          >
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" />
            </svg>
          </button>
          <button onClick={togglePlay} className="text-3xl hover:text-blue-400">
            {isPlaying ? '⏸' : '▶️'}
          </button>
          {/* NEXT BUTTON */}
          <button 
            onClick={playNextTrack}
            disabled={queue.length === 0 || queueIndex === queue.length - 1}
            className="text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
          >
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" />
            </svg>
          </button>
        </div>
        
        {/* Progress bar */}
        <div className="w-full mt-2">
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
            className="w-full h-1 bg-gray-700 accent-blue-500 cursor-pointer"
          />
          <div className="flex justify-between text-[10px] text-gray-400 mt-1">
            <span>{Math.floor(currentTime / 60)}:{(currentTime % 60).toFixed(0).padStart(2, '0')}</span>
            <span>{duration ? Math.floor(duration / 60) + ":" + (duration % 60).toFixed(0).padStart(2, '0') : "0:00"}</span>
          </div>
        </div>
      </div>

      {/* Volume */}
      <div className="w-1/3 flex justify-end">
        {/* QUEUE BUTTON */}
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
            {/* Tiny indicator dot if there are tracks in the queue */}
            {queue.length > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-blue-500 rounded-full border-2 border-gray-900"></span>
            )}
          </button>
        <input 
          type="range" min="0" max="1" step="0.01" 
          defaultValue={volume}
          onChange={(e) => usePlayerStore.getState().setVolume(e.target.value)}
          className="w-32 accent-blue-500"
        />
      </div>
    </div>
  );
}
