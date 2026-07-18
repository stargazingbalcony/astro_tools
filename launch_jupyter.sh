#!/bin/bash

#NOTEBOOK_DIR="/tcenas/home/alessiol/notebooks_go_to_repository/"
NOTEBOOK_DIR="/Users/alessiol/pyastro"

[[ -d "$NOTEBOOK_DIR" ]] || mkdir -p "$NOTEBOOK_DIR"


#source /DSNNAS2/Repro/users/alessiol/js_miniconda3/bin/activate
#conda activate jsmet
jupyter lab --port=8080 --port-retries=100 --ServerApp.allow_remote_access=True --ServerApp.ip="`deepblue --ip-address`" --ServerApp.open_browser=False --ServerApp.quit_button=True --notebook-dir="$NOTEBOOK_DIR"
