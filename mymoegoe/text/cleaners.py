import re
def cjke_cleaners2(text):
    from mymoegoe.text.english import english_to_ipa2
    text = re.sub(r'^(.*?)$',
                  lambda x: english_to_ipa2(x.group(1))+' ', text)
    text = re.sub(r'\s+$', '', text)
    text = re.sub(r'([^\.,!\?\-…~])$', r'\1.', text)
    return text
