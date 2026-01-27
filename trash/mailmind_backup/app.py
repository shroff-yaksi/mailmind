from flask import Flask, jsonify, request, render_template, send_from_directory
from mailmind import DatabaseManager, EmailProcessor, OpenRouterClient, load_config
import threading
import os
import json
from flask_cors import CORS
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

db = DatabaseManager()
config = load_config()

# Get OpenRouter API key from environment or config
# Check both top-level and nested structure
openrouter_api_key = os.environ.get('OPENROUTER_API_KEY', '')
if not openrouter_api_key:
    openrouter_api_key = config.get('openrouter_api_key', '')
    if not openrouter_api_key and 'openrouter' in config:
        openrouter_api_key = config['openrouter'].get('api_key', '')

# Set default AI model to Sarvam AI
ai_model = "mistralai/mistral-7b-instruct:free"
if 'openrouter' in config and 'model' in config['openrouter']:
    ai_model = config['openrouter']['model']

# Get signature from config
signature = ""
if 'signature' in config:
    signature = config['signature']
elif 'settings' in config and 'signature' in config['settings']:
    signature = config['settings']['signature']

# Get check interval from config
check_interval = 300
if 'check_interval' in config:
    check_interval = config['check_interval']
elif 'settings' in config and 'check_interval' in config['settings']:
    check_interval = config['settings']['check_interval']

email_config = None
if 'email' in config:
    email_config = config['email']
    from mailmind import EmailConfig
    email_config = EmailConfig(**email_config)

email_processor = None
if email_config and openrouter_api_key:
    try:
        # Create OpenRouterClient with the Sarvam AI model
        openrouter_client = OpenRouterClient(openrouter_api_key, model=ai_model)
        
        # Create EmailProcessor with the configured OpenRouterClient
        email_processor = EmailProcessor(
            email_config, 
            openrouter_api_key,
            signature=signature,
            response_delay=check_interval
        )
        
        # Override the default AI client with our custom one
        email_processor.ai_client = openrouter_client
        logger.info("Email processor initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing email processor: {e}")

monitoring_thread = None
monitoring_active = False

def start_monitoring():
    global monitoring_thread, monitoring_active
    if not monitoring_active and email_processor:
        try:
            monitoring_active = True
            monitoring_thread = threading.Thread(target=email_processor.start_monitoring)
            monitoring_thread.daemon = True
            monitoring_thread.start()
            logger.info("Monitoring started")
            return True
        except Exception as e:
            monitoring_active = False
            logger.error(f"Error starting monitoring: {e}")
            return False
    return False

def stop_monitoring():
    global monitoring_active
    if monitoring_active and email_processor:
        try:
            email_processor.stop_monitoring()
            monitoring_active = False
            logger.info("Monitoring stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
            return False
    return False

@app.route('/')
def index():
    """Serve the main application page."""
    return render_template('index.html')

@app.route('/api/emails', methods=['GET'])
def get_emails():
    """Return all emails from the database."""
    try:
        emails = db.get_unreplied_emails()
        return jsonify([{
            'msg_id': email.msg_id,
            'sender': email.sender,
            'subject': email.subject,
            'body': email.body,
            'timestamp': email.timestamp.isoformat(),
            'thread_id': email.thread_id,
            'is_replied': email.is_replied
        } for email in emails])
    except Exception as e:
        logger.error(f"Error getting emails: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/fetch', methods=['POST'])
def fetch_emails():
    """Fetch new emails and store them in the database."""
    if not email_processor:
        logger.error("Email processor not configured")
        return jsonify({'error': 'Email processor not configured. Please check your email settings.'}), 400
    
    try:
        new_emails = email_processor.fetch_new_emails()
        logger.info(f"Fetched {len(new_emails)} new emails")
        return jsonify({'fetched': len(new_emails)})
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/respond', methods=['POST'])
def respond_to_emails():
    """Generate and send responses to unreplied emails."""
    if not email_processor:
        logger.error("Email processor not configured")
        return jsonify({'error': 'Email processor not configured. Please check your email settings.'}), 400
    
    try:
        unreplied = db.get_unreplied_emails()
        for email in unreplied:
            email_processor.generate_and_send_response(email)
        logger.info(f"Responded to {len(unreplied)} emails")
        return jsonify({'responded': len(unreplied)})
    except Exception as e:
        logger.error(f"Error responding to emails: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/monitoring', methods=['POST'])
def toggle_monitoring():
    """Start or stop monitoring for new emails."""
    action = request.json.get('action')
    if action == 'start':
        success = start_monitoring()
        return jsonify({'monitoring': monitoring_active, 'success': success})
    elif action == 'stop':
        success = stop_monitoring()
        return jsonify({'monitoring': monitoring_active, 'success': success})
    else:
        return jsonify({'error': 'Invalid action'}), 400

@app.route('/api/status', methods=['GET'])
def get_status():
    """Return status of the monitoring thread."""
    processor_configured = email_processor is not None
    return jsonify({
        'monitoring': monitoring_active,
        'processor_configured': processor_configured,
        'api_key_configured': bool(openrouter_api_key),
        'email_configured': email_config is not None
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Return the last 100 lines of the log file."""
    try:
        with open('mailmind.log', 'r') as f:
            lines = f.readlines()[-100:]
        return jsonify({'logs': lines})
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """Get or update application settings."""
    global config, email_config, email_processor, openrouter_api_key, signature, check_interval
    
    if request.method == 'GET':
        # Return current settings (without sensitive data like passwords)
        safe_config = {
            'email': {},
            'openrouter': {},
            'settings': {}
        }
        
        # Email settings
        if 'email' in config:
            safe_config['email'] = config['email'].copy()
            if 'password' in safe_config['email']:
                safe_config['email']['password'] = '********'  # Mask password
        
        # OpenRouter settings
        safe_config['openrouter']['api_key'] = '********' if openrouter_api_key else ''
        safe_config['openrouter']['model'] = ai_model
        
        # Other settings
        safe_config['settings']['signature'] = signature
        safe_config['settings']['check_interval'] = check_interval
        
        return jsonify(safe_config)
    else:
        # Update settings
        try:
            new_config = request.json
            logger.info(f"Received settings update: {new_config}")
            
            if not new_config:
                return jsonify({'error': 'No configuration data provided'}), 400
            
            # Load the existing config first to avoid overwriting values
            current_config = load_config() or {}
            
            # Structure the config properly
            structured_config = {
                'email': current_config.get('email', {}),
                'openrouter': current_config.get('openrouter', {'model': ai_model}),
                'settings': current_config.get('settings', {})
            }
            
            # Email settings
            if 'email' in new_config:
                # Update email settings but preserve password if not provided
                if 'password' not in new_config['email'] and 'password' in structured_config['email']:
                    new_config['email']['password'] = structured_config['email']['password']
                structured_config['email'].update(new_config['email'])
                logger.info("Updated email settings")
            
            # OpenRouter settings
            if 'openrouter' in new_config:
                # Update OpenRouter settings but preserve API key if not provided
                if 'api_key' not in new_config['openrouter'] and 'api_key' in structured_config['openrouter']:
                    new_config['openrouter']['api_key'] = structured_config['openrouter']['api_key']
                structured_config['openrouter'].update(new_config['openrouter'])
                logger.info("Updated OpenRouter settings")
            
            # Other settings
            if 'settings' in new_config:
                structured_config['settings'].update(new_config['settings'])
                logger.info("Updated general settings")
            
            # Save to config.json
            try:
                with open('config.json', 'w') as f:
                    json.dump(structured_config, f, indent=2)
                logger.info("Config file saved successfully")
            except Exception as e:
                logger.error(f"Error saving config file: {e}")
                return jsonify({'error': f'Failed to save config file: {str(e)}'}), 500
            
            # Reload configuration
            try:
                config = load_config()
                logger.info("Config reloaded successfully")
            except Exception as e:
                logger.error(f"Error reloading config: {e}")
                return jsonify({'error': f'Failed to reload config: {str(e)}'}), 500
            
            # Get OpenRouter API key
            openrouter_api_key = os.environ.get('OPENROUTER_API_KEY', '')
            if not openrouter_api_key:
                openrouter_api_key = config.get('openrouter_api_key', '') if config else ''
                if not openrouter_api_key and config and 'openrouter' in config:
                    openrouter_api_key = config['openrouter'].get('api_key', '')
            
            # Get signature
            signature = ""
            if 'signature' in config:
                signature = config['signature']
            elif 'settings' in config and 'signature' in config['settings']:
                signature = config['settings']['signature']
            
            # Get check interval
            check_interval = 300
            if 'check_interval' in config:
                check_interval = config['check_interval']
            elif 'settings' in config and 'check_interval' in config['settings']:
                check_interval = config['settings']['check_interval']
            
            # Reinitialize email processor if email config is available
            if 'email' in config:
                try:
                    from mailmind import EmailConfig
                    email_config = EmailConfig(**config['email'])
                    
                    if email_config and openrouter_api_key:
                        try:
                            # Create OpenRouterClient with the Sarvam AI model
                            openrouter_client = OpenRouterClient(openrouter_api_key, model=ai_model)
                            
                            # Create EmailProcessor with the configured OpenRouterClient
                            email_processor = EmailProcessor(
                                email_config, 
                                openrouter_api_key,
                                signature=signature,
                                response_delay=check_interval
                            )
                            
                            # Override the default AI client with our custom one
                            email_processor.ai_client = openrouter_client
                            logger.info("Email processor reinitialized successfully")
                        except Exception as e:
                            logger.error(f"Error reinitializing email processor: {e}")
                            return jsonify({'error': f'Failed to initialize email processor: {str(e)}'}), 500
                except Exception as e:
                    logger.error(f"Error creating EmailConfig: {e}")
                    return jsonify({'error': f'Failed to create EmailConfig: {str(e)}'}), 500
            
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Unexpected error in settings endpoint: {e}")
            return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 