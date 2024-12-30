from flask import Flask, render_template, request, jsonify
import pandas as pd
import ast
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

# Load and preprocess data
movies_path = 'tmdb_5000_movies.csv'
credits_path = 'tmdb_5000_credits.csv'
movies = pd.read_csv(movies_path)
credits = pd.read_csv(credits_path)

credits.rename(columns={'movie_id': 'id'}, inplace=True)
data = movies.merge(credits, on='id')

def parse_col(col):
    return col.apply(lambda x: [i['name'] for i in ast.literal_eval(x)] if pd.notna(x) else [])

data['genres'] = parse_col(data['genres'])
data['cast'] = parse_col(data['cast'])
data['crew'] = data['crew'].apply(lambda x: [i['name'] for i in ast.literal_eval(x) if i['job'] == 'Director'] if pd.notna(x) else [])
data['keywords'] = parse_col(data['keywords'])

data['combined_features'] = data['genres'].apply(lambda x: ' '.join(x)) + ' ' + \
                           data['cast'].apply(lambda x: ' '.join(x)) + ' ' + \
                           data['crew'].apply(lambda x: ' '.join(x)) + ' ' + \
                           data['keywords'].apply(lambda x: ' '.join(x))

# Vectorize and calculate cosine similarity
vectorizer = TfidfVectorizer(stop_words='english')
feature_matrix = vectorizer.fit_transform(data['combined_features'].fillna(''))
similarity_matrix = cosine_similarity(feature_matrix, feature_matrix)

# Function to get movie recommendations
def get_recommendations(title, top_n=10):
    try:
        movie_idx = data[data['title'].str.lower() == title.lower()].index[0]
        similarity_scores = list(enumerate(similarity_matrix[movie_idx]))
        similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)
        top_movies = [data.iloc[i[0]] for i in similarity_scores[1:top_n + 1]]

        # Fetch poster data using OMDb API
        api_key = "2b2ffd38"
        results = []
        for movie in top_movies:
            omdb_response = requests.get(f"https://www.omdbapi.com/?t={movie['title']}&apikey={api_key}").json()
            results.append({
                'title': movie['title'],
                'year': movie['release_date'][:4] if pd.notna(movie['release_date']) else 'Unknown',
                'poster': omdb_response.get('Poster', 'https://via.placeholder.com/150')
            })
        return results
    except IndexError:
        return []

@app.route('/')
def home():
    return render_template('movie.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    movie_title = request.json.get('title')
    if not movie_title:
        return jsonify({'error': 'No movie title provided'}), 400

    recommendations = get_recommendations(movie_title)
    if recommendations:
        return jsonify(recommendations)
    else:
        return jsonify({'error': 'No recommendations found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
