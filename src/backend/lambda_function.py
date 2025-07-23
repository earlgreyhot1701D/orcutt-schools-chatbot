# lambda/lambda_function.py
# AWS Lambda function handler for processing chat requests
# Handles user messages, integrates with AWS Bedrock for AI responses,
# manages conversation history in DynamoDB, and retrieves information
# from knowledge bases when needed

import json
import boto3
import os
import uuid
import time
import numpy as np
from typing import Dict, List, Tuple
from decimal import Decimal
from datetime import datetime, timezone, timedelta, date
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    """Main Lambda handler for chat requests with full functionality"""
    
    # Handle CORS preflight requests
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': ''
        }
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        message = body.get('message', '').strip()
        session_id = body.get('sessionId', str(uuid.uuid4()))
        
        if not message or not session_id:
            return create_error_response(400, "Message/Session ID is missing")
        
        # Initialize the chatbot
        chatbot = OrcuttChatbot()
        
        # Process the chat request
        result = chatbot.process_chat_request(message, session_id)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(result, default=decimal_default)
        }
        
    except Exception as e:
        return create_error_response(500, f"Internal server error: {str(e)}")

def get_cors_headers():
    """Return standard CORS headers"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
        'Content-Type': 'application/json'
    }

def decimal_default(obj):
    """Handle Decimal serialization for JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def create_error_response(status_code, message):
    """Create standardized error response"""
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'error': message,
            'success': False
        })
    }

def calculate_zscores(cosine_scores):
    """Calculate z-scores for cosine similarity scores"""
    # Calculate the mean of the sample points
    mean = np.mean(cosine_scores)
    # Calculate the standard deviation of the sample points
    std_deviation = np.std(cosine_scores, ddof=1)  # ddof=1 for sample standard deviation
    # Calculate the z-scores for each sample point
    z_scores = [(x - mean) / std_deviation for x in cosine_scores]
    return z_scores

class OrcuttChatbot:
    def __init__(self):
        self.bedrock_client = None
        self.bedrock_agent_runtime = None
        self.dynamodb = None
        self.s3_client = None
        self.table = None
        self.initialize_aws_clients()
    
    def initialize_aws_clients(self):
        """Initialize AWS clients"""
        try:
            region = os.environ.get('AWS_REGION', 'us-west-2')
            
            self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
            self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=region)
            self.s3_client = boto3.client('s3', region_name=region)
            self.dynamodb = boto3.resource('dynamodb', region_name=region)
            self.table = self.dynamodb.Table(os.environ.get('DYNAMODB_TABLE'))
            
        except Exception as e:
            print(f"Failed to initialize AWS clients: {str(e)}")
            raise
    
    def process_chat_request(self, message: str, session_id: str) -> Dict:
        """Main method to process chat request with full functionality"""
        start_time = time.time()
        
        try:
            # Step 1: Get conversation history
            conversation_history = self.get_conversation_history(session_id)
            
            # Step 2: Classify query using Nova
            query_type = self.classify_query_with_nova(message)
            
            # Step 3: Apply input guardrails
            input_allowed = self.apply_bedrock_guardrails(message, 'INPUT')
            
            if not input_allowed:
                blocked_response = "Please keep your questions appropriate and school-related."
                self.save_conversation_to_dynamodb(session_id, message, blocked_response, [], 0, 'blocked')
                return {
                    'success': False,
                    'response': blocked_response,
                    'sessionId': session_id,
                    'queryType': 'blocked',
                    'responseTime': round(time.time() - start_time, 2),
                    'sources': []
                }
            
            # Step 4: Get context from knowledge base if needed
            context = ""
            sources = []
            
            if query_type == 'knowledge_base':
                knowledge_base_id = os.environ.get('KNOWLEDGE_BASE_ID')
                if knowledge_base_id:
                    kb_response = self.query_knowledge_base_semantic(message, knowledge_base_id)
                    context, sources = self.process_knowledge_base_response(kb_response)
            
            # Step 5: Generate response with conversation context
            conversation_context = self.format_conversation_context(conversation_history)
            response_text, generation_time = self.generate_response(
                message, context, query_type, conversation_context
            )
            
            total_time = round(time.time() - start_time, 2)
            
            # Step 7: Save conversation to DynamoDB
            self.save_conversation_to_dynamodb(session_id, message, response_text, sources, total_time, query_type)
            
            return {
                'success': True,
                'response': response_text,
                'sessionId': session_id,
                'queryType': query_type,
                'responseTime': total_time,
                'sources': sources
            }
            
        except Exception as e:
            error_response = "I'm sorry, I encountered an error while processing your request. Please try again."
            self.save_conversation_to_dynamodb(session_id, message, error_response, [], 0, 'error')
            return {
                'success': False,
                'response': error_response,
                'sessionId': session_id,
                'queryType': 'error',
                'responseTime': round(time.time() - start_time, 2),
                'sources': []
            }
    
    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """Retrieve conversation history from DynamoDB"""
        try:
            response = self.table.query(
                KeyConditionExpression=Key('session_id').eq(session_id),
                ScanIndexForward=False,  # Most recent first
                Limit=6  # Last 3 exchanges (6 messages total)
            )
            
            # Reverse to get chronological order
            items = list(reversed(response.get('Items', [])))
            
            history = []
            for item in items:
                # Add user message
                history.append({
                    'role': 'user',
                    'content': item['user_message'],
                    'timestamp': item['timestamp']
                })
                # Add assistant message
                history.append({
                    'role': 'assistant', 
                    'content': item['assistant_response'],
                    'timestamp': item['timestamp']
                })
            
            return history
            
        except Exception as e:
            return []
    
    def save_conversation_to_dynamodb(self, session_id: str, user_message: str, 
                                    assistant_response: str, sources: list, 
                                    response_time: float, query_type: str):
        """Save conversation exchange to DynamoDB"""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Get next message ID for this session
            message_id = self.get_next_message_id(session_id)
            
            conversation_item = {
                'session_id': str(session_id),
                'timestamp': str(timestamp),
                'message_id': message_id,
                'user_message': str(user_message),
                'assistant_response': str(assistant_response),
                'query_type': str(query_type),
                'response_time_seconds': Decimal(str(round(response_time, 2))),
                'created_at': str(timestamp),
            }
            
            self.table.put_item(Item=conversation_item)
            
        except Exception as e:
            pass
    
    def get_next_message_id(self, session_id: str) -> str:
        """Get the next sequential message ID for a session"""
        try:
            # Query existing messages for this session to get count
            response = self.table.query(
                KeyConditionExpression=Key('session_id').eq(session_id),
                Select='COUNT'
            )
            
            # Next message number is count + 1
            next_number = response.get('Count', 0) + 1
            return f"conv{next_number}"
            
        except Exception as e:
            # Fallback to timestamp-based ID if query fails
            return f"msg{int(time.time())}"
    
    def format_conversation_context(self, conversation_history: List[Dict]) -> str:
        """Format conversation history for Claude context"""
        if not conversation_history:
            return ""
        
        # Use last 6 messages max for context
        recent_messages = conversation_history[-6:]
        
        context = ""
        for msg in recent_messages:
            role = "Human" if msg['role'] == 'user' else "Assistant"
            content = msg['content']
            context += f"{role}: {content}\n"
        
        return context
    
    def classify_query_with_nova(self, user_input: str) -> str:
        """Classify the user query using Nova Pro/Lite"""
        try:
            classification_prompt = f"""You are a query classifier for the Orcutt Schools Assistant chatbot. Your job is to classify user messages into one of these categories:

CATEGORIES:
1. "greeting" - Initial hellos, good morning/afternoon/evening, introductory messages
2. "farewell" - Thank you messages, goodbye, see you later, closing statements  
3. "knowledge_base" - Any questions or requests for information (school-related or otherwise)

EXAMPLES:
- "Hi there" → greeting
- "Hello, how are you?" → greeting
- "Good morning!" → greeting
- "Thanks for your help" → farewell
- "Goodbye" → farewell
- "Thank you, that's all I needed" → farewell
- "What are the school hours?" → knowledge_base
- "How do I enroll my child?" → knowledge_base
- "Tell me about the math program" → knowledge_base
- "What's the weather like?" → knowledge_base
- "Can you help me with homework?" → knowledge_base
- "I need information about buses" → knowledge_base

USER MESSAGE: "{user_input}"

Respond with ONLY the category name (greeting, farewell, or knowledge_base). No explanation needed."""

            body = json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": classification_prompt}]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 10,
                    "temperature": 0.1,
                    "topP": 0.9
                }
            })
            
            response = self.bedrock_client.invoke_model(
                modelId="us.amazon.nova-lite-v1:0",
                contentType="application/json",
                body=body
            )
            
            response_body = json.loads(response['body'].read())
            classification = response_body['output']['message']['content'][0]['text'].strip().lower()
            
            # Validate the classification result
            valid_categories = ['greeting', 'farewell', 'knowledge_base']
            if classification in valid_categories:
                return classification
            else:
                return 'knowledge_base'
                
        except Exception as e:
            # Fallback to knowledge_base if Nova fails
            return 'knowledge_base'
    
    def apply_bedrock_guardrails(self, text: str, source: str = 'INPUT') -> bool:
        """Apply Bedrock Guardrails"""
        try:
            guardrail_id = os.environ.get('GUARDRAIL_ID')
            guardrail_version = os.environ.get('GUARDRAIL_VERSION', '1')
            
            if not guardrail_id:
                return True, []
                
            response = self.bedrock_client.apply_guardrail(
                guardrailIdentifier=guardrail_id,
                guardrailVersion=guardrail_version,
                source=source,
                content=[{
                    'text': {'text': text}
                }]
            )
            
            if response['action'] == 'GUARDRAIL_INTERVENED':
                return False
            
            return True
            
        except Exception as e:
            return True
    
    def query_knowledge_base_semantic(self, query: str, knowledge_base_id: str) -> Dict:
        """Query Knowledge Base using only semantic search with z-score filtering"""
        try:
            print(f"🔍 Querying KB with: '{query}'")
            print(f"🔍 Knowledge Base ID: {knowledge_base_id}")
            
            # Use only semantic search
            response = self.bedrock_agent_runtime.retrieve(
                knowledgeBaseId=knowledge_base_id,
                retrievalQuery={'text': query},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': 10,
                        'overrideSearchType': 'SEMANTIC'
                    }
                }
            )
            
            print(f"🔍 KB Response received: {len(response.get('retrievalResults', []))} results")
            
            # Apply z-score filtering if we have results
            if 'retrievalResults' in response and len(response['retrievalResults']) > 1:
                # Extract similarity scores
                scores = [result.get('score', 0) for result in response['retrievalResults']]
                print(f"🔍 Scores: {[f'{s:.3f}' for s in scores]}")
                
                # Calculate z-scores
                z_scores = calculate_zscores(scores)
                
                # Filter results with z-score > 1 (above one standard deviation)
                filtered_results = []
                for i, (result, z_score) in enumerate(zip(response['retrievalResults'], z_scores)):
                    if z_score > 1:  # Keep results above one standard deviation
                        filtered_results.append(result)
                        print(f"🔍 Result {i+1}: Score={result.get('score', 0):.3f}, Z-score={z_score:.3f} - KEPT")
                    else:
                        print(f"🔍 Result {i+1}: Score={result.get('score', 0):.3f}, Z-score={z_score:.3f} - FILTERED OUT")
                
                # Update response with filtered results
                # response['retrievalResults'] = filtered_results
                print(f"🔍 Z-score filtering: {len(filtered_results)} results kept out of {len(scores)} total")
            
            return response
            
        except Exception as e:
            print(f"🔍 Error querying knowledge base: {str(e)}")
            return {}
    
    def process_knowledge_base_response(self, kb_response: Dict) -> Tuple[str, List]:
        """Process knowledge base response and extract context and sources"""
        context = ""
        sources = []
        
        if 'retrievalResults' in kb_response:
            total_context_length = 0
            max_context_length = 8000
            
            for i, result in enumerate(kb_response['retrievalResults']):
                if 'content' in result and 'text' in result['content']:
                    chunk_text = result['content']['text']

                    if 'meeting_date' in result['metadata']:
                        meeting_date = result['metadata']['meeting_date']

                    else:
                        meeting_date = "NA"
                    
                    # Always add for now (test = 0)
                    # if total_context_length + len(chunk_text) <= max_context_length:
                    context += f"[Source {i+1}]: Meeting Date: {meeting_date} {chunk_text}\n\n"
                    total_context_length += len(chunk_text)
                    
                    # Extract source metadata
                    source_info = {
                        "filename": f"Source {i+1}", 
                        "url": None, 
                        "s3Uri": None, 
                        "presignedUrl": None
                    }
                    
                    if 'location' in result:
                        s3_location = result['location'].get('s3Location', {})
                        if 'uri' in s3_location:
                            s3_uri = s3_location['uri']
                            filename = s3_uri.split('/')[-1]
                            source_info["filename"] = filename
                            source_info["s3Uri"] = s3_uri
                            
                            # Generate pre-signed URL with page number if available
                            presigned_url = self.generate_presigned_url(s3_uri)
                            page_number = result.get('metadata', {}).get('x-amz-bedrock-kb-document-page-number')
                            if page_number and presigned_url:
                                source_info["presignedUrl"] = f"{presigned_url}#page={page_number}"
                            else:
                                source_info["presignedUrl"] = presigned_url
                            
                            # Check for source URL in metadata
                            if 'metadata' in result and 'source' in result['metadata']:
                                source_info["url"] = result['metadata']['source']
                    
                    sources.append(source_info)
                else:
                    break

        
        return context, sources
    
    def generate_presigned_url(self, s3_uri: str) -> str:
        """Generate pre-signed URL for S3 object"""
        try:
            if not s3_uri.startswith('s3://'):
                return None
                
            s3_path = s3_uri[5:]
            bucket_name = s3_path.split('/')[0]
            object_key = '/'.join(s3_path.split('/')[1:])
            
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': object_key},
                ExpiresIn=3600
            )
            
            return presigned_url
            
        except Exception as e:
            return None
    
    def generate_response(self, query: str, context: str, query_type: str, conversation_context: str) -> Tuple[str, float]:
        """Generate response using Claude with conversation context"""
        start_time = time.time()
        
        try:
            if query_type == 'greeting':
                response_text = """Hello! I'm here to help you with information about our schools. Ask me about:

- Academic programs and curriculum
- School hours and schedules  
- Contact information and staff directory
- Sports and extracurricular activities
- Transportation and bus routes
- Lunch menus and nutrition
- School calendar and events
- Enrollment and registration
- School policies and procedures

What would you like to know about Orcutt Schools?"""
                
            elif query_type == 'farewell':
                response_text = "Thank you for using the Orcutt Schools Assistant! If you have any more questions about our schools, feel free to ask anytime. Have a great day!"
                
            else:  # knowledge_base
                prompt = f"""
You are an intelligent assistant for Orcutt Schools that provides helpful information to students, parents, staff, and community members.

Today's date is {date.today()}. Answer according to today's date

Recent conversation context:
{conversation_context}

Knowledge Base Context:
{context}

Current User Question: {query}

Use retrieved context to provide accurate, detailed responses
If information is insufficient, clearly state "I don't have specific information about [topic]"
Suggest contacting Orcutt Schools directly when appropriate
NEVER say "The provided context does not relate to your question"
If the meeting_date for sources is given, use the source with the latest meeting_date but do not mention the meeting_date in your answer

STEP-BY-STEP GUIDANCE:
For complex processes (enrollment, registration, applications), provide complete information first
At the end of complex responses, ask: "Would you like me to walk you through this step-by-step instead?"
If user requests step-by-step guidance, break down the previous response into individual steps
Strictly Present one step at a time and wait for user confirmation before continuing
Handle topic changes gracefully - if user asks new questions, start fresh

RESPONSE GUIDELINES:
Be conversational and helpful, not robotic
Provide specific details when available (dates, contact info, requirements)
Structure responses clearly with relevant details
Double-check contact information for accuracy
Suggest related resources or next steps when appropriate
Always prioritize accuracy, helpfulness, and user experience in your responses.
Do not explain your reasoning of the response
"""

                body = {
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000,
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "anthropic_version": "bedrock-2023-05-31"
                }
                
                response = self.bedrock_client.invoke_model(
                    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                    body=json.dumps(body),
                    contentType='application/json'
                )
                
                response_body = json.loads(response['body'].read())
                response_text = response_body['content'][0]['text']
            
            response_time = round(time.time() - start_time, 2)
            return response_text, response_time
                
        except Exception as e:
            return "I'm sorry, I encountered an error while processing your request. Please try again or contact the school directly for assistance.", 0