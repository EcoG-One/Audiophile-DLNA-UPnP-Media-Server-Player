export default function ArtistGrid({ artists, onArtistClick }) {
  
  if (!Array.isArray(artists) || artists.length === 0) {
    return <div className="text-gray-500 text-center py-20">No artists found.</div>;
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-8">
      {artists.map((artist, index) => (
        <button 
          // 2. Append the index to guarantee a perfectly unique key
          key={`artist-${artist.name}-${index}`} 
          onClick={() => onArtistClick(artist.name)}
          className="group text-center focus:outline-none flex flex-col items-center"
        >
          {/* Artist Image (Circular) */}
          {/* Inside the artist.map loop */}
          <div className="relative w-full aspect-square rounded-full bg-gray-800 overflow-hidden shadow-lg mb-4 transition-transform duration-300 group-hover:scale-105 group-focus:ring-2 group-focus:ring-blue-500">
            {artist.thumbnail ? (
              <img 
                src={artist.thumbnail} 
                alt={artist.name} 
                loading="lazy"
                className="w-full h-full object-cover"
                onError={(e) => { 
                  // Fallback if image fails to load
                  e.target.style.display = 'none'; 
                  e.target.nextSibling.style.display = 'flex'; 
                }}
              />
            ) : null}
            {/* Fallback Icon */}
            <div className={`w-full h-full items-center justify-center text-gray-600 text-5xl ${artist.thumbnail ? 'hidden' : 'flex'}`}>
              🎤
            </div>
          </div>

          {/* Typography */}
          <h3 className="text-base font-bold text-gray-100 truncate w-full group-hover:text-blue-400 transition-colors">
            {artist.name}
          </h3>
          <p className="text-xs text-gray-500 mt-1 uppercase tracking-wider">
            {artist.album_count || 1} Album{artist.album_count !== 1 ? 's' : ''}
          </p>
        </button>
      ))}
    </div>
  );
}