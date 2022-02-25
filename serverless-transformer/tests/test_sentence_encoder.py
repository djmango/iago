from src.sentence_encoder import SentenceEncoder
import numpy as np

pipeline = SentenceEncoder()

def test_response(requests, response):
    assert np.allclose(response['vectors'], pipeline(requests)['vectors'], atol=1e-3)
