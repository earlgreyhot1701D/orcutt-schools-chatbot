// src/components/MessageBubble.js
import React from 'react';

const MessageBubble = ({ message }) => {
  const isUser = message.role === 'user';
  const isError = message.isError;

  return (
    <div className={`message-bubble ${isUser ? 'user-message' : 'assistant-message'} ${isError ? 'error-message' : ''}`}>
      <div className="message-content">
        {message.content}
      </div>
      
      {/* Show response time for assistant messages */}
      {!isUser && message.responseTime && (
        <div className="message-metadata">
          <span>⏱️</span>
          <span>{message.responseTime}s</span>
        </div>
      )}
      
      {/* Show timestamp */}
      <div className="message-timestamp">
        {message.timestamp.toLocaleTimeString()}
      </div>
    </div>
  );
};

export default MessageBubble;