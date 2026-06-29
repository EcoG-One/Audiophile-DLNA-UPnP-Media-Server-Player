export default function Artists() {
  return (
    <div className="w-full max-w-screen-xl mx-auto px-6 py-8 animate-fade-in text-white h-full flex flex-col items-center justify-center">
      <div className="text-6xl mb-6">🎤</div>
      <h1 className="text-3xl font-bold mb-4">Artists</h1>
      <p className="text-gray-500 text-center max-w-md">
        Your artist library will live here. We just need to wire this up to your Python backend to fetch the artist database!
      </p>
    </div>
  );
}