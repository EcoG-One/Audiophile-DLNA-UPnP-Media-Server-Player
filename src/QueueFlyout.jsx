import { usePlayerStore } from './store';

export default function QueueFlyout() {
  const { 
    queue, 
    queueIndex, 
    isQueueFlyoutOpen, 
    toggleQueueFlyout, 
    jumpToQueueIndex 
  } = usePlayerStore();

  const formatTime = (seconds) => {
    if (!seconds) return '--:--';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <>
      {/* Background Overlay (closes flyout when clicked outside) */}
      {isQueueFlyoutOpen && (
        <div 
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
          onClick={toggleQueueFlyout}
        />
      )}

      {/* The Flyout Panel */}
      <div 
        className={`fixed top-0 right-0 h-full w-96 bg-gray-900 border-l border-gray-800 shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col ${
          isQueueFlyoutOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="p-6 border-b border-gray-800 flex justify-between items-center bg-gray-900/95 backdrop-blur z-10">
          <h2 className="text-xl font-bold text-gray-100 flex items-center gap-3">
            <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h7" />
            </svg>
            Up Next
          </h2>
          <button 
            onClick={toggleQueueFlyout}
            className="text-gray-500 hover:text-white transition-colors p-1"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Queue List */}
        <div className="flex-1 overflow-y-auto p-2 scrollbar-thin scrollbar-thumb-gray-700">
          {queue.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-4">
              <span className="text-4xl">📭</span>
              <p>The queue is empty.</p>
            </div>
          ) : (
            <div className="space-y-1">
              {queue.map((track, index) => {
                const isPlaying = index === queueIndex;
                const isPast = index < queueIndex;
                
                return (
                  <button
                    key={`${track.id}-${index}`}
                    onClick={() => jumpToQueueIndex(index)}
                    className={`w-full text-left p-3 rounded-lg flex items-center gap-3 transition-all group ${
                      isPlaying 
                        ? 'bg-blue-600/20 border-l-4 border-blue-500 shadow-inner' 
                        : isPast 
                          ? 'opacity-50 hover:opacity-100 hover:bg-gray-800 border-l-4 border-transparent'
                          : 'hover:bg-gray-800 border-l-4 border-transparent'
                    }`}
                  >
                    {/* Artwork / Icon */}
                    <div className="w-10 h-10 flex-shrink-0 bg-gray-800 rounded overflow-hidden flex items-center justify-center">
                      {track.art_hash || track.art ? (
                        <img src={`/art/${track.art_hash || track.art}`} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <span className="text-gray-500 text-xs">🎵</span>
                      )}
                    </div>
                    
                    {/* Track Info */}
                    <div className="flex-1 min-w-0 flex flex-col justify-center">
                      <span className={`truncate text-sm font-medium ${isPlaying ? 'text-blue-400' : 'text-gray-200'}`}>
                        {track.title}
                      </span>
                      <span className="truncate text-xs text-gray-500">
                        {track.artist}
                      </span>
                    </div>

                    {/* Time / Playing Indicator */}
                    <div className="text-xs font-mono text-gray-600 flex-shrink-0">
                      {isPlaying ? (
                        <div className="flex items-center gap-1">
                          <span className="w-1 h-3 bg-blue-500 animate-pulse"></span>
                          <span className="w-1 h-2 bg-blue-500 animate-pulse delay-75"></span>
                          <span className="w-1 h-4 bg-blue-500 animate-pulse delay-150"></span>
                        </div>
                      ) : (
                        formatTime(track.duration)
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}