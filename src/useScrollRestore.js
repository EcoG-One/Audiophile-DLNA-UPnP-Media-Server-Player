import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

export default function useScrollRestore() {
  const location = useLocation();
  const scrollRef = useRef(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    // 1. Restore scroll position instantly on mount
    const savedPosition = sessionStorage.getItem(`scroll-${location.key}`);
    if (savedPosition) {
      // Use requestAnimationFrame to ensure the DOM has fully painted the cached grid
      requestAnimationFrame(() => {
        el.scrollTop = parseInt(savedPosition, 10);
      });
    }

    // 2. Save scroll position whenever the user scrolls
    const handleScroll = () => {
      sessionStorage.setItem(`scroll-${location.key}`, el.scrollTop.toString());
    };

    el.addEventListener('scroll', handleScroll, { passive: true });
    
    return () => el.removeEventListener('scroll', handleScroll);
  }, [location.key]); // Ties the memory to the specific history state

  return scrollRef;
}