// src/services/apiService.js
import axios from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';

// Replace with your actual API Gateway URL
const API_BASE_URL = '';

// Function to get authentication headers
const getAuthHeaders = async () => {
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    
    if (token) {
      return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      };
    } else {
      console.warn('No auth token found');
      return {
        'Content-Type': 'application/json'
      };
    }
  } catch (error) {
    console.error('Error getting auth token:', error);
    return {
      'Content-Type': 'application/json'
    };
  }
};

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds for Bedrock responses
});

// Add request interceptor to include auth headers
apiClient.interceptors.request.use(
  async (config) => {
    // Get fresh auth headers for each request
    const authHeaders = await getAuthHeaders();
    config.headers = {
      ...config.headers,
      ...authHeaders
    };
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    
    if (error.code === 'ECONNABORTED') {
      throw new Error('Request timeout - please try again');
    }
    
    if (error.response) {
      // Handle specific auth errors
      if (error.response.status === 401) {
        throw new Error('Authentication failed - please sign in again');
      }
      if (error.response.status === 403) {
        throw new Error('Access forbidden - insufficient permissions');
      }
      
      // Server responded with error status
      const message = error.response.data?.error || 'Server error occurred';
      throw new Error(message);
    } else if (error.request) {
      // Network error
      throw new Error('Network error - please check your connection');
    } else {
      throw new Error('An unexpected error occurred');
    }
  }
);

export const chatService = {
  /**
   * Send a chat message
   * @param {string} message - User message
   * @param {string} sessionId - Session identifier
   * @returns {Promise} API response
   */
  sendMessage: async (message, sessionId) => {
    try {
      const response = await apiClient.post('/chat', {
        message: message.trim(),
        sessionId,
      });
      console.log("Session ID sent:", sessionId);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get presigned URL for a source document
   * @param {string} sourceId - Source identifier
   * @param {string} s3Uri - S3 URI of the document
   * @returns {Promise} Presigned URL response
   */
  getSourceUrl: async (sourceId, s3Uri) => {
    try {
      const response = await apiClient.get(`/sources/${sourceId}`, {
        params: {
          s3Uri: s3Uri
        }
      });
      
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Test authentication status
   * @returns {Promise} Auth status
   */
  testAuth: async () => {
    try {
      const session = await fetchAuthSession();
      return {
        isAuthenticated: !!session.tokens?.idToken,
        username: session.tokens?.idToken?.payload?.email || 'Unknown'
      };
    } catch (error) {
      console.error('Auth test failed:', error);
      return {
        isAuthenticated: false,
        username: null
      };
    }
  }
};

export default chatService;