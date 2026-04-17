
import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load env variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app import create_app
from app.models.document import Document
from app.extensions.database import db
from sqlalchemy import or_

app = create_app()

with app.app_context():
    # Find docs without size
    docs = Document.query.filter(or_(Document.file_size == None, Document.file_size == 0)).all()
    print(f"Found {len(docs)} documents to update.")
    
    count = 0
    not_found = 0
    
    for doc in docs:
        file_path = doc.file_path
        
        project_root = Path(app.root_path).parent
        
        # If path starts with /, remove it
        if file_path.startswith('/') or file_path.startswith('\\'):
            file_path = file_path[1:]
            
        full_path = project_root / file_path
        
        if full_path.exists():
            size = os.path.getsize(full_path)
            doc.file_size = size
            count += 1
            print(f"Updated {doc.id}: {size} bytes")
        else:
            # Try checking in static/ if legacy
            static_path = Path(app.root_path) / 'static' / file_path
            if static_path.exists():
                size = os.path.getsize(static_path)
                doc.file_size = size
                count += 1
                print(f"Updated {doc.id} (from static): {size} bytes")
            else:
                print(f"File not found for {doc.id}: {full_path}")
                not_found += 1
    
    db.session.commit()
    print(f"Finished. Updated: {count}. Not Found: {not_found}")
