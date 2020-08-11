# Bruno communication simulation

`bruno_comm_sim.py` provides stripped down classes that implement the
zmq servers and clients used in the Visualix Bruno server (v20.03) and Unity client [[v20.03]](https://gitlab.com/visualix/unity-client/-/tree/ae5c9269daa4d1b1f3e8399c1d1c43abfaa74d1c). 


## Quickstart
```
git clone blue_shell
cd blue_shell/simulation  
python -m venv ./
pip install --update pip
pip install -r requirements.txt
python bruno_comm_sim.py server map
```
In a second terminal window,
```
python bruno_comm_sim.py client map
```
Substitute `locate` for `map` above, and localization communication
will be simulated.
