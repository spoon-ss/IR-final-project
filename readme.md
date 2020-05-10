# Build
Install full dependency
```shell script
python -m pip install -r new-requirements.txt 
```
Build index
```shell script
python build_index.py 
```
Run app
```shell script
python run.py 
```
# Example Query
```text
covid <chem>hematoxylin</chem> novel
covid <chem>tri-n-butyl phosphate</chem> novel
covid <chem>tri-n-butyl phosphate</chem> novel <phrase>eye drops</phrase>
```
