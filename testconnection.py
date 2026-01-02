import json
from mailmind import EmailProcessor, EmailConfig, OpenRouterClient

def test_connection():
    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # Test email connection
    email_config = EmailConfig(
        imap_server=config["email"]["imap_server"],
        imap_port=config["email"]["imap_port"],
        smtp_server=config["email"]["smtp_server"],
        smtp_port=config["email"]["smtp_port"],
        email_address=config["email"]["email_address"],
        password=config["email"]["password"],
        use_ssl=config["email"]["use_ssl"]
    )
    
    processor = EmailProcessor(
        config=email_config,
        openrouter_api_key=config["openrouter"]["api_key"]
    )
    
    # Test connections
    try:
        imap = processor.connect_imap()
        print("✅ IMAP connection successful")
        imap.logout()
        
        smtp = processor.connect_smtp()
        print("✅ SMTP connection successful")
        smtp.quit()
        
        # Test AI
        ai_client = OpenRouterClient(config["openrouter"]["api_key"])
        response, tokens = ai_client.generate_response(
            "Test email", "uvaghasia77@gmail.com", "Test Subject"
        )
        print("✅ OpenRouter API working")
        print(f"Sample response: {response[:100]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_connection()