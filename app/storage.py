import os
from flask import current_app
from supabase import create_client, Client

def get_supabase_client() -> Client:
    """Get a Supabase client using environment variables"""
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        current_app.logger.warning("Supabase credentials not found. File storage in cloud disabled.")
        return None
    
    try:
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        current_app.logger.error(f"Error creating Supabase client: {e}")
        return None

def upload_file(file_path, destination_path, bucket="uploads"):
    """
    Upload a file to Supabase Storage
    
    Parameters:
    - file_path: Local path to the file
    - destination_path: Path in Supabase where the file should be stored
    - bucket: Supabase Storage bucket name
    
    Returns:
    - Public URL if successful, None if failed
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
            
        # Upload to Supabase Storage
        response = client.storage.from_(bucket).upload(
            path=destination_path,
            file=file_data,
            file_options={"content-type": "auto"}
        )
        
        # Get the public URL
        url = client.storage.from_(bucket).get_public_url(destination_path)
        current_app.logger.info(f"Uploaded file to Supabase: {url}")
        return url
        
    except Exception as e:
        current_app.logger.error(f"Error uploading file to Supabase: {e}")
        return None

def get_file_url(file_path, bucket="uploads"):
    """
    Get the public URL for a file in Supabase Storage
    
    Parameters:
    - file_path: Path in Supabase where the file is stored
    - bucket: Supabase Storage bucket name
    
    Returns:
    - Public URL
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        return client.storage.from_(bucket).get_public_url(file_path)
    except Exception as e:
        current_app.logger.error(f"Error getting file URL from Supabase: {e}")
        return None

def delete_file(file_path, bucket="uploads"):
    """
    Delete a file from Supabase Storage
    
    Parameters:
    - file_path: Path in Supabase where the file is stored
    - bucket: Supabase Storage bucket name
    
    Returns:
    - True if successful, False if failed
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        client.storage.from_(bucket).remove([file_path])
        return True
    except Exception as e:
        current_app.logger.error(f"Error deleting file from Supabase: {e}")
        return False