
import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load env variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app import create_app
from app.models.document import Document
from app.extensions.database import db

app = create_app()

with app.app_context():
    total = Document.query.count()
    with_size = Document.query.filter(Document.file_size != None).count()
    zero_size = Document.query.filter(Document.file_size == 0).count()
    
    print(f"Total documents: {total}")
    print(f"With size set: {with_size}")
    print(f"With size = 0: {zero_size}")
    
    docs = Document.query.limit(5).all()
    for d in docs:
        print(f"ID: {d.id}, Size: {d.file_size}, Path: {d.file_path}")
