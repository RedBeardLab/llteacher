#!/bin/bash
set -e

# Wait for database directory to be available
while [ ! -d "/data" ]; do
    echo "Waiting for /data directory to be available..."
    sleep 1
done

# Run database migrations
echo "Running database migrations..."
uv run python manage.py migrate

# Create admin user if it doesn't exist
echo "Creating admin user..."
uv run python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('Creating superuser...')
    User.objects.create_superuser('admin', 'admin@example.com', 'jkewj323efbwiknfw3')
    print('Superuser created: admin/jkewj323efbwiknfw3')
else:
    print('Superuser already exists')
" || echo "Superuser creation skipped"

# Populate database with test data
echo "Populating database with test data..."
uv run python manage.py populate_test_database

# Start the application
echo "Starting LLTeacher application..."
exec "$@"
