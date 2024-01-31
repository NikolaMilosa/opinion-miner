import openai
from bs4 import BeautifulSoup

def find_sentiment(search_term, text):
    soup = BeautifulSoup(text, 'html.parser')
    sentences = soup.get_text(separator=' ', strip=True).split('.')
    client = openai.OpenAI(
        api_key='something',
        base_url="http://localhost:8000",
    )
    total= []
    for i in range(0, len(sentences), 3):
        messages = [{
                    "role": "user",
                    "content": f"""You are a research scientist and your role is to devise the sentiment of a search term in a given text. The search term will be a couple of words and the text will be scraped text. The sentiment values that you have to return can be one of 'Really Positive', 'Positive', 'Neutral' 'Negative', 'Really Negative'. You will be sent a lot of sentences and when you receive a message 'Decide' you should return one work from return options.
                    For example: 
                    user:'I use Python somewhat regularly, and overall I consider it to be a very good language. Nonetheless, no language is perfect.'
                    user: 'Decide'
                    You should return 'Positive'

                    Given the previous instruction devise the sentiment value of '{search_term}' in the following sentences:
                    """
                }] + [{
                    "role": "user",
                    "content": sentence
                } for sentence in sentences[i:i+2]] + [{
                    "role": "user",
                    "content": "Decide"
                }]
        completion = client.chat.completions.create(
            model= "any",
            messages= messages)
        total.append(completion.choices[0].message.content.strip().lower())
    return max(set(total), key=total.count)

