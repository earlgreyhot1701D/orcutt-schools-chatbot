# Orcutt Schools Chatbot

An AI-powered chatbot built for Orcutt Schools to help students, parents, and staff get information about school programs, schedules, and policies.

## Features

- **Intelligent Chat Interface** - Natural language processing using AWS Bedrock Claude
- **Knowledge Base Integration** - Semantic search through school documents and policies
- **Real-time Responses** - Fast, contextual answers to school-related questions
- **Source Citations** - Provides links to original documents and sources
- **Conversation History** - Maintains context throughout chat sessions
- **Mobile Responsive** - Works seamlessly on desktop and mobile devices

## Architecture

### Frontend
- **React 18** - Modern React with hooks
- **Tailwind CSS** - Utility-first styling
- **AWS Amplify Hosting** - Global CDN distribution

### Backend
- **AWS Lambda** - Serverless compute
- **Amazon Bedrock** - Claude 3.5 Sonnet for chat responses
- **AWS Knowledge Bases** - Semantic document search
- **Amazon DynamoDB** - Conversation storage
- **API Gateway** - REST API endpoints

### AI/ML
- **Nova Lite** - Query classification
- **Claude 3.5 Sonnet** - Response generation
- **Bedrock Guardrails** - Content safety
- **Z-score filtering** - Relevance scoring

## Installation

### Prerequisites
- Node.js 18+
- AWS CLI configured
- Amplify CLI installed

### Setup
```bash
# Clone the repository
git clone https://github.com/cal-poly-dxhub/orcutt-schools-chatbot.git

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env.local
# Edit .env.local with your API endpoints

# Start development server
npm start
AWS Deployment
bash# Initialize Amplify
amplify init

# Deploy backend
amplify push

# Deploy frontend
amplify publish
Configuration
Environment Variables
envREACT_APP_API_URL=your-api-gateway-url
REACT_APP_REGION=us-west-2
AWS Services Setup

Knowledge Base - Upload school documents
DynamoDB - Create conversations table
Lambda - Deploy chat handler function
API Gateway - Configure REST endpoints

Project Structure
src/
├── components/          # React components
│   ├── ChatInterface.js # Main chat UI
│   ├── MessageBubble.js # Individual messages
│   └── Sidebar.js       # Sources and info
├── hooks/               # Custom React hooks
│   └── useChat.js       # Chat logic and state
├── services/            # API services
│   └── apiService.js    # HTTP client
└── App.js               # Main application
Deployment
Development
bashnpm start                # Local development
Production
bashnpm run build           # Build for production
amplify publish         # Deploy to AWS
Custom Domain

Configure domain in Amplify Console
Add SSL certificate via ACM
Update DNS records in Route 53

Security

Input Validation - All user inputs sanitized
Guardrails - AWS Bedrock content filtering
CORS - Configured for secure cross-origin requests
Rate Limiting - API throttling and usage controls

Monitoring

CloudWatch - Application logs and metrics
DynamoDB - Conversation analytics
API Gateway - Request/response monitoring
Amplify - Deployment and hosting metrics

Contributing

Fork the repository
Create a feature branch (git checkout -b feature/amazing-feature)
Commit your changes (git commit -m 'Add amazing feature')
Push to the branch (git push origin feature/amazing-feature)
Open a Pull Request

License
This project is licensed under the MIT License - see the LICENSE file for details.
Support
For questions or support, please contact:

Email: tech-support@orcutt-schools.net
Issues: GitHub Issues tab
Documentation: /docs folder

Acknowledgments

Orcutt Union School District - Project sponsor
AWS Bedrock - AI/ML capabilities
React Community - Frontend framework
Amplify Team - Deployment platform


This README.md includes all the essential information for someone to understand, install, and contribute to your Orcutt Schools chatbot project.

