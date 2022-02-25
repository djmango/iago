import json
import logging
from pathlib import Path

HERE = Path(__file__).parent
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger.info('loading transformers')
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

# config, temp
model_name = 'all-mpnet-base-v2'

logger.info(f'Loading tokenizer and model..')
tokenizer = AutoTokenizer.from_pretrained(HERE/'models'/f'{model_name}_tokenizer')
model = AutoModel.from_pretrained(HERE/'models'/'all-mpnet-base-v2_model')
logger.info('Loaded')

#Mean Pooling - Take attention mask into account for correct averaging
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


def handler(event, context):
    try:
        logger.info(event)
        logger.info(context)
        
        sentences = json.loads(event['strings']) # should be a list of strings
        
        # Tokenize sentences
        encoded_input = tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')

        # Compute token embeddings
        with torch.no_grad():
            model_output = model(**encoded_input)

        # Perform pooling
        sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])

        # Normalize embeddings
        sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

        print("Sentence embeddings:")
        print(sentence_embeddings.tolist())


        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True

            },
            'body': json.dumps({'embeds': sentence_embeddings.tolist(), 'model': model_name})
        }

    except Exception as e:
        logger.error(repr(e))
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            },
            'body': json.dumps({'error': repr(e)})
        }
