from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# Supabase production connection with service_role key (admin access)
SUPABASE_URL = "https://hxkzdyrwdfbkdkhslfmk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh4a3pkeXJ3ZGZia2RraHNsZm1rIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTUyNDA1NiwiZXhwIjoyMDY1MTAwMDU2fQ.tMwHsM4yE8XwepeM8nnwuav-Y6exuEGgDVtp6GT-8KI"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def discover_tables():
    """Discover what tables exist in Supabase"""
    try:
        # Get schema information
        response = supabase.rpc('get_schema_tables').execute()
        print("📊 Available tables:")
        for table in response.data:
            print(f"  - {table}")
        return response.data
    except Exception as e:
        print(f"RPC failed, trying direct table discovery...")
        
        # Try common table names
        common_tables = ['user', 'users', 'post', 'posts', 'prayer', 'prayers', 
                        'music', 'soundlab', 'logos', 'message', 'messages']
        
        existing_tables = []
        for table_name in common_tables:
            try:
                response = supabase.table(table_name).select("*").limit(1).execute()
                existing_tables.append(table_name)
                print(f"✅ Found table: {table_name} ({len(response.data)} sample records)")
            except Exception:
                print(f"❌ No table: {table_name}")
        
        return existing_tables

def get_table_data(table_name):
    """Get all data from a specific table"""
    try:
        response = supabase.table(table_name).select("*").execute()
        print(f"📦 {table_name}: {len(response.data)} records")
        return response.data
    except Exception as e:
        print(f"❌ Error getting {table_name}: {e}")
        return []

if __name__ == "__main__":
    print("🔍 Discovering Supabase schema...")
    tables = discover_tables()
    
    print("\n📊 Pulling data from existing tables...")
    all_data = {}
    for table in tables if isinstance(tables, list) else []:
        all_data[table] = get_table_data(table)
    
    print(f"\n✅ Data discovery complete!")
    for table, data in all_data.items():
        print(f"  {table}: {len(data)} records")
