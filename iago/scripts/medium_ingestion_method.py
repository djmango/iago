# import header

import requests
import re
import json

def insert_string_by_index(string1, string2, start_i, stop_i):
    return string1[:start_i] + string2 + string1[stop_i:]


url = "https://serverless.iago.jeeny.ai:443/medium"

payload = json.dumps({
    "url": "https://medium.com/serverlessguru/amazon-api-gateway-http-apis-with-the-serverless-framework-7be95f305318"
})
headers = {
    'Authorization': 'Basic e3tVU0VSfX06e3tQQVNTfX0=',
    'Content-Type': 'application/json'
}

response = requests.post(url, headers=headers, data=payload)
paragraphs = response.json()['payload']['value']['content']['bodyModel']['paragraphs']
output = ""

def medium_to_markdown(text_block, last_type, i=0) -> str:
    # medium types

    # text blocks
    # 1 is normal text
    # 3 is header
    # 4 is image
    # 6 is quote
    # 8 is code block
    # 9 is bullet list
    # 11 is iframe, not easy to handle
    # 13 is a subtitle

    # markup
    # 1 is bold
    # 3 is link
    # 10 is inline code
 
    # first we do inline markup
    # so to since making something markup changes its char count, we have to keep track of the original string and the new string and keep an index of where the last change ended in the original string
    original_text = text_block['text']
    markdown_text = ""
    last_index = 0
    if len(text_block['markups']) > 0:
        for markup in text_block['markups']:
            modified_subtext = original_text[markup['start']-last_index:markup['end']-last_index] # we only want to edit the part that has the rule applied to it
            if markup['type'] == 1:
                modified_subtext = "**" + modified_subtext + "**"
            elif markup['type'] == 2:
                modified_subtext = "*" + modified_subtext + "*"
            elif markup['type'] == 3:
                modified_subtext = "[" + modified_subtext + "]" + "(" + markup['href'] + ")"
            
            markdown_text += original_text[:markup['start']-last_index] + modified_subtext
            original_text = original_text[markup['end']-last_index:]
            last_index = markup['end']

        # add the rest of the text that hasn't been modified
    markdown_text += original_text

    # then we clean up the text
    # NOTE we cant do this it will break our new inline markup - gotta figure out a way to differentiate between markup we add and the accidental stuff thats there because of unclean text
    # https://tech.saigonist.com/b/code/escaping-special-characters-markdown.html
    # text = text.replace('_', '\_').replace('*', '\*').replace('`', '\`')
    text = markdown_text

    # then we format the whole block according to the type
    if text_block['type'] == 1: # normal text
        pass
    elif text_block['type'] == 3: # header
        if i == 0: # title
            text = f"# {text}"
        else:
            text = f"## {text}"
    elif text_block['type'] == 4: # image
        # validate image
        if 'metadata' not in text_block or 'id' not in text_block['metadata'] or re.findall(r'^0\*.{10,20}\.png', text_block['metadata']['id']) == None:
            raise ValueError(f'Block {text_block["id"]} has no image id or is not a png')
        image_url = f'https://miro.medium.com/{text_block["metadata"]["id"]}'
        text = f'![alt text]({image_url} "{text}")\n\n{text}' # add a caption on hover and below
    elif text_block['type'] == 6: # quote
        text = f'> {text}'
    elif text_block['type'] == 8: # code block or quote, dont set language cuz we dont know it
        text = f"```\n{text}\n```"
    elif text_block['type'] == 9: # bullet list
        text = f"* {text}"
    elif text_block['type'] == 11: # iframe, just post the thumbnail, we wont include the actual iframe
        text = f'![alt text]({text_block["iframe"]["thumbnailurl"]} "{text}"'
    elif text_block['type'] == 13: # subtitle
        text = f"### {text}"
    else: # unknown type
        print(f'Unknown type {text_block["type"]} for id {text_block["name"]}')

    # finally we need to decide if we want 1, 2, or 3 newlines at the end
    if last_type == 9: # 1 only if we have a sequential list
        text = f"{text}\n"
    elif text_block['type'] != 3: # 2 is between paragraphs in the same section
        text = f"{text}\n\n"
    else: # 2 is to seperae sections (i.e. new headers), was 3 but actually it renders the same soo
        text = f"{text}\n\n"

    return str(text)

for i, text_block in enumerate(paragraphs):
    if i > 0:
        text = medium_to_markdown(text_block, paragraphs[i-1]['type'])
    else:
        text = medium_to_markdown(text_block, None)
    
    output += text

with open('medium_ingestion_method.md', 'w') as f:
    f.write(output)

print('done!')
