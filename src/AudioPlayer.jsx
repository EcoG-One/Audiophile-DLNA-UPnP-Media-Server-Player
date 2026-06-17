import { useEffect, useRef } from 'react';
import { usePlayerStore } from './store';

export default function AudioPlayer() {
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
      <div className="flex items-center w-1/3">
        {currentTrack.art && (
          <img src={`/art/${currentTrack.art}`} alt="Album Art" className="w-16 h-16 rounded shadow-lg mr-4" />
        )}
        <div>
          <h4 className="font-bold text-lg">{currentTrack.title}</h4>
          <p className="text-gray-400 text-sm">{currentTrack.artist}</p>
        </div>
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
        
        {/* Progress bar added here */}
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
