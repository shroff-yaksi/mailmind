# Email Response Templates

## Default Templates

### Out of Office
```
Subject: Out of Office: {original_subject}

Thank you for your email. I am currently out of the office and will have limited access to email.

I will respond to your message as soon as possible upon my return on {return_date}.

For urgent matters, please contact {alternate_contact}.

Best regards,
{signature}
```

### Meeting Request
```
Subject: Re: {original_subject}

Thank you for reaching out regarding a meeting.

I'd be happy to discuss this further. Please use the following link to schedule a time that works for both of us:

{calendar_link}

Alternatively, feel free to suggest a few times that work for you, and I'll do my best to accommodate.

Looking forward to connecting!

{signature}
```

### Information Request
```
Subject: Re: {original_subject}

Thank you for your inquiry.

I've received your request for information about {topic}. I'll review the details and get back to you with a comprehensive response within {response_time}.

If you have any additional questions in the meantime, please don't hesitate to reach out.

Best regards,
{signature}
```

### General Acknowledgment
```
Subject: Re: {original_subject}

Thank you for your email.

I've received your message and will review it carefully. I'll get back to you with a detailed response as soon as possible.

Best regards,
{signature}
```

### Support Request
```
Subject: Re: {original_subject}

Thank you for contacting support.

I've received your support request regarding {issue}. Your ticket number is {ticket_number}.

Our team is reviewing your case and will respond within {sla_time}. We appreciate your patience.

If you have any additional information to add, please reply to this email.

Best regards,
{signature}
```

## Template Variables

Available variables for use in templates:

- `{original_subject}` - Subject of the incoming email
- `{sender_name}` - Name of the email sender
- `{sender_email}` - Email address of sender
- `{signature}` - Your email signature
- `{date}` - Current date
- `{time}` - Current time
- `{return_date}` - Your return date (for out of office)
- `{calendar_link}` - Your calendar booking link
- `{topic}` - Extracted topic from email
- `{response_time}` - Expected response time
- `{issue}` - Issue description
- `{ticket_number}` - Generated ticket number
- `{sla_time}` - Service level agreement time
- `{alternate_contact}` - Alternate contact information

## Custom Templates

To create custom templates, add them to this file following the format above.

Template selection can be based on:
- Keywords in subject line
- Sender domain
- Email content analysis
- Time of day
- Day of week
