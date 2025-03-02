# from flask import Flask, request, jsonify, render_template
# import pandas as pd
# import os
# import numpy as np

# app = Flask(__name__, template_folder="templates")

# # Load the CSV data
# def load_data():
#     # csv_path = 'medium_articles.csv' # for development
#     csv_path = os.path.join(os.path.dirname(__file__), 'medium_articles.csv')  # for deployment to render

#     if not os.path.exists(csv_path):
#         return None

#     try:
#         df = pd.read_csv(csv_path, encoding='utf-8')
#         return df
#     except Exception as e:
#         print(f"Error loading CSV: {str(e)}")
#         return None

# # API route for searching articles by keywords in title
# @app.route('/search', methods=['GET'])
# def search_articles():
#     keyword = request.args.get('keyword', '').strip()

#     if not keyword:
#         return jsonify({
#             'error': 'Please provide a keyword parameter',
#             'example': '/search?keyword=python'
#         }), 400

#     df = load_data()

#     if df is None:
#         return jsonify({'error': 'Could not load article data'}), 500

#     matching_articles = df[df['title'].str.contains(keyword, case=False, na=False)]

#     # Fix: Replace NaN values with None so that JSON doesn't break
#     results = matching_articles.replace({np.nan: None}).to_dict(orient='records')

#     return jsonify({
#         'keyword': keyword,
#         'count': len(results),
#         'results': results
#     })

# # Serve the frontend HTML
# @app.route('/')
# def home():
#     return render_template('index.html')

# # Run the application
# if __name__ == '__main__':
#     df = load_data()
#     if df is not None:
#         print(f"Loaded {len(df)} articles from CSV")
#     else:
#         print("Warning: Could not load article data. Make sure 'medium_articles.csv' exists.")

#     app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)

from flask import Flask, request, jsonify, render_template
import pandas as pd
import os
import numpy as np

app = Flask(__name__, template_folder="templates")

# Load the CSV data
def load_data():
    csv_path = os.path.join(os.path.dirname(__file__), 'medium_articles.csv')  # Correct CSV path

    if not os.path.exists(csv_path):
        return None

    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
        return df
    except Exception as e:
        print(f"Error loading CSV: {str(e)}")
        return None

# API route for searching articles
@app.route('/search', methods=['GET'])
def search_articles():
    keyword = request.args.get('keyword', '').strip()

    if not keyword:
        return jsonify({
            'error': 'Please provide a keyword parameter',
            'example': '/search?keyword=python'
        }), 400

    df = load_data()

    if df is None:
        return jsonify({'error': 'Could not load article data'}), 500

    matching_articles = df[df['title'].str.contains(keyword, case=False, na=False)]
    results = matching_articles.replace({np.nan: None}).to_dict(orient='records')

    return jsonify({
        'keyword': keyword,
        'count': len(results),
        'results': results
    })

# Serve the frontend
@app.route('/')
def home():
    return render_template('index.html')

# Run the application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=False)
