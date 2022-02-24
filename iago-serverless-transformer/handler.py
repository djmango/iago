import json
import logging
from pathlib import Path

from sentence_transformers import SentenceTransformer

HERE = Path(__file__).parent
logger = logging.getLogger(__name__)

model_name = 'all-mpnet-base-v2'
model: SentenceTransformer
try:
    model = SentenceTransformer(HERE/'models'/model_name)
except Exception as e:
    raise(e)

def handler(event, context):
    try:
        logger.info(event)
        logger.info(context)
        
        strings = json.loads(event['strings']) # should be a list of strings
        
        embeds = model.encode(strings, convert_to_numpy=True)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True

            },
            'body': json.dumps({'embeds': embeds.tolist(), 'model': model_name})
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
