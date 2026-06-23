import { useState, useEffect } from 'react';

export default function ScrollToTopButton() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Connect to the main scroll container in App.jsx
    const container = document.getElementById('main-scroll-container');
    if (!container) return;

    const handleScroll = () => {
      // Show the button only after scrolling down 400 pixels
      setIsVisible(container.scrollTop > 400);
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = () => {
    const container = document.getElementById('main-scroll-container');
    if (container) {
      container.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    }
  };

  return (
    <button
      onClick={scrollToTop}
      className={`fixed bottom-32 right-10 p-4 rounded-full bg-blue-600 text-white shadow-[0_0_15px_rgba(37,99,235,0.5)] transition-all duration-300 z-50 hover:bg-blue-500 hover:scale-110 focus:outline-none ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10 pointer-events-none'
      }`}
      title="Back to Top"
    >
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 10l7-7m0 0l7 7m-7-7v18" />
      </svg>
    </button>
  );
}