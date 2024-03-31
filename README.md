Install:
```
mkdir data
echo "Some secret thing" > data/secret.txt
python3 -m venv venv
source venv/bin/activate
pip install -e '.[dev,test]'
flask --app quotes2 init-db
```

Run:
```
flask --app quotes2 --debug run
```

Test:
```
black .
mypy quotes2
pytest
```
