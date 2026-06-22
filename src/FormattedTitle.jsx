import React from 'react';

export default function FormattedTitle({ 
  title, 
  className = "", 
  spanClassName = "text-[0.8em] text-gray-400/90 font-normal ml-1" 
}) {
  if (!title) return null;

  // Split the title into an array, isolating anything wrapped in parentheses
  const parts = title.split(/(\([^)]+\))/g);

  return (
    <span className={className} title={title}>
      {parts.map((part, index) => {
        // If the chunk is a parenthetical string, wrap it in the smaller styling
        if (part.startsWith('(') && part.endsWith(')')) {
          return (
            <span key={index} className={spanClassName}>
              {part}
            </span>
          );
        }
        // Otherwise, render the normal text
        return <React.Fragment key={index}>{part}</React.Fragment>;
      })}
    </span>
  );
}