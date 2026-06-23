import { useEffect, useRef } from 'react';
import { usePlayerStore } from './store';
import { useNavigate } from 'react-router-dom';

export default function AudioPlayer() {
  const navigate = useNavigate();
  const audioRef = useRef(null);
  const { 
    currentTrack, 
    isPlaying, 
    volume, 
    togglePlay, 
    nextTrack, 
    currentTime, 
    duration, 
    setTrackProgress, 
    seekTo 
  } = usePlayerStore();

  const handleNavigateToAlbum = () => {
    if (currentTrack?.album_id) {
      // Navigate seamlessly without interrupting the <audio> element
      navigate(`/album/${encodeURIComponent(currentTrack.album_id)}`);
    } else {
      console.warn("No album ID available for this track.");
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

  if (!currentTrack) return null; // Hide if nothing is playing

  return (
    <div className="fixed bottom-0 w-full h-24 bg-gray-900 border-t border-gray-800 text-white flex items-center px-6">
      
      {/* Hidden Native Audio Element */}
      <audio 
        ref={audioRef} 
        src={`/media/${currentTrack.id}`} 
        onEnded={nextTrack}
        onTimeUpdate={(e) => setTrackProgress(e.target.currentTime, e.target.duration)}
        onLoadedMetadata={(e) => setTrackProgress(0, e.target.duration)}
      />

      {/* Track Info */}
      <div 
          onClick={handleNavigateToAlbum}
          className={`flex items-center w-1/3 gap-4 p-2 -ml-2 rounded-xl transition-all ${
            currentTrack?.album_id 
              ? 'cursor-pointer group hover:bg-gray-800/60' 
              : ''
          }`}
          title={currentTrack?.album_id ? "View Album" : ""}
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
          <button className="hover:text-blue-400 text-gray-300">⏮</button>
          <button onClick={togglePlay} className="text-3xl hover:text-blue-400">
            {isPlaying ? '⏸' : '▶️'}
          </button>
          <button onClick={nextTrack} className="hover:text-blue-400 text-gray-300">⏭</button>
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
