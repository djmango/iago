from src.sentence_encoder import SentenceEncoder
import numpy as np

pipeline = SentenceEncoder()

def test_response(requests, response):
    assert np.allclose(np.array(response['vectors']), np.array(pipeline(requests)['vectors']), atol=1e-3)
