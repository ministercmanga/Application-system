import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# Load and prepare your model
def train_model():
    # Load your dataset
    df = pd.read_csv("generated_Data.csv")
    df = df.reset_index(drop=True)

    df['Subject'], _ = pd.factorize(df['Subject'])

    x = df.drop(columns=['Final', 'Subject'])
    y = df['Final']  

    model = LinearRegression()
    model.fit(x, y)

    return model

# Make predictions based on input percentages
def predict_percentages(model, subjects_features):
    # Example feature names (columns in the model)
    feature_names = ['Grade 11', 'March', 'June', 'September']

    # Convert input data into a pandas DataFrame with the correct feature names
    subjects_df = pd.DataFrame(subjects_features, columns=feature_names)

    # Make predictions using the model
    predictions = model.predict(subjects_df)

    # Round the predictions to the nearest integer and return
    return np.round(predictions).astype(int)