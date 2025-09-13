#!/usr/bin/env python
"""
Script to create and run migrations for new models
Run this file to update database with new features
"""

import os
import sys
import django

# Setup Django
if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

    from django.core.management import execute_from_command_line

    # Create migrations for new models
    print("Creating migrations for new models...")
    
    # Make migrations for reviews app (ReviewReply model)
    execute_from_command_line(['manage.py', 'makemigrations', 'reviews'])
    
    # Make migrations for core app (UserActivity model)  
    execute_from_command_line(['manage.py', 'makemigrations', 'core'])
    
    # Apply all migrations
    print("Applying migrations...")
    execute_from_command_line(['manage.py', 'migrate'])
    
    print("Database updated successfully!")
    print("\nNew features added:")
    print("✅ Reply system for reviews")
    print("✅ User activity tracking")
    print("✅ Enhanced personalized recommendations")
    print("✅ Recently viewed restaurants")