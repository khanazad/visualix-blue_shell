# secure zmq
```
cd ../
python -m venv .
pip install --upgrade pip
pip install -r requirements.txt
cd test_zmq
python secure_pubsub.py pub
# open new terminal
python secure_pubsub.py sub
```
