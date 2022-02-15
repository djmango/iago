from time import perf_counter
start = perf_counter()

from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F
print(f'Load took {round(perf_counter() - start, 2)}s')


#Mean Pooling - Take attention mask into account for correct averaging
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


# Sentences we want sentence embeddings for
sentences = ['This is an example sentence', 'Each sentence is converted']

# Load model from HuggingFace Hub
tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-mpnet-base-v2')
model = AutoModel.from_pretrained('sentence-transformers/all-mpnet-base-v2')

print(f'Model load took {round(perf_counter() - start, 2)}s')


# Tokenize sentences
encoded_input = tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')

# Compute token embeddings
with torch.no_grad():
    model_output = model(**encoded_input)

# Perform pooling
sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])

# Normalize embeddings
sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

# from sentence_transformers import SentenceTransformer
# print(f'Load took {round(perf_counter() - start, 2)}s')
# sentences = ["This is an example sentence", "Each sentence is converted"]

# model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
# print(f'Model load took {round(perf_counter() - start, 2)}s')
# sentence_embeddings = model.encode(sentences)

print(f'Execution took {round(perf_counter() - start, 2)}s')
print("Sentence embeddings:")
print(sentence_embeddings)