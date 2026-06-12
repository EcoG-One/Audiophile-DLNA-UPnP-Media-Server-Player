export default function AlbumGrid({ albums, onAlbumClick }) {
  
  // Safety net
  if (!Array.isArray(albums) || albums.length === 0) {
    return <div className="text-gray-500 text-center py-20">No albums found in your library.</div>;
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-6">
      {albums.map((album, index) => (
        <button 
          key={`album-${album.id}-${index}`} 
          onClick={() => onAlbumClick(album.title)}
          className="group text-left focus:outline-none"
        >
          {/* Artwork Container */}
          <div className="relative w-full aspect-square bg-gray-800 rounded-lg overflow-hidden shadow-md mb-3 transition-transform duration-300 group-hover:scale-105 group-focus:ring-2 group-focus:ring-blue-500">
            {album.art_hash ? (
              <img 
                src={`/art/${album.art_hash}`} 
                alt={album.title} 
                loading="lazy" 
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-gray-600 text-4xl">
                💿
              </div>
            )}
            
            {/* Play Overlay */}
            <div className="absolute inset-0 bg-black bg-opacity-40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <div className="bg-blue-600 rounded-full p-3 shadow-lg transform translate-y-4 group-hover:translate-y-0 transition-all duration-200">
                <svg className="w-8 h-8 text-white pl-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                </svg>
              </div>
            </div>
          </div>

          {/* Typography */}
          <h3 className="text-base font-bold text-gray-100 truncate group-hover:text-blue-400 transition-colors">
            {album.title}
          </h3>
          <p className="text-sm text-gray-400 truncate">
            {album.artist}
          </p>
        </button>
      ))}
    </div>
  );
}