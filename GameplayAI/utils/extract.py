import re

def extract_from_language(raw_content, language=''):
    try:
        text = re.findall(r'```' + language + r'\s+(.*?)\s+```', raw_content, re.DOTALL)[-1]
    except:
        text = raw_content
    return text