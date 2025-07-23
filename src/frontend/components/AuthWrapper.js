import React from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import ChatInterface from './ChatInterface';
import logo from '../assets/logo.png';


const AuthWrapper = () => {
  return (
    <Authenticator>
      {({ signOut, user }) => (
        <div>
          {/* Header with sign out */}
                  <div style={{ 
          padding: '0.5rem',
          color: 'white',
          display: 'flex',
          justifyContent: 'center',
          // minHeight: '60px',

        }}>
                <div className="chat-header">
                  
                  <div className="header-content">
                    <img src={logo} alt="Orcutt Union School District" className="header-logo" />
                    <div className="header-text">
                    <h1>Orcutt Schools Assistant</h1>
                    <p style={{marginTop:-7}}>Get help with school information, schedules, and more</p>
                    </div>
                  </div>
                </div>
          <div style={{position:"absolute",top:10,right:10, color:"#1A2F71"}}>
            <span>Welcome, {user.username}!</span>
            <button 
              onClick={signOut}
              style={{
                marginLeft: '1rem',
                padding: '0.5rem 1rem',
                background: 'rgba(178, 177, 191, 0.86)',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                color: '#1A2F71'
              }}
            >
              Sign Out
            </button>
          </div>
        </div>
          
          <ChatInterface />
        </div>
      )}
    </Authenticator>
  );
};

export default AuthWrapper;