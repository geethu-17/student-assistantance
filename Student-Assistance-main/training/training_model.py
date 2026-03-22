# ==========================================
# 1. Import Libraries
# ==========================================

import json
import numpy as np
import tensorflow as tf
import pickle
from pathlib import Path

from tensorflow.keras.layers import Input, Embedding, LSTM, Dense
from tensorflow.keras.models import Model
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from sklearn.preprocessing import LabelEncoder


# ==========================================
# 2. Load Dataset
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
INTENTS_PATH = BASE_DIR / "intents.json"

with INTENTS_PATH.open("r", encoding="utf-8") as file:
    data = json.load(file)

texts = []
labels = []

for intent in data["intents"]:
    for sentence in intent["text"]:
        texts.append(sentence)
        labels.append(intent["intent"])

print("Total training sentences:", len(texts))


# ==========================================
# 3. Tokenize Text
# ==========================================

tokenizer = Tokenizer(oov_token="<OOV>")
tokenizer.fit_on_texts(texts)

sequences = tokenizer.texts_to_sequences(texts)

# Save tokenizer
with (BASE_DIR / "tokenizer.pickle").open("wb") as f:
    pickle.dump(tokenizer, f)


# ==========================================
# 4. Padding Sequences
# ==========================================

max_len = max(len(seq) for seq in sequences)

padded_sequences = pad_sequences(
    sequences,
    maxlen=max_len,
    padding="post"
)

# Save max length
with (BASE_DIR / "max_len.pickle").open("wb") as f:
    pickle.dump(max_len, f)


# ==========================================
# 5. Encode Labels
# ==========================================

label_encoder = LabelEncoder()
encoded_labels = label_encoder.fit_transform(labels)

num_classes = len(label_encoder.classes_)

encoded_labels = tf.keras.utils.to_categorical(encoded_labels, num_classes)

# Save label encoder
with (BASE_DIR / "label_encoder.pickle").open("wb") as f:
    pickle.dump(label_encoder, f)


# ==========================================
# 6. Build LSTM Model
# ==========================================

input_layer = Input(shape=(max_len,))

embedding = Embedding(
    input_dim=len(tokenizer.word_index) + 1,
    output_dim=128
)(input_layer)

lstm = LSTM(128)(embedding)

output_layer = Dense(
    num_classes,
    activation="softmax"
)(lstm)

model = Model(inputs=input_layer, outputs=output_layer)


# ==========================================
# 7. Compile Model
# ==========================================

model.compile(
    optimizer="adam",
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

model.summary()


# ==========================================
# 8. Train Model
# ==========================================

history = model.fit(
    padded_sequences,
    encoded_labels,
    epochs=50,
    batch_size=16,
    verbose=1
)


# ==========================================
# 9. Save Model
# ==========================================

model.save(str(BASE_DIR / "chatbot_model.h5"))

print("Model training complete.")
print("Saved files:")
print("- chatbot_model.h5")
print("- tokenizer.pickle")
print("- label_encoder.pickle")
print("- max_len.pickle")

