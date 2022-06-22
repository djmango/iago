import re

def medium_to_markdown(text_block: dict, i: int, paragraphs_raw: list[dict]) -> str:
    # medium types

    # text blocks
    # 1 is normal text
    # 3 is header
    # 4 is image
    # 6 is quote
    # 7 is also quote block
    # 8 is code block
    # 9 is bullet list
    # 10 is numbered list
    # 11 is iframe, not easy to handle
    # 13 is a subtitle
    # 14 is an embedded link

    # markup
    # 1 is bold
    # 3 is link
    # 10 is inline code
 
    # first we do inline markup
    # so to since making something markup changes its char count, we have to keep track of the original string and the new string and keep an index of where the last change ended in the original string
    original_text = text_block['text']
    markdown_text = ""
    last_index = 0
    if 'markups' in text_block and len(text_block['markups']) > 0:
        for markup in text_block['markups']:
            modified_subtext = original_text[markup['start']-last_index:markup['end']-last_index] # we only want to edit the part that has the rule applied to it
            if markup['type'] == 1:
                modified_subtext = "**" + modified_subtext + "**"
            elif markup['type'] == 2:
                modified_subtext = "*" + modified_subtext + "*"
            elif markup['type'] == 3 and 'href' in markup: # sometimes its linking to an internal reference like a user or something so we dont need to link that right now
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

    if i > 0:
        last_type = paragraphs_raw[i-1]['type']
    else:
        last_type = None
    # then we format the whole block according to the type
    if text_block['type'] == 1: # normal text
        pass
    elif text_block['type'] == 3: # header
        if last_type == None: # title
            text = f"# {text}"
        else:
            text = f"## {text}"
    elif text_block['type'] == 4: # image
        # validate image
        if 'metadata' not in text_block or 'id' not in text_block['metadata'] or re.findall(r'^0\*.{10,20}\.png', text_block['metadata']['id']) == None:
            raise ValueError(f'Block {text_block["id"]} has no image id or is not a png')
        image_url = f'https://miro.medium.com/{text_block["metadata"]["id"]}'
        text = f'![alt text]({image_url} "{text}")\n\n{text}' # add a caption on hover and below
    elif text_block['type'] == 6 or text_block['type'] == 7: # quote
        text = f'> {text}'
    elif text_block['type'] == 8: # code block or quote, dont set language cuz we dont know it
        text = f"```\n{text}\n```"
    elif text_block['type'] == 9: # bullet list
        text = f"* {text}"
    elif text_block['type'] == 10: # numbered list
        if last_type == 10: # if this is a continuation of a numbered list we have to backtrack to the previous find the current number
            k = 1
            while 1:
                if paragraphs_raw[i-k]['type'] == 10:
                    k += 1
                else:
                    break
            text = f"{k+1}. {text}" # essentially we keep looking back 1 until we find the top of the numbered list to keep the function self contained
        else:
            text = f"1. {text}" # if this is the first number we can just use 1 without checks

    elif text_block['type'] == 11: # iframe, just post the thumbnail. TODO: actual embeds are going to be a bit more difficult
        if 'thumbnailurl' in text_block['iframe']:
            text = f'![alt text]({text_block["iframe"]["thumbnailurl"]} "{text}"'
        else:
            text = f'MEDIUM_IFRAME_RESOURCE_({text_block["iframe"]["mediaResourceId"]} "{text}"'
    elif text_block['type'] == 13: # subtitle
        text = f"### {text}"
    elif text_block['type'] == 14: # embedded link
        # here the text is actually already nicely in markdown format
        pass
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