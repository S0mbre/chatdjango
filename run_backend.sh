cd ../backend && 
source venv/bin/activate && 
python manage.py makemigrations && 
python manage.py migrate && 
python manage.py loaddata fixtures/roles.json && 
python manage.py crontab add && 
python manage.py runserver 0.0.0.0:8000