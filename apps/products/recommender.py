import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from django.conf import settings

class DjangoContentRecommender:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DjangoContentRecommender, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.df = None
        self.tfidf_matrix = None
        self.initialized = True

    def train(self):
        """Fetches products from Django ORM and trains the model."""
        from .models import Product  # Lazy import to avoid circular dependency
        
        # Querying via ORM is cleaner in Django
        products = Product.objects.filter(is_active=True).values('id', 'name', 'category__name', 'description')
        self.df = pd.DataFrame(list(products))

        if self.df.empty:
            print("⚠️ No products found to train recommender.")
            return

        # Create metadata soup
        self.df['metadata'] = (
            self.df['name'].fillna('') + " " + 
            self.df['category__name'].fillna('') + " " + 
            self.df['description'].fillna('')
        )
        
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df['metadata'])
        print(f"✅ Django Recommender trained with {len(self.df)} products.")

    def get_recommendations(self, product_id, n=4):
        if self.df is None or self.tfidf_matrix is None:
            return []
        try:
            idx = self.df.index[self.df['id'] == product_id][0]
            cosine_sim = linear_kernel(self.tfidf_matrix[idx], self.tfidf_matrix).flatten()
            related_indices = cosine_sim.argsort()[:-(n+2):-1]
            return [int(self.df.iloc[i]['id']) for i in related_indices if self.df.iloc[i]['id'] != product_id]
        except (IndexError, Exception):
            return []

# Create a global instance
recommender_engine = DjangoContentRecommender()